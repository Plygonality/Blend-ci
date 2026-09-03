from __future__ import annotations

from pathlib import Path

from blend_ci.dump import dumps
from blend_ci.goldens import compare_cook, sha256_file
from tests.test_dump import VALID


def test_dump_mismatch_fails(tmp_path: Path) -> None:
    golden = tmp_path / "scene.dump.json"
    golden.write_text(dumps(VALID), encoding="utf-8")
    drifted = {"objects": [dict(VALID["objects"][0]), *VALID["objects"][1:]]}
    drifted["objects"][0] = {**drifted["objects"][0], "name": "OtherFigure", "role": "human_figure"}
    result = compare_cook(drifted, golden, update=False)
    assert not result.dump_ok
    assert not result.ok


def test_missing_golden_fails_unless_update(tmp_path: Path) -> None:
    golden = tmp_path / "missing.json"
    result = compare_cook(VALID, golden, update=False)
    assert not result.dump_ok
    updated = compare_cook(VALID, golden, update=True)
    assert updated.dump_ok
    assert golden.exists()


def test_png_hash_is_advisory(tmp_path: Path) -> None:
    golden = tmp_path / "scene.dump.json"
    png = tmp_path / "workbench.png"
    png.write_bytes(b"png-a")
    png_golden = tmp_path / "scene.png.sha256"
    compare_cook(VALID, golden, png=png, png_golden=png_golden, update=True)
    png.write_bytes(b"png-b")
    result = compare_cook(VALID, golden, png=png, png_golden=png_golden, update=False)
    assert result.dump_ok
    assert result.png_advisory
    assert result.ok
    assert sha256_file(png) != png_golden.read_text(encoding="utf-8").strip()


def test_update_goldens_rewrites_png_hash(tmp_path: Path, monkeypatch) -> None:
    golden = tmp_path / "scene.dump.json"
    png = tmp_path / "workbench.png"
    png.write_bytes(b"png-a")
    png_golden = tmp_path / "scene.png.sha256"
    monkeypatch.setenv("UPDATE_GOLDENS", "1")
    result = compare_cook(VALID, golden, png=png, png_golden=png_golden)
    assert result.updated
    assert png_golden.read_text(encoding="utf-8").strip() == sha256_file(png)
