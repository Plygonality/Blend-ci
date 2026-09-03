"""Compare a cook dump to golden JSON. PNG hash is advisory unless UPDATE_GOLDENS=1."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from blend_ci.dump import compare_dumps, dumps, load_dump

UPDATE_ENV = "UPDATE_GOLDENS"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_hash(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip().split()[0]


def write_hash(path: Path, digest: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(digest + "\n", encoding="utf-8")


def update_requested() -> bool:
    return os.environ.get(UPDATE_ENV) == "1"


@dataclass
class CookCompare:
    dump_ok: bool
    png_ok: bool
    png_advisory: bool
    updated: bool
    messages: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.dump_ok and (self.png_ok or self.png_advisory)


def compare_cook(
    dump: Mapping[str, object] | Sequence[Mapping[str, object]] | Path,
    golden: Path,
    *,
    png: Path | None = None,
    png_golden: Path | None = None,
    update: bool | None = None,
) -> CookCompare:
    """Compare a structural dump (and optional PNG) to goldens.

    Dump mismatch fails the cook. PNG hash mismatch is printed and ignored
    unless ``UPDATE_GOLDENS=1``, which rewrites both goldens.
    """
    if update is None:
        update = update_requested()
    payload = load_dump(dump) if isinstance(dump, Path) else dump
    messages: list[str] = []
    updated = False

    if update:
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(dumps(payload), encoding="utf-8")
        messages.append(f"wrote dump golden {golden}")
        updated = True
        dump_ok = True
    elif not golden.exists():
        messages.append(
            f"missing dump golden {golden}. Re-run with {UPDATE_ENV}=1 if this is intended."
        )
        dump_ok = False
    else:
        diff = compare_dumps(payload, load_dump(golden))
        dump_ok = diff.ok
        if not diff.ok:
            messages.append(f"dump drifted from {golden}")
            messages.extend(diff.messages)
            messages.append(f"Re-run with {UPDATE_ENV}=1 if the change is intended.")

    png_ok = True
    png_advisory = False
    if png is not None:
        if not png.exists():
            messages.append(f"workbench PNG missing: {png}")
            png_ok = False
        else:
            digest = sha256_file(png)
            target = png_golden or golden.with_suffix(".png.sha256")
            if update:
                write_hash(target, digest)
                messages.append(f"wrote PNG hash golden {target} ({digest})")
                updated = True
                png_ok = True
            elif not target.exists():
                messages.append(
                    f"PNG hash advisory: no golden at {target} (got {digest}). "
                    f"Set {UPDATE_ENV}=1 to record it."
                )
                png_advisory = True
                png_ok = False
            else:
                expected = read_hash(target)
                if digest != expected:
                    messages.append(
                        f"PNG hash advisory: {digest} != {expected} ({target}). "
                        "Workbench pixels are not a closed gate; "
                        f"set {UPDATE_ENV}=1 to accept the new hash."
                    )
                    png_advisory = True
                    png_ok = False

    return CookCompare(
        dump_ok=dump_ok,
        png_ok=png_ok,
        png_advisory=png_advisory,
        updated=updated,
        messages=messages,
    )
