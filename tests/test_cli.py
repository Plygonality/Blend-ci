from __future__ import annotations

import json
from pathlib import Path

from blend_ci.blender import EXIT_MISSING
from blend_ci.cli import main
from blend_ci.dump import dumps
from blend_ci.versions import BLENDER_CURRENT, BLENDER_LTS, release_url
from tests.test_dump import VALID

ROOT = Path(__file__).resolve().parents[1]
COLUMN = ROOT / "fixtures" / "column.json"


def test_versions_lists_official_urls(capsys) -> None:
    assert main(["versions"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["lts"] == BLENDER_LTS
    assert payload["current"] == BLENDER_CURRENT
    assert payload["lts_url"] == release_url(BLENDER_LTS)
    assert "download.blender.org/release/Blender4.5/" in payload["lts_url"]
    assert "download.blender.org/release/Blender5.2/" in payload["current_url"]


def test_compare_cli(tmp_path: Path, capsys) -> None:
    dump = tmp_path / "dump.json"
    golden = tmp_path / "golden.json"
    dump.write_text(dumps(VALID), encoding="utf-8")
    golden.write_text(dumps(VALID), encoding="utf-8")
    png = tmp_path / "w.png"
    png.write_bytes(b"bytes")
    assert main(["compare", "--dump", str(dump), "--golden", str(golden), "--png", str(png)]) == 0
    out = capsys.readouterr().out
    assert "PNG hash advisory" in out


def test_compare_cli_dump_fail(tmp_path: Path) -> None:
    dump = tmp_path / "dump.json"
    golden = tmp_path / "golden.json"
    dump.write_text(dumps(VALID), encoding="utf-8")
    broken = json.loads(dumps(VALID))
    broken["objects"][0]["name"] = "Renamed"
    golden.write_text(dumps(broken), encoding="utf-8")
    assert main(["compare", "--dump", str(dump), "--golden", str(golden)]) == 1


def test_cook_without_blender_fails_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("BLENDER", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert (
        main(
            [
                "cook",
                "--graph",
                str(COLUMN),
                "--scene",
                str(ROOT / "fixtures" / "canon_scene.py"),
                "--out-dir",
                str(tmp_path / "out"),
            ]
        )
        == EXIT_MISSING
    )
