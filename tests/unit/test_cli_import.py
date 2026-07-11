"""Phase 3 DoD: `okf-bridge import <bundle-dir> -o <graph.json>` produces a
graphify-loadable graph.json (IMPLEMENTATION_PLAN.md Phase 3 step 4)."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from graphify_okf_bridge.cli import main
from graphify_okf_bridge.graphify_io.loader import load_graph

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_import_ga4_produces_loadable_graph_json(tmp_path: Path) -> None:
    out_path = tmp_path / "ga4_graph.json"
    result = CliRunner().invoke(
        main, ["import", str(FIXTURES / "okf_official" / "ga4"), "-o", str(out_path)]
    )
    assert result.exit_code == 0, result.output

    graph = load_graph(out_path)
    assert len(graph.nodes) == 11


def test_import_of_own_export_round_trips_via_cli(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    imported_path = tmp_path / "imported.json"
    runner = CliRunner()

    export_result = runner.invoke(
        main, ["export", str(FIXTURES / "tiny_graph.json"), "-o", str(bundle_dir)]
    )
    assert export_result.exit_code == 0, export_result.output

    import_result = runner.invoke(main, ["import", str(bundle_dir), "-o", str(imported_path)])
    assert import_result.exit_code == 0, import_result.output

    original = load_graph(FIXTURES / "tiny_graph.json")
    imported = load_graph(imported_path)
    assert len(imported.nodes) == len(original.nodes)
    assert len(imported.links) == len(original.links)


def test_import_output_is_plain_json(tmp_path: Path) -> None:
    out_path = tmp_path / "ga4_graph.json"
    CliRunner().invoke(
        main, ["import", str(FIXTURES / "okf_official" / "ga4"), "-o", str(out_path)]
    )
    json.loads(out_path.read_text(encoding="utf-8"))


def test_import_prints_success_summary(tmp_path: Path) -> None:
    out_path = tmp_path / "ga4_graph.json"
    result = CliRunner().invoke(
        main, ["import", str(FIXTURES / "okf_official" / "ga4"), "-o", str(out_path)]
    )
    assert result.exit_code == 0, result.output
    assert "11 node(s), 9 edge(s) written to" in result.output
    assert str(out_path) in result.output
