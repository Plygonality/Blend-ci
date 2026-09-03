"""Run blender --background --python and compare the cook to goldens."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from blend_ci.apply_input import prepare_apply_script
from blend_ci.blender import EXIT_MISSING, BlenderBinary, resolve_blender
from blend_ci.dump import canonicalize, lint_dump, load_dump
from blend_ci.goldens import CookCompare, compare_cook, update_requested
from blend_ci.versions import GPU_BACKENDS

INSIDE = Path(__file__).with_name("inside_blender.py")

VULKAN_CRASH_CODES = {132, 133, 134, 136, 137, 139, -11, -6, -4}


@dataclass(frozen=True, slots=True)
class CookResult:
    returncode: int
    dump: Path
    png: Path
    backend_used: str
    compare: CookCompare | None
    log: str


def write_driver(dest: Path) -> Path:
    dest.write_text(INSIDE.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def _blender_cmd(
    binary: BlenderBinary,
    *,
    scene_blend: Path | None,
    driver: Path,
    backend: str,
    extra: list[str],
    factory: bool,
) -> list[str]:
    cmd = [str(binary.path), "--background", "--python-exit-code", "1"]
    if factory and scene_blend is None:
        cmd.append("--factory-startup")
    if backend:
        cmd.extend(["--gpu-backend", backend])
    if scene_blend is not None:
        cmd.append(str(scene_blend))
    cmd.extend(["--python", str(driver), "--", *extra])
    return cmd


def _should_fallback(returncode: int, backend: str, fallback: bool) -> bool:
    if not fallback or backend != "vulkan":
        return False
    return returncode != 0 and (
        returncode in VULKAN_CRASH_CODES or returncode > 128 or returncode < 0
    )


def _run_xvfb(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    env.setdefault("GALLIUM_DRIVER", "llvmpipe")
    wrapped = cmd
    if not env.get("DISPLAY") and shutil.which("xvfb-run"):
        wrapped = ["xvfb-run", "-a", "-s", "-screen 0 1024x768x24", *cmd]
    return subprocess.run(
        wrapped,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def cook(
    *,
    graph: Path | None = None,
    apply: Path | None = None,
    scene: Path | None = None,
    object_name: str | None = None,
    out_dir: Path,
    golden: Path | None = None,
    png_golden: Path | None = None,
    blender: str | Path | None = None,
    gpu_backend: str = "opengl",
    fallback_opengl: bool = True,
    lint: bool = True,
    require_roles: bool = True,
    work_dir: Path | None = None,
) -> CookResult:
    if gpu_backend not in GPU_BACKENDS:
        raise ValueError(f"gpu_backend must be one of {GPU_BACKENDS}, got {gpu_backend!r}")

    try:
        binary = resolve_blender(blender)
    except FileNotFoundError as exc:
        sys.stderr.write(f"blend-ci: {exc}\n")
        raise SystemExit(EXIT_MISSING) from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    dump_out = out_dir / "dump.json"
    png_out = out_dir / "workbench.png"

    scene_blend: Path | None = None
    scene_script: Path | None = None
    if scene is not None:
        suffix = scene.suffix.lower()
        if suffix in {".blend", ".blend1"}:
            scene_blend = scene
        elif suffix == ".py":
            scene_script = scene
        else:
            raise ValueError(
                f"scene fixture must be a .blend or a .py setup script, got {scene}"
            )

    tmp = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="blend-ci-"))
    tmp.mkdir(parents=True, exist_ok=True)
    apply_script = prepare_apply_script(
        graph=graph,
        apply=apply,
        object_name=object_name,
        dest=tmp / "apply.py",
    )
    driver = write_driver(tmp / "driver.py")
    extra = [
        "--dump-out",
        str(dump_out.resolve()),
        "--png-out",
        str(png_out.resolve()),
    ]
    if scene_script:
        extra.extend(["--scene-script", str(scene_script.resolve())])
    extra.extend(["--apply-script", str(apply_script.resolve())])

    logs: list[str] = []
    backend_used = gpu_backend
    cmd = _blender_cmd(
        binary,
        scene_blend=scene_blend,
        driver=driver,
        backend=gpu_backend,
        extra=extra,
        factory=True,
    )
    proc = _run_xvfb(cmd, cwd=tmp)
    logs.append(f"$ {' '.join(cmd)}\n{proc.stdout}")
    if _should_fallback(proc.returncode, gpu_backend, fallback_opengl):
        logs.append(
            f"vulkan exited {proc.returncode}; retrying with --gpu-backend opengl "
            "(5.x crash fallback)"
        )
        backend_used = "opengl"
        retry = _blender_cmd(
            binary,
            scene_blend=scene_blend,
            driver=driver,
            backend="opengl",
            extra=extra,
            factory=True,
        )
        proc = _run_xvfb(retry, cwd=tmp)
        logs.append(f"$ {' '.join(retry)}\n{proc.stdout}")

    if proc.returncode != 0:
        logs.append(f"blend-ci: blender exited {proc.returncode}")
        return CookResult(
            returncode=proc.returncode,
            dump=dump_out,
            png=png_out,
            backend_used=backend_used,
            compare=None,
            log="\n".join(logs),
        )

    if lint:
        result = lint_dump(load_dump(dump_out), require_roles=require_roles)
        if not result.ok:
            for item in result.violations:
                logs.append(f"lint {item.code}: {item.message}")
            return CookResult(
                returncode=1,
                dump=dump_out,
                png=png_out,
                backend_used=backend_used,
                compare=None,
                log="\n".join(logs),
            )

    compared: CookCompare | None = None
    code = 0
    if golden is not None:
        compared = compare_cook(
            canonicalize(load_dump(dump_out)),
            golden,
            png=png_out if png_golden is not None or update_requested() else None,
            png_golden=png_golden,
        )
        logs.extend(compared.messages)
        if not compared.dump_ok:
            code = 1
    return CookResult(
        returncode=code,
        dump=dump_out,
        png=png_out,
        backend_used=backend_used,
        compare=compared,
        log="\n".join(logs),
    )
