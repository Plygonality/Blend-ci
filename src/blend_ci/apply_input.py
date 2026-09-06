"""Turn a sibling artifact into a bpy apply script. No new graph format."""

from __future__ import annotations

import json
from pathlib import Path

from gn_as_code.apply import to_apply_script
from gn_as_code.dump import load as load_graph

GN_FORMAT = "gn-as-code"
SHADER_FORMAT = "shader-as-code"


def prepare_apply_script(
    *,
    graph: Path | None,
    apply: Path | None,
    object_name: str | None,
    dest: Path,
) -> Path:
    """Write a self-contained bpy script to ``dest``.

    * ``--graph`` must be an existing sibling dump (``gn-as-code``).
    * ``--apply`` is a bpy script from gn-as-code / probe-kit / Master-Node.
    """
    if graph and apply:
        raise ValueError("pass either --graph or --apply, not both")
    if not graph and not apply:
        raise ValueError("pass --graph (gn-as-code JSON) or --apply (existing bpy script)")

    dest.parent.mkdir(parents=True, exist_ok=True)
    if apply:
        text = Path(apply).read_text(encoding="utf-8")
        dest.write_text(text, encoding="utf-8")
        return dest

    path = Path(graph)
    payload = json.loads(path.read_text(encoding="utf-8"))
    fmt = payload.get("format")
    if fmt == GN_FORMAT:
        script = to_apply_script(load_graph(path), object_name=object_name)
        dest.write_text(script, encoding="utf-8")
        return dest
    if fmt == SHADER_FORMAT:
        return _shader_apply(payload, object_name=object_name, dest=dest)
    raise ValueError(
        f"{path} has format {fmt!r}. Blend-ci does not invent graph formats. "
        "Pass a gn-as-code dump, or an existing apply script via --apply "
        "(gn-as-code apply-script, probe-kit apply-script, Master-Node smoke)."
    )


def _shader_apply(payload: dict, *, object_name: str | None, dest: Path) -> Path:
    try:
        from shader_as_code.apply import to_apply_script as shader_script
    except ImportError as exc:
        raise ValueError(
            "shader-as-code dump requires the shader-as-code package. "
            "pip install 'shader-as-code @ git+https://github.com/Plygonality/Shader-as-code.git' "
            "or pass --apply with a script you already generated."
        ) from exc
    dest.write_text(
        shader_script(payload, object_name=object_name),
        encoding="utf-8",
    )
    return dest
