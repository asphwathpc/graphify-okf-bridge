"""Phase 3 acceptance bar (IMPLEMENTATION_PLAN.md Phase 3 / MAPPING.md I6):
`import(export(tiny_graph))` must preserve node count, edge count, relations,
and confidences. Titles/slugs/confidence_score may normalize.
"""

from __future__ import annotations

from pathlib import Path

from graphify_okf_bridge.exporter import export
from graphify_okf_bridge.graphify_io.loader import load_graph
from graphify_okf_bridge.importer import import_bundle

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _tiny_graph():
    return load_graph(FIXTURES / "tiny_graph.json")


def test_round_trip_preserves_node_count() -> None:
    graph = _tiny_graph()
    bundle = export(graph)
    imported, diagnostics = import_bundle(bundle)

    assert [d for d in diagnostics if d.level == "error"] == []
    assert len(imported.nodes) == len(graph.nodes)


def test_round_trip_preserves_node_ids() -> None:
    graph = _tiny_graph()
    bundle = export(graph)
    imported, _ = import_bundle(bundle)

    assert {n.id for n in imported.nodes} == {n.id for n in graph.nodes}


def test_round_trip_preserves_edge_count() -> None:
    graph = _tiny_graph()
    bundle = export(graph)
    imported, diagnostics = import_bundle(bundle)

    assert [d for d in diagnostics if d.level == "warning"] == []
    assert len(imported.links) == len(graph.links)


def test_round_trip_preserves_relations_and_confidences_multiset() -> None:
    graph = _tiny_graph()
    bundle = export(graph)
    imported, _ = import_bundle(bundle)

    original = sorted((e.source, e.target, e.relation, e.confidence) for e in graph.links)
    round_tripped = sorted(
        (e.source, e.target, e.relation, e.confidence) for e in imported.links
    )
    assert original == round_tripped
