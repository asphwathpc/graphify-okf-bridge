"""Phase 4 DoD: `okf-bridge link <graph.json> <bundle-dir> -o out.json` merges
inferred edges (and their synthetic source nodes) into a graphify-loadable
graph.json (IMPLEMENTATION_PLAN.md Phase 4 step 2)."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from graphify_okf_bridge.cli import main
from graphify_okf_bridge.graphify_io.loader import load_graph

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_link_merges_inferred_edges_into_output_graph(tmp_path: Path) -> None:
    out_path = tmp_path / "linked.json"
    result = CliRunner().invoke(
        main,
        [
            "link",
            str(FIXTURES / "tiny_graph.json"),
            str(FIXTURES / "okf_minimal"),
            "-o",
            str(out_path),
            "--repo-root",
            str(FIXTURES / "tiny_repo"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "5 edge(s) inferred" in result.output

    original = load_graph(FIXTURES / "tiny_graph.json")
    linked = load_graph(out_path)

    assert len(linked.links) == len(original.links) + 5
    # two synthetic .sql source nodes + two synthetic okf: concept target nodes (L13)
    assert len(linked.nodes) == len(original.nodes) + 4

    new_edges = [e for e in linked.links if e.confidence == "INFERRED" and e.model_extra
                 and "linker_signal" in e.model_extra]
    assert len(new_edges) == 5


def test_link_output_composes_with_import(tmp_path: Path) -> None:
    """MAPPING.md L11: linker edge targets must resolve against an imported bundle."""
    linked_path = tmp_path / "linked.json"
    imported_path = tmp_path / "imported.json"
    runner = CliRunner()

    link_result = runner.invoke(
        main,
        [
            "link",
            str(FIXTURES / "tiny_graph.json"),
            str(FIXTURES / "okf_minimal"),
            "-o",
            str(linked_path),
            "--repo-root",
            str(FIXTURES / "tiny_repo"),
        ],
    )
    assert link_result.exit_code == 0, link_result.output

    import_result = runner.invoke(
        main, ["import", str(FIXTURES / "okf_minimal"), "-o", str(imported_path)]
    )
    assert import_result.exit_code == 0, import_result.output

    linked = load_graph(linked_path)
    imported = load_graph(imported_path)
    imported_ids = {n.id for n in imported.nodes}
    linker_edge_targets = {e.target for e in linked.links if e.target.startswith("okf:")}
    assert linker_edge_targets <= imported_ids
