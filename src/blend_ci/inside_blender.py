"""Self-contained bpy cook. Host concatenates this file; it must not import blend_ci."""

from __future__ import annotations

import argparse
import json
import runpy
import sys
from pathlib import Path

MESH_TYPES = {"MESH", "CURVE", "SURFACE", "META", "FONT", "VOLUME", "POINTCLOUD", "CURVES"}
HUMAN_FIGURE = "HumanFigure"


def _collection_name(obj) -> str:
    collections = obj.users_collection
    return collections[0].name if collections else ""


def _role_for(obj) -> str | None:
    role = obj.get("unit_canon.role")
    if role:
        return str(role)
    if obj.name == HUMAN_FIGURE:
        return "human_figure"
    return None


def dump_scene(bpy) -> dict:
    """Same fields as unit_canon.blender.dump_scene, mesh/role objects only."""
    bpy.context.view_layer.update()
    objects = []
    for obj in bpy.data.objects:
        role = _role_for(obj)
        obj_type = getattr(obj, "type", "")
        if obj_type not in MESH_TYPES and role is None:
            continue
        objects.append(
            {
                "name": obj.name,
                "collection": _collection_name(obj),
                "dimensions": [
                    round(float(obj.dimensions.x), 4),
                    round(float(obj.dimensions.y), 4),
                    round(float(obj.dimensions.z), 4),
                ],
                "location": [
                    round(float(obj.location.x), 4),
                    round(float(obj.location.y), 4),
                    round(float(obj.location.z), 4),
                ],
                "role": role,
            }
        )
    objects.sort(key=lambda row: row["name"])
    return {"objects": objects}


def _ensure_camera(bpy):
    scene = bpy.context.scene
    if scene.camera is not None:
        return
    data = bpy.data.cameras.new("BlendCI")
    cam = bpy.data.objects.new("BlendCI", data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = (7.0, -7.0, 5.0)
    cam.rotation_euler = (1.1, 0.0, 0.785)


def render_workbench(bpy, png_out: Path) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str(png_out)
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = False
    shading.show_cavity = False
    _ensure_camera(bpy)
    png_out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)


def _run_script(path: str | None) -> None:
    if not path:
        return
    runpy.run_path(path, run_name="__blend_ci_script__")


def cook(scene_script: str | None, apply_script: str | None, dump_out: str, png_out: str) -> int:
    import bpy

    _run_script(scene_script)
    _run_script(apply_script)
    bpy.context.view_layer.update()
    dump_path = Path(dump_out)
    dump_path.parent.mkdir(parents=True, exist_ok=True)
    dump_path.write_text(json.dumps(dump_scene(bpy), indent=2) + "\n", encoding="utf-8")
    render_workbench(bpy, Path(png_out))
    return 0


def script_argv(argv: list[str] | None = None) -> list[str]:
    """Blender puts the full CLI in ``sys.argv``. Take flags after ``--``."""
    raw = list(sys.argv if argv is None else argv)
    if "--" in raw:
        return raw[raw.index("--") + 1 :]
    if raw and raw[0].endswith(".py"):
        return raw[1:]
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="blend-ci-inside")
    parser.add_argument("--scene-script")
    parser.add_argument("--apply-script")
    parser.add_argument("--dump-out", required=True)
    parser.add_argument("--png-out", required=True)
    args = parser.parse_args(script_argv(argv))
    return cook(args.scene_script, args.apply_script, args.dump_out, args.png_out)


if __name__ == "__main__":
    raise SystemExit(main())
