"""Unit-canon scale-reference fixture. Executed inside Blender.

Creates the four Collection-linter roles. Git is the source of truth;
this script is the scene fixture, not a .blend.
"""

from __future__ import annotations

import bpy

CANON_COLLECTION = "canon"


def _clear_defaults() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def _collection() -> bpy.types.Collection:
    existing = bpy.data.collections.get(CANON_COLLECTION)
    if existing is not None:
        return existing
    col = bpy.data.collections.new(CANON_COLLECTION)
    bpy.context.scene.collection.children.link(col)
    return col


def _link(obj, collection) -> None:
    for user in list(obj.users_collection):
        user.objects.unlink(obj)
    collection.objects.link(obj)


def _mesh(name: str, role: str, collection, *, primitive: str, **kwargs):
    op = getattr(bpy.ops.mesh, primitive)
    op(**kwargs)
    obj = bpy.context.object
    obj.name = name
    obj["unit_canon.role"] = role
    _link(obj, collection)
    return obj


def setup() -> None:
    _clear_defaults()
    col = _collection()

    human = _mesh(
        "HumanFigure",
        "human_figure",
        col,
        primitive="primitive_cube_add",
        size=1.0,
        location=(0.0, 0.0, 0.9),
    )
    human.scale = (0.45, 0.30, 1.8)

    _mesh(
        "airlock_main",
        "airlock",
        col,
        primitive="primitive_cylinder_add",
        radius=0.5,
        depth=1.0,
        location=(3.0, 0.0, 0.5),
    )

    deck = _mesh(
        "deck_1",
        "deck",
        col,
        primitive="primitive_cube_add",
        size=1.0,
        location=(0.0, 3.0, 3.0),
    )
    deck.scale = (4.0, 4.0, 0.2)

    _mesh(
        "grid_origin",
        "grid",
        col,
        primitive="primitive_plane_add",
        size=2.0,
        location=(2.0, 2.0, 0.0),
    )

    bpy.context.view_layer.update()


setup()
