from __future__ import annotations

from pathlib import Path

import pytest

from blend_ci.blender import EXIT_MISSING, MISSING_BLENDER, resolve_blender
from blend_ci.cli import main


def test_resolve_blender_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BLENDER", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="fails closed"):
        resolve_blender()


def test_ensure_blender_exit_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BLENDER", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert main(["ensure-blender"]) == EXIT_MISSING


def test_resolve_blender_explicit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    binary = tmp_path / "blender"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.delenv("BLENDER", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    found = resolve_blender(binary)
    assert found.path == binary.resolve()


def test_missing_message_documents_installer() -> None:
    assert "scripts/install_blender.sh" in MISSING_BLENDER
    assert "BLEND_CI_CACHE" in MISSING_BLENDER
