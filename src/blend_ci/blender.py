"""Locate Blender and fail closed when it is not on the runner."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

MISSING_BLENDER = (
    "blender is not on PATH and BLENDER is unset. "
    "Blend-ci fails closed: it will not skip, stub, or fake a cook. "
    "Install the official linux-x64 tarball with scripts/install_blender.sh "
    "(cached under $BLEND_CI_CACHE/blender-<version>/) or point BLENDER at "
    "the binary. See README.md § Install Blender."
)

EXIT_MISSING = 2


@dataclass(frozen=True, slots=True)
class BlenderBinary:
    path: Path

    def __str__(self) -> str:
        return str(self.path)


def resolve_blender(explicit: str | Path | None = None) -> BlenderBinary:
    """Return the Blender executable or raise FileNotFoundError."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env = os.environ.get("BLENDER")
    if env:
        candidates.append(Path(env).expanduser())
    which = shutil.which("blender")
    if which:
        candidates.append(Path(which))

    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve() if path.exists() else path
        if resolved in seen:
            continue
        seen.add(resolved)
        if path.is_file() and os.access(path, os.X_OK):
            return BlenderBinary(path=path.resolve())
    raise FileNotFoundError(MISSING_BLENDER)


def require_blender(explicit: str | Path | None = None) -> BlenderBinary:
    """CLI helper: resolve Blender or print the fail-closed message."""
    try:
        return resolve_blender(explicit)
    except FileNotFoundError as exc:
        raise SystemExit(f"blend-ci: {exc}") from exc
