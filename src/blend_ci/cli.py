"""CLI: cook, compare, ensure-blender."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from blend_ci.blender import EXIT_MISSING, resolve_blender
from blend_ci.cook import cook
from blend_ci.dump import dumps, lint_dump, load_dump
from blend_ci.goldens import compare_cook
from blend_ci.versions import (
    BLENDER_CURRENT,
    BLENDER_LTS,
    GPU_BACKENDS,
    release_url,
    resolve_channel,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="blend-ci",
        description=(
            "Apply a gn-as-code / Master-Node / Habitat-kit artifact in "
            "headless Blender, dump the scene, render one workbench PNG, "
            "and fail if the structural dump drifts."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cook = sub.add_parser("cook", help="Run blender --background --python and compare goldens")
    p_cook.add_argument("--graph", type=Path, help="Existing gn-as-code (or shader-as-code) JSON")
    p_cook.add_argument("--apply", type=Path, help="Existing bpy apply script")
    p_cook.add_argument(
        "--scene",
        type=Path,
        help="Scene fixture: .blend or a .py setup script executed inside Blender",
    )
    p_cook.add_argument("--object", dest="object_name", help="Object name for gn-as-code apply")
    p_cook.add_argument("--out-dir", type=Path, default=Path("artifacts"))
    p_cook.add_argument("--golden", type=Path, help="Structural dump golden JSON")
    p_cook.add_argument("--png-golden", type=Path, help="Advisory SHA-256 file for the PNG")
    p_cook.add_argument("--blender", help="Blender executable (else BLENDER or PATH)")
    p_cook.add_argument(
        "--gpu-backend",
        choices=GPU_BACKENDS,
        default="opengl",
        help="Vulkan, or the OpenGL fallback used when 5.x Vulkan crashes",
    )
    p_cook.add_argument(
        "--no-fallback-opengl",
        action="store_true",
        help="Do not retry --gpu-backend opengl after a Vulkan crash",
    )
    p_cook.add_argument("--no-lint", action="store_true", help="Skip unit-canon collection lint")
    p_cook.add_argument(
        "--allow-missing-roles",
        action="store_true",
        help="Do not fail lint when a canon role is absent",
    )

    p_cmp = sub.add_parser("compare", help="Compare an existing dump/PNG to goldens")
    p_cmp.add_argument("--dump", type=Path, required=True)
    p_cmp.add_argument("--golden", type=Path, required=True)
    p_cmp.add_argument("--png", type=Path)
    p_cmp.add_argument("--png-golden", type=Path)
    p_cmp.add_argument("--no-lint", action="store_true")
    p_cmp.add_argument("--allow-missing-roles", action="store_true")

    p_ok = sub.add_parser("ensure-blender", help="Exit 2 if blender is missing (fail closed)")
    p_ok.add_argument("--blender")

    sub.add_parser("versions", help="Print pinned LTS / current download URLs")

    args = parser.parse_args(argv)

    if args.cmd == "ensure-blender":
        try:
            binary = resolve_blender(args.blender)
        except FileNotFoundError as exc:
            sys.stderr.write(f"blend-ci: {exc}\n")
            return EXIT_MISSING
        sys.stdout.write(f"{binary.path}\n")
        return 0

    if args.cmd == "versions":
        payload = {
            "lts": BLENDER_LTS,
            "current": BLENDER_CURRENT,
            "lts_url": release_url(BLENDER_LTS),
            "current_url": release_url(BLENDER_CURRENT),
            "resolved": {
                "lts": resolve_channel("lts"),
                "current": resolve_channel("current"),
            },
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if args.cmd == "compare":
        dump = load_dump(args.dump)
        if not args.no_lint:
            lint_result = lint_dump(dump, require_roles=not args.allow_missing_roles)
            if not lint_result.ok:
                for item in lint_result.violations:
                    sys.stderr.write(f"lint {item.code}: {item.message}\n")
                return 1
        result = compare_cook(
            dump,
            args.golden,
            png=args.png,
            png_golden=args.png_golden,
        )
        for line in result.messages:
            stream = sys.stdout if result.ok else sys.stderr
            stream.write(line + "\n")
        if result.dump_ok:
            sys.stdout.write(dumps(dump))
        return 0 if result.ok else 1

    if args.cmd == "cook":
        try:
            result = cook(
                graph=args.graph,
                apply=args.apply,
                scene=args.scene,
                object_name=args.object_name,
                out_dir=args.out_dir,
                golden=args.golden,
                png_golden=args.png_golden,
                blender=args.blender,
                gpu_backend=args.gpu_backend,
                fallback_opengl=not args.no_fallback_opengl,
                lint=not args.no_lint,
                require_roles=not args.allow_missing_roles,
            )
        except ValueError as exc:
            sys.stderr.write(f"blend-ci: {exc}\n")
            return 2
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else EXIT_MISSING
            return code
        sys.stdout.write(result.log)
        if not result.log.endswith("\n"):
            sys.stdout.write("\n")
        if result.returncode == 0:
            sys.stdout.write(f"dump {result.dump}\n")
            sys.stdout.write(f"png {result.png}\n")
            sys.stdout.write(f"gpu_backend {result.backend_used}\n")
        return result.returncode

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
