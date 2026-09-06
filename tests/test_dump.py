from __future__ import annotations

from blend_ci.dump import canonicalize, compare_dumps, dumps, lint_dump

VALID = {
    "objects": [
        {
            "name": "HumanFigure",
            "collection": "canon",
            "dimensions": [0.45, 0.3, 1.8],
            "location": [0.0, 0.0, 0.0],
            "role": "human_figure",
        },
        {
            "name": "airlock_main",
            "collection": "canon",
            "dimensions": [1.0, 1.0, 1.0],
            "location": [3.0, 0.0, 0.0],
            "role": "airlock",
        },
        {
            "name": "deck_1",
            "collection": "canon",
            "dimensions": [4.0, 4.0, 0.2],
            "location": [0.0, 0.0, 3.0],
            "role": "deck",
        },
        {
            "name": "grid_origin",
            "collection": "canon",
            "dimensions": [2.0, 2.0, 0.0],
            "location": [2.0, 2.0, 0.0],
            "role": "grid",
        },
    ]
}


def test_canonicalize_sorts_and_rounds() -> None:
    payload = {
        "objects": [
            {"name": "b", "collection": "c", "dimensions": [1.00004, 0, 0], "location": [0, 0, 0]},
            {"name": "a", "collection": "c", "dimensions": [0, 0, 0], "location": [0, 0, 0], "role": ""},
        ]
    }
    got = canonicalize(payload)
    assert [row["name"] for row in got["objects"]] == ["a", "b"]
    assert got["objects"][1]["dimensions"][0] == 1.0
    assert got["objects"][0]["role"] is None


def test_compare_tolerance() -> None:
    shifted = canonicalize(VALID)
    shifted["objects"][0]["dimensions"][2] = 1.805
    assert compare_dumps(shifted, VALID).ok
    shifted["objects"][0]["dimensions"][2] = 1.9
    diff = compare_dumps(shifted, VALID)
    assert not diff.ok
    assert any("dimensions.z" in line for line in diff.messages)


def test_compare_name_drift() -> None:
    other = canonicalize(VALID)
    other["objects"][0]["name"] = "NotHuman"
    diff = compare_dumps(other, VALID)
    assert not diff.ok
    assert any("missing objects" in line for line in diff.messages)


def test_lint_uses_unit_canon() -> None:
    assert lint_dump(VALID).ok
    broken = canonicalize(VALID)
    for row in broken["objects"]:
        if row["role"] == "human_figure":
            row["dimensions"][2] = 2.5
    result = lint_dump(broken)
    assert not result.ok
    assert result.by_code("HUMAN_HEIGHT")


def test_dumps_stable() -> None:
    text = dumps(VALID)
    assert text.startswith("{\n  \"objects\":")
    assert text.endswith("\n")
