from __future__ import annotations

from pathlib import Path

from blend_ci.blender import BlenderBinary
from blend_ci.cook import VULKAN_CRASH_CODES, _blender_cmd, _should_fallback, write_driver
from blend_ci.inside_blender import script_argv


def test_driver_is_self_contained(tmp_path: Path) -> None:
    dest = tmp_path / "driver.py"
    write_driver(dest)
    text = dest.read_text(encoding="utf-8")
    assert "from blend_ci" not in text
    assert "import blend_ci\n" not in text
    assert "dump_scene" in text
    assert "BLENDER_WORKBENCH" in text


def test_blender_command_order() -> None:
    binary = BlenderBinary(path=Path("/opt/blender/blender"))
    cmd = _blender_cmd(
        binary,
        scene_blend=None,
        driver=Path("/tmp/driver.py"),
        backend="vulkan",
        extra=["--dump-out", "/tmp/d.json"],
        factory=True,
    )
    assert cmd[:4] == [
        "/opt/blender/blender",
        "--background",
        "--python-exit-code",
        "1",
    ]
    assert "--gpu-backend" in cmd
    assert "vulkan" in cmd
    assert cmd[cmd.index("--python") + 1] == "/tmp/driver.py"
    assert "--" in cmd


def test_opengl_fallback_on_vulkan_crash() -> None:
    assert _should_fallback(139, "vulkan", True)
    assert _should_fallback(134, "vulkan", True)
    assert not _should_fallback(139, "opengl", True)
    assert not _should_fallback(1, "vulkan", True)
    assert not _should_fallback(139, "vulkan", False)
    assert 139 in VULKAN_CRASH_CODES


def test_script_argv_strips_blender_cli() -> None:
    raw = [
        "/opt/blender/blender",
        "--background",
        "--python",
        "/tmp/driver.py",
        "--",
        "--dump-out",
        "/tmp/d.json",
        "--png-out",
        "/tmp/p.png",
    ]
    assert script_argv(raw) == ["--dump-out", "/tmp/d.json", "--png-out", "/tmp/p.png"]
    assert script_argv(["--dump-out", "x", "--png-out", "y"]) == [
        "--dump-out",
        "x",
        "--png-out",
        "y",
    ]


def test_help() -> None:
    from blend_ci.cli import main

    try:
        main(["cook", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
