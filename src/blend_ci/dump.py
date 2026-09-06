"""Structural scene dump: object names, dimensions, unit_canon roles.

The object list matches ``unit_canon.blender.dump_scene`` / Collection-linter
``Scene.from_dicts``. This is not a graph format.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from unit_canon.collection_linter import DEFAULT_TOLERANCE_M, Scene, lint

PathLike = str | Path


def round_vec(values: Sequence[float], *, places: int = 4) -> list[float]:
    return [round(float(item), places) for item in values]


def object_dict(
    *,
    name: str,
    collection: str,
    dimensions: Sequence[float],
    location: Sequence[float],
    role: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "collection": collection,
        "dimensions": round_vec(dimensions),
        "location": round_vec(location),
        "role": role,
    }


def canonicalize(payload: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Sort objects by name; keep only the linter fields."""
    if isinstance(payload, Mapping) and "objects" in payload:
        rows = list(payload["objects"])
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        rows = list(payload)
    else:
        raise ValueError('Scene dump must be {"objects": [...]} or a list of objects')
    objects = []
    for row in rows:
        role = row.get("role")
        if role == "":
            role = None
        objects.append(
            object_dict(
                name=str(row["name"]),
                collection=str(row.get("collection", "")),
                dimensions=row.get("dimensions", (0.0, 0.0, 0.0)),
                location=row.get("location", (0.0, 0.0, 0.0)),
                role=role,
            )
        )
    objects.sort(key=lambda item: item["name"])
    return {"objects": objects}


def dumps(payload: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> str:
    return json.dumps(canonicalize(payload), indent=2, sort_keys=False, ensure_ascii=False) + "\n"


def load_dump(path: PathLike) -> dict[str, Any]:
    return canonicalize(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(frozen=True, slots=True)
class DumpDiff:
    ok: bool
    messages: tuple[str, ...]

    def format(self) -> str:
        return "\n".join(self.messages)


def compare_dumps(
    got: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    expected: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    tolerance_m: float = DEFAULT_TOLERANCE_M,
) -> DumpDiff:
    """Fail if names/roles drift or a length is off by more than the canon tolerance."""
    left = canonicalize(got)["objects"]
    right = canonicalize(expected)["objects"]
    messages: list[str] = []
    if len(left) != len(right):
        messages.append(f"object count {len(left)} != golden {len(right)}")
    by_name_l = {row["name"]: row for row in left}
    by_name_r = {row["name"]: row for row in right}
    extra = sorted(set(by_name_l) - set(by_name_r))
    missing = sorted(set(by_name_r) - set(by_name_l))
    if extra:
        messages.append("unexpected objects: " + ", ".join(extra))
    if missing:
        messages.append("missing objects: " + ", ".join(missing))
    for name in sorted(set(by_name_l) & set(by_name_r)):
        a, b = by_name_l[name], by_name_r[name]
        if a["collection"] != b["collection"]:
            messages.append(f"{name} collection {a['collection']!r} != {b['collection']!r}")
        if a["role"] != b["role"]:
            messages.append(f"{name} role {a['role']!r} != {b['role']!r}")
        for field in ("dimensions", "location"):
            for i, axis in enumerate("xyz"):
                delta = abs(float(a[field][i]) - float(b[field][i]))
                if delta > tolerance_m:
                    messages.append(
                        f"{name} {field}.{axis} {a[field][i]:g} != {b[field][i]:g} "
                        f"(Δ {delta:g} m > {tolerance_m:g})"
                    )
    return DumpDiff(ok=not messages, messages=tuple(messages))


def lint_dump(
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    require_roles: bool = True,
):
    canonical = canonicalize(payload)
    return lint(Scene.from_dicts(canonical["objects"]), require_roles=require_roles)


def iter_objects(payload: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    return canonicalize(payload)["objects"]
