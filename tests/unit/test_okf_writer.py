"""Phase 1 acceptance tests: okf/writer.py.

Determinism (byte-identical re-runs), frontmatter emission (`type` first),
and the slug registry (bijective, collision-suffixed).
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from graphify_okf_bridge.okf.model import Bundle, Concept, TypedLink
from graphify_okf_bridge.okf.writer import SlugRegistry, slugify, write_bundle


def _sample_bundle(root: Path) -> Bundle:
    return Bundle(
        root=root,
        okf_version="0.1",
        concepts={
            "tables/orders": Concept(
                concept_id="tables/orders",
                type="BigQuery Table",
                title="Orders",
                description="One row per order.",
                tags=["sales", "orders"],
                extra_frontmatter={"graphify_node_id": "app_models_order"},
                body="# Schema\n\nSee [customers](/tables/customers.md).\n",
                typed_links=[
                    TypedLink(target="tables/customers", rel="references", confidence="extracted")
                ],
            ),
            "tables/customers": Concept(
                concept_id="tables/customers",
                type="BigQuery Table",
                title="Customers",
                body="body\n",
            ),
        },
    )


def _tree_contents(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): p.read_text(encoding="utf-8")
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_write_bundle_is_byte_identical_across_runs(tmp_path: Path) -> None:
    bundle_a = _sample_bundle(tmp_path / "src")
    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    write_bundle(bundle_a, out_a)
    write_bundle(bundle_a, out_b)
    assert _tree_contents(out_a) == _tree_contents(out_b)


def test_write_bundle_emits_type_first_in_frontmatter(tmp_path: Path) -> None:
    bundle = _sample_bundle(tmp_path / "src")
    out = tmp_path / "out"
    write_bundle(bundle, out)
    text = (out / "tables" / "orders.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "---"
    assert lines[1].startswith("type:")


def test_write_bundle_generates_root_index_with_okf_version(tmp_path: Path) -> None:
    bundle = _sample_bundle(tmp_path / "src")
    out = tmp_path / "out"
    write_bundle(bundle, out)
    text = (out / "index.md").read_text(encoding="utf-8")
    assert 'okf_version: "0.1"' in text or "okf_version: '0.1'" in text


def test_write_bundle_generates_directory_indexes(tmp_path: Path) -> None:
    bundle = _sample_bundle(tmp_path / "src")
    out = tmp_path / "out"
    write_bundle(bundle, out)
    assert (out / "tables" / "index.md").exists()


def test_write_bundle_preserves_typed_links_in_frontmatter(tmp_path: Path) -> None:
    bundle = _sample_bundle(tmp_path / "src")
    out = tmp_path / "out"
    write_bundle(bundle, out)
    text = (out / "tables" / "orders.md").read_text(encoding="utf-8")
    assert "links:" in text
    assert "rel: references" in text


def test_slugify_produces_lowercase_hyphenated_slug() -> None:
    assert slugify("Customer Orders!!") == "customer-orders"
    assert slugify("  spaced__out  ") == "spaced-out"


def test_slug_registry_resolves_collisions_deterministically() -> None:
    registry = SlugRegistry()
    first = registry.register("orders")
    second = registry.register("orders")
    third = registry.register("orders")
    assert first == "orders"
    assert second == "orders-2"
    assert third == "orders-3"


def test_slug_registry_is_bijective_across_distinct_ids() -> None:
    registry = SlugRegistry()
    a = registry.register("orders", node_id="node-a")
    b = registry.register("orders", node_id="node-b")
    assert a != b
    assert registry.slug_for("node-a") == a
    assert registry.slug_for("node-b") == b


@given(st.text(min_size=1, max_size=40))
def test_slugify_is_idempotent_and_url_safe(text: str) -> None:
    slug = slugify(text)
    assert slug == slugify(slug)
    assert all(c.islower() or c.isdigit() or c == "-" for c in slug)
    assert not slug.startswith("-")
    assert not slug.endswith("-")
