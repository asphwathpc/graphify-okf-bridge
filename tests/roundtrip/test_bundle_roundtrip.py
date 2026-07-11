"""Round-trip invariant (IMPLEMENTATION_PLAN.md §Test strategy):
`reader(writer(b)) == b` for bundles — concepts, frontmatter, links, and
typed links survive a write/read cycle unchanged (titles/slugs are already
final at this layer, so no normalization is expected here).
"""

from __future__ import annotations

from pathlib import Path

from graphify_okf_bridge.okf.model import Bundle, Concept, Link, TypedLink
from graphify_okf_bridge.okf.reader import read_bundle
from graphify_okf_bridge.okf.writer import write_bundle


def _make_bundle(root: Path) -> Bundle:
    # `.links` mirrors what the reader would extract from `.body` — it is
    # derived data, not independent state, so hand-built fixtures must keep
    # the two in sync themselves (the exporter will do this in Phase 2).
    return Bundle(
        root=root,
        okf_version="0.1",
        concepts={
            "tables/orders": Concept(
                concept_id="tables/orders",
                type="BigQuery Table",
                title="Orders",
                description="One row per order.",
                resource="https://example.com/orders",
                tags=["sales", "orders"],
                timestamp="2026-07-11T00:00:00Z",
                extra_frontmatter={"graphify_node_id": "app_models_order"},
                body="# Schema\n\nSee [customers](/tables/customers.md) for the FK.\n",
                links=[Link(target="tables/customers", text="customers", bundle_relative=True)],
                typed_links=[
                    TypedLink(target="tables/customers", rel="references", confidence="extracted")
                ],
            ),
            "tables/customers": Concept(
                concept_id="tables/customers",
                type="BigQuery Table",
                title="Customers",
                body="Referenced by [orders](../tables/orders.md).\n",
                links=[Link(target="tables/orders", text="orders", bundle_relative=False)],
            ),
        },
    )


def test_reader_of_writer_preserves_concepts_and_okf_version(tmp_path: Path) -> None:
    original = _make_bundle(tmp_path / "in-memory")
    out_dir = tmp_path / "bundle"
    write_bundle(original, out_dir)

    reread, diagnostics = read_bundle(out_dir)

    assert [d for d in diagnostics if d.level == "error"] == []
    assert reread.okf_version == original.okf_version
    assert set(reread.concepts) == set(original.concepts)

    for concept_id, original_concept in original.concepts.items():
        reread_concept = reread.concepts[concept_id]
        assert reread_concept.type == original_concept.type
        assert reread_concept.title == original_concept.title
        assert reread_concept.description == original_concept.description
        assert reread_concept.resource == original_concept.resource
        assert reread_concept.tags == original_concept.tags
        assert reread_concept.timestamp == original_concept.timestamp
        assert reread_concept.extra_frontmatter == original_concept.extra_frontmatter
        assert reread_concept.typed_links == original_concept.typed_links
        assert {link.target for link in reread_concept.links} == {
            link.target for link in original_concept.links
        }


def test_writing_twice_produces_byte_identical_trees(tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path / "in-memory")
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    write_bundle(bundle, out_a)
    write_bundle(bundle, out_b)

    files_a = sorted(p.relative_to(out_a) for p in out_a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(out_b) for p in out_b.rglob("*") if p.is_file())
    assert files_a == files_b
    for rel in files_a:
        assert (out_a / rel).read_bytes() == (out_b / rel).read_bytes()
