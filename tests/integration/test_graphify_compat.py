"""Phase 3 DoD (IMPLEMENTATION_PLAN.md Phase 3 step 3 / MAPPING.md I7):
output of `okf-bridge import` must be consumable by the real, installed
`graphify` binary -- `merge-graphs`, `explain`, and `path` must work against
an imported+merged graph. Ground rule 8: only `-m integration` tests may
invoke graphify; deselected by default (pyproject.toml addopts).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from graphify_okf_bridge.exporter import export
from graphify_okf_bridge.graphify_io.loader import load_graph, save_graph
from graphify_okf_bridge.importer import import_bundle
from graphify_okf_bridge.okf.reader import read_bundle

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent.parent / "fixtures"

_GRAPHIFY = shutil.which("graphify")


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    assert _GRAPHIFY is not None, "graphify binary not on PATH -- install with graphifyy"
    return subprocess.run([_GRAPHIFY, *args], capture_output=True, text=True)


def test_merge_graphs_accepts_imported_ga4_bundle(tmp_path: Path) -> None:
    bundle, _ = read_bundle(FIXTURES / "okf_official" / "ga4")
    ga4_graph, diagnostics = import_bundle(bundle)
    assert [d for d in diagnostics if d.level == "error"] == []

    ga4_graph_path = tmp_path / "ga4_graph.json"
    save_graph(ga4_graph, ga4_graph_path)

    merged_path = tmp_path / "merged.json"
    result = _run(
        "merge-graphs",
        str(FIXTURES / "tiny_graph.json"),
        str(ga4_graph_path),
        "--out",
        str(merged_path),
    )
    assert result.returncode == 0, result.stderr
    assert merged_path.exists()

    merged = load_graph(merged_path)
    tiny_graph = load_graph(FIXTURES / "tiny_graph.json")
    assert len(merged.nodes) == len(tiny_graph.nodes) + len(ga4_graph.nodes)


def test_explain_and_path_work_on_merged_graph(tmp_path: Path) -> None:
    bundle, _ = read_bundle(FIXTURES / "okf_official" / "ga4")
    ga4_graph, _ = import_bundle(bundle)
    ga4_graph_path = tmp_path / "ga4_graph.json"
    save_graph(ga4_graph, ga4_graph_path)

    merged_path = tmp_path / "merged.json"
    _run(
        "merge-graphs",
        str(FIXTURES / "tiny_graph.json"),
        str(ga4_graph_path),
        "--out",
        str(merged_path),
    )

    explain_result = _run("explain", "BaseModel", "--graph", str(merged_path))
    assert explain_result.returncode == 0, explain_result.stderr

    path_result = _run("path", "models.py", "BaseModel", "--graph", str(merged_path))
    assert path_result.returncode == 0, path_result.stderr


def test_import_of_own_export_round_trips_through_graphify_merge(tmp_path: Path) -> None:
    graph = load_graph(FIXTURES / "tiny_graph.json")
    bundle = export(graph)
    imported, diagnostics = import_bundle(bundle)
    assert [d for d in diagnostics if d.level == "error"] == []
    assert [d for d in diagnostics if d.level == "warning"] == []

    imported_path = tmp_path / "imported.json"
    save_graph(imported, imported_path)

    merged_path = tmp_path / "merged.json"
    result = _run(
        "merge-graphs",
        str(FIXTURES / "tiny_graph.json"),
        str(imported_path),
        "--out",
        str(merged_path),
    )
    assert result.returncode == 0, result.stderr
