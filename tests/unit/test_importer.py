"""Phase 3 acceptance tests: importer.py (OKF bundle -> graph.json).

MAPPING.md §Import (I1-I7) is normative. Hand-built `Bundle` fixtures here
mirror tests/roundtrip/test_bundle_roundtrip.py's style; the official
bundles (tests/fixtures/okf_official) are exercised as permissive-import
ground truth (I5).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from graphify_okf_bridge.importer import import_bundle
from graphify_okf_bridge.okf.model import Bundle, Concept, Link, TypedLink
from graphify_okf_bridge.okf.reader import read_bundle

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _bundle(root: Path, concepts: dict[str, Concept]) -> Bundle:
    return Bundle(root=root, okf_version="0.1", concepts=concepts)


def test_concept_with_graphify_node_id_recovers_original_id(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {
            "code/foo": Concept(
                concept_id="code/foo",
                type="Code",
                title="foo",
                extra_frontmatter={"graphify_node_id": "app_foo"},
            )
        },
    )
    graph, diagnostics = import_bundle(bundle)

    assert [d for d in diagnostics if d.level == "error"] == []
    assert len(graph.nodes) == 1
    assert graph.nodes[0].id == "app_foo"


def test_concept_without_graphify_node_id_gets_okf_prefixed_id(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {
            "datasets/sales": Concept(concept_id="datasets/sales", type="BigQuery Dataset"),
        },
    )
    graph, _ = import_bundle(bundle)

    assert graph.nodes[0].id == "okf:datasets/sales"


def test_type_becomes_lowercased_file_type(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {"code/foo": Concept(concept_id="code/foo", type="Code")},
    )
    graph, _ = import_bundle(bundle)

    assert graph.nodes[0].file_type == "code"
    assert graph.nodes[0].model_extra is not None
    assert graph.nodes[0].model_extra["okf_type"] == "Code"


def test_file_resource_splits_into_source_file_and_location(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {
            "code/foo": Concept(
                concept_id="code/foo",
                type="Code",
                resource="file://app/foo.py#L12",
            )
        },
    )
    graph, _ = import_bundle(bundle)

    node = graph.nodes[0]
    assert node.source_file == "app/foo.py"
    assert node.source_location == "L12"


def test_file_resource_without_fragment_has_no_source_location(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {"code/foo": Concept(concept_id="code/foo", type="Code", resource="file://app/foo.py")},
    )
    graph, _ = import_bundle(bundle)

    assert graph.nodes[0].source_file == "app/foo.py"
    assert graph.nodes[0].source_location is None


def test_non_file_resource_is_carried_verbatim_as_source_file(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {
            "datasets/sales": Concept(
                concept_id="datasets/sales",
                type="BigQuery Dataset",
                resource="https://bigquery.googleapis.com/sales",
            )
        },
    )
    graph, _ = import_bundle(bundle)

    assert graph.nodes[0].source_file == "https://bigquery.googleapis.com/sales"
    assert graph.nodes[0].source_location is None


def test_missing_resource_falls_back_to_okf_prefixed_source_file(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {"concept/x": Concept(concept_id="concept/x", type="Concept")},
    )
    graph, _ = import_bundle(bundle)

    assert graph.nodes[0].source_file == "okf:concept/x"


def test_community_tag_becomes_community_int(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {
            "code/foo": Concept(
                concept_id="code/foo", type="Code", tags=["community:3", "ecommerce"]
            )
        },
    )
    graph, _ = import_bundle(bundle)

    node = graph.nodes[0]
    assert node.community == 3
    assert node.model_extra is not None
    assert node.model_extra["okf_tags"] == ["ecommerce"]


def test_typed_link_becomes_edge_with_uppercased_confidence(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {
            "code/foo": Concept(
                concept_id="code/foo",
                type="Code",
                extra_frontmatter={"graphify_node_id": "foo"},
                typed_links=[TypedLink(target="code/bar", rel="calls", confidence="extracted")],
                links=[Link(target="code/bar", text="calls", bundle_relative=True)],
            ),
            "code/bar": Concept(
                concept_id="code/bar", type="Code", extra_frontmatter={"graphify_node_id": "bar"}
            ),
        },
    )
    graph, diagnostics = import_bundle(bundle)

    assert [d for d in diagnostics if d.level == "warning"] == []
    assert len(graph.links) == 1
    edge = graph.links[0]
    assert (edge.source, edge.target) == ("foo", "bar")
    assert edge.relation == "calls"
    assert edge.confidence == "EXTRACTED"


def test_plain_body_link_without_typed_entry_becomes_references_extracted(
    tmp_path: Path,
) -> None:
    bundle = _bundle(
        tmp_path,
        {
            "code/foo": Concept(
                concept_id="code/foo",
                type="Code",
                links=[Link(target="code/bar", text="see also", bundle_relative=True)],
            ),
            "code/bar": Concept(concept_id="code/bar", type="Code"),
        },
    )
    graph, _ = import_bundle(bundle)

    assert len(graph.links) == 1
    edge = graph.links[0]
    assert edge.relation == "references"
    assert edge.confidence == "EXTRACTED"


def test_plain_body_link_matching_a_typed_target_is_not_duplicated(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {
            "code/foo": Concept(
                concept_id="code/foo",
                type="Code",
                typed_links=[TypedLink(target="code/bar", rel="calls", confidence="extracted")],
                links=[Link(target="code/bar", text="calls", bundle_relative=True)],
            ),
            "code/bar": Concept(concept_id="code/bar", type="Code"),
        },
    )
    graph, _ = import_bundle(bundle)

    assert len(graph.links) == 1


def test_broken_typed_link_dropped_with_warning(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {
            "code/foo": Concept(
                concept_id="code/foo",
                type="Code",
                typed_links=[
                    TypedLink(target="code/missing", rel="calls", confidence="extracted")
                ],
            ),
        },
    )
    graph, diagnostics = import_bundle(bundle)

    assert graph.links == []
    warnings = [d for d in diagnostics if d.level == "warning"]
    assert len(warnings) == 1
    assert "code/missing" in warnings[0].message


def test_broken_plain_link_dropped_with_warning(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {
            "code/foo": Concept(
                concept_id="code/foo",
                type="Code",
                links=[Link(target="code/missing", text="see", bundle_relative=True)],
            ),
        },
    )
    graph, diagnostics = import_bundle(bundle)

    assert graph.links == []
    assert len([d for d in diagnostics if d.level == "warning"]) == 1


def test_synthetic_overview_concept_excluded_from_import(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        {
            "overview": Concept(concept_id="overview", type="Overview", title="Graph Overview"),
            "code/foo": Concept(
                concept_id="code/foo",
                type="Code",
                extra_frontmatter={"graphify_node_id": "foo"},
            ),
        },
    )
    graph, _ = import_bundle(bundle)

    assert len(graph.nodes) == 1
    assert graph.nodes[0].id == "foo"


def test_foreign_overview_concept_with_graphify_node_id_is_not_excluded(tmp_path: Path) -> None:
    """Only the exporter's own synthetic marker (no graphify_node_id) is excluded."""
    bundle = _bundle(
        tmp_path,
        {
            "overview": Concept(
                concept_id="overview",
                type="Overview",
                extra_frontmatter={"graphify_node_id": "real_overview_node"},
            ),
        },
    )
    graph, _ = import_bundle(bundle)

    assert len(graph.nodes) == 1


def test_output_graph_shape_is_graphify_compatible(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, {"code/foo": Concept(concept_id="code/foo", type="Code")})
    graph, _ = import_bundle(bundle)

    assert graph.directed is False
    assert graph.multigraph is False
    assert graph.hyperedges == []


@pytest.mark.parametrize("name", ["ga4", "crypto_bitcoin", "stackoverflow"])
def test_official_bundles_import_cleanly(name: str) -> None:
    bundle, read_diagnostics = read_bundle(FIXTURES / "okf_official" / name)
    assert [d for d in read_diagnostics if d.level == "error"] == []

    graph, import_diagnostics = import_bundle(bundle)

    assert [d for d in import_diagnostics if d.level == "error"] == []
    assert len(graph.nodes) == len(bundle.concepts)
    assert {n.id for n in graph.nodes} == {f"okf:{cid}" for cid in bundle.concepts}
