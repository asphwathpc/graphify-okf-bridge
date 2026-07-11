"""Phase 2 acceptance tests: exporter.py (graph.json -> OKF bundle).

MAPPING.md §Export (E1-E11) is normative. `tests/fixtures/tiny_graph.json`
is real graphify output (see §1) -- assertions here are grounded in its
actual node/edge shape, not an assumed one.
"""

from __future__ import annotations

from pathlib import Path

from graphify_okf_bridge.exporter import export
from graphify_okf_bridge.graphify_io.loader import load_graph
from graphify_okf_bridge.okf.reader import read_bundle
from graphify_okf_bridge.okf.validator import validate
from graphify_okf_bridge.okf.writer import write_bundle

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _tiny_graph():
    return load_graph(FIXTURES / "tiny_graph.json")


def test_every_node_maps_to_exactly_one_concept() -> None:
    graph = _tiny_graph()
    bundle = export(graph)

    # +1 for the E11 overview.md concept.
    assert len(bundle.concepts) == len(graph.nodes) + 1


def test_concept_ids_are_bijective_with_node_ids() -> None:
    graph = _tiny_graph()
    bundle = export(graph)

    node_ids_by_graphify_id = {
        c.extra_frontmatter["graphify_node_id"]: cid
        for cid, c in bundle.concepts.items()
        if "graphify_node_id" in c.extra_frontmatter
    }
    assert len(node_ids_by_graphify_id) == len(graph.nodes)
    assert set(node_ids_by_graphify_id) == {n.id for n in graph.nodes}


def test_concept_directory_matches_file_type() -> None:
    graph = _tiny_graph()
    bundle = export(graph)

    by_node_id = {n.id: n for n in graph.nodes}
    for concept in bundle.concepts.values():
        node_id = concept.extra_frontmatter.get("graphify_node_id")
        if node_id is None:
            continue  # overview.md
        node = by_node_id[node_id]
        assert concept.concept_id.startswith(f"{node.file_type}/")
        assert concept.type == node.file_type.title()


def test_graphify_node_id_present_on_every_node_concept() -> None:
    graph = _tiny_graph()
    bundle = export(graph)

    node_concepts = [
        c for c in bundle.concepts.values() if "graphify_node_id" in c.extra_frontmatter
    ]
    assert len(node_concepts) == len(graph.nodes)


def test_resource_includes_source_location_when_present() -> None:
    graph = _tiny_graph()
    bundle = export(graph)

    node = next(n for n in graph.nodes if n.id == "app_models_basemodel")
    concept = next(
        c
        for c in bundle.concepts.values()
        if c.extra_frontmatter.get("graphify_node_id") == node.id
    )
    assert concept.resource == f"file://{node.source_file}#{node.source_location}"


def test_resource_omits_fragment_when_source_location_missing() -> None:
    graph = _tiny_graph()
    bundle = export(graph)

    node = next(n for n in graph.nodes if n.id == "docs_adr_0001_orders_table")
    assert node.source_location is None
    concept = next(
        c
        for c in bundle.concepts.values()
        if c.extra_frontmatter.get("graphify_node_id") == node.id
    )
    assert concept.resource == f"file://{node.source_file}"


def test_community_becomes_tag() -> None:
    graph = _tiny_graph()
    bundle = export(graph)

    node = next(n for n in graph.nodes if n.id == "app_models_basemodel")
    concept = next(
        c
        for c in bundle.concepts.values()
        if c.extra_frontmatter.get("graphify_node_id") == node.id
    )
    assert f"community:{node.community}" in concept.tags


def test_rationale_label_becomes_body() -> None:
    graph = _tiny_graph()
    bundle = export(graph)

    node = next(n for n in graph.nodes if n.id == "app_models_rationale_1")
    concept = next(
        c
        for c in bundle.concepts.values()
        if c.extra_frontmatter.get("graphify_node_id") == node.id
    )
    assert node.label in concept.body


def test_every_edge_appears_as_typed_link_and_body_link() -> None:
    graph = _tiny_graph()
    bundle = export(graph)

    concept_id_by_node_id = {
        c.extra_frontmatter["graphify_node_id"]: cid
        for cid, c in bundle.concepts.items()
        if "graphify_node_id" in c.extra_frontmatter
    }

    for edge in graph.links:
        source_concept = bundle.concepts[concept_id_by_node_id[edge.source]]
        target_concept_id = concept_id_by_node_id[edge.target]

        matching_typed = [
            tl
            for tl in source_concept.typed_links
            if tl.target == target_concept_id and tl.rel == edge.relation
        ]
        assert matching_typed, f"missing typed link for edge {edge.source}->{edge.target}"
        assert matching_typed[0].confidence == edge.confidence.lower()

        assert f"/{target_concept_id}.md" in source_concept.body


def test_export_is_deterministic(tmp_path: Path) -> None:
    graph = _tiny_graph()
    bundle_a = export(graph)
    bundle_b = export(graph)

    out_a, out_b = tmp_path / "a", tmp_path / "b"
    write_bundle(bundle_a, out_a)
    write_bundle(bundle_b, out_b)

    files_a = sorted(p.relative_to(out_a) for p in out_a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(out_b) for p in out_b.rglob("*") if p.is_file())
    assert files_a == files_b
    for rel in files_a:
        assert (out_a / rel).read_bytes() == (out_b / rel).read_bytes()


def test_exported_bundle_passes_strict_validation(tmp_path: Path) -> None:
    graph = _tiny_graph()
    bundle = export(graph)
    out_dir = tmp_path / "bundle"
    write_bundle(bundle, out_dir)

    reread, diagnostics = read_bundle(out_dir)
    report = validate(reread, diagnostics)

    assert report.ok(strict=True), [d.message for d in [*report.errors, *report.warnings]]


def test_every_concept_has_a_description() -> None:
    """MAPPING.md E6b: strict validate (ground rule 5) requires no missing-description
    warnings, so every concept -- including overview.md -- must carry one."""
    graph = _tiny_graph()
    bundle = export(graph)

    for concept in bundle.concepts.values():
        assert concept.description


def test_overview_concept_present_at_bundle_root() -> None:
    graph = _tiny_graph()
    bundle = export(graph)

    assert "overview" in bundle.concepts
    overview = bundle.concepts["overview"]
    assert overview.type == "Overview"
    assert str(len(graph.nodes)) in overview.body
    assert str(len(graph.links)) in overview.body
