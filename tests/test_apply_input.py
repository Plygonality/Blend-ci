from __future__ import annotations

from pathlib import Path

import pytest

from blend_ci.apply_input import prepare_apply_script

ROOT = Path(__file__).resolve().parents[1]
COLUMN = ROOT / "fixtures" / "column.json"


def test_gn_as_code_graph_uses_sibling_apply(tmp_path: Path) -> None:
    dest = tmp_path / "apply.py"
    written = prepare_apply_script(
        graph=COLUMN,
        apply=None,
        object_name="Column",
        dest=dest,
    )
    text = written.read_text(encoding="utf-8")
    assert "apply_graph_dict" in text
    assert "Column" in text
    assert '"format": "gn-as-code"' in text or '"format": "gn-as-code"' in COLUMN.read_text(
        encoding="utf-8"
    )


def test_existing_apply_script_is_copied(tmp_path: Path) -> None:
    src = tmp_path / "live.py"
    src.write_text("print('from Master-Node smoke')\n", encoding="utf-8")
    dest = tmp_path / "apply.py"
    prepare_apply_script(graph=None, apply=src, object_name=None, dest=dest)
    assert dest.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")


def test_rejects_unknown_graph_format(tmp_path: Path) -> None:
    graph = tmp_path / "novel.json"
    graph.write_text('{"format": "blend-ci-graph", "nodes": []}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="does not invent graph formats"):
        prepare_apply_script(
            graph=graph,
            apply=None,
            object_name=None,
            dest=tmp_path / "apply.py",
        )


def test_requires_graph_or_apply(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="--graph"):
        prepare_apply_script(graph=None, apply=None, object_name=None, dest=tmp_path / "a.py")
