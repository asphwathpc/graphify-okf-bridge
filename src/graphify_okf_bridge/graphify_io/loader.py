"""Load/save graphify's `graph.json`."""

from __future__ import annotations

import json
from pathlib import Path

from graphify_okf_bridge.graphify_io.schema import Graph


def load_graph(path: str | Path) -> Graph:
    """Parse a graphify `graph.json` file into a `Graph` model."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Graph.model_validate(data)


def save_graph(graph: Graph, path: str | Path) -> None:
    """Serialize a `Graph` model back to a graphify-compatible `graph.json` file."""
    payload = graph.model_dump(by_alias=True, exclude_none=False)
    Path(path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
