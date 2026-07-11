"""Phase 1 acceptance tests: okf/reader.py.

Frontmatter edge cases, link extraction, reserved-filename handling.
Reading NEVER raises — violations are collected as Diagnostics (OKF §9
permissive consumption, ground rule 5).
"""

from __future__ import annotations

from pathlib import Path

from graphify_okf_bridge.okf.model import TypedLink
from graphify_okf_bridge.okf.reader import read_bundle

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_missing_type_is_an_error(tmp_path: Path) -> None:
    _write(tmp_path, "concepts/thing.md", "---\ntitle: No Type Here\n---\nbody\n")
    bundle, diagnostics = read_bundle(tmp_path)
    assert bundle.concepts["concepts/thing"].type == ""
    errors = [d for d in diagnostics if d.level == "error"]
    assert any("type" in d.message.lower() for d in errors)


def test_empty_type_is_an_error(tmp_path: Path) -> None:
    _write(tmp_path, "concepts/thing.md", "---\ntype: ''\n---\nbody\n")
    _bundle, diagnostics = read_bundle(tmp_path)
    errors = [d for d in diagnostics if d.level == "error"]
    assert any("type" in d.message.lower() for d in errors)


def test_unknown_frontmatter_keys_are_preserved(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "concepts/thing.md",
        "---\ntype: Widget\nsome_future_key: kept\n---\nbody\n",
    )
    bundle, diagnostics = read_bundle(tmp_path)
    assert bundle.concepts["concepts/thing"].extra_frontmatter["some_future_key"] == "kept"
    assert not [d for d in diagnostics if d.level == "error"]


def test_empty_file_is_an_error(tmp_path: Path) -> None:
    _write(tmp_path, "concepts/empty.md", "")
    _bundle, diagnostics = read_bundle(tmp_path)
    errors = [d for d in diagnostics if d.level == "error"]
    assert any("empty.md" in d.path for d in errors)


def test_body_only_file_is_an_error(tmp_path: Path) -> None:
    _write(tmp_path, "concepts/prose.md", "Just some markdown prose, no frontmatter at all.\n")
    _bundle, diagnostics = read_bundle(tmp_path)
    errors = [d for d in diagnostics if d.level == "error"]
    assert any("prose.md" in d.path for d in errors)


def test_unparseable_yaml_frontmatter_is_an_error_not_an_exception(tmp_path: Path) -> None:
    _write(tmp_path, "concepts/bad.md", "---\ntype: [unterminated\n---\nbody\n")
    bundle, diagnostics = read_bundle(tmp_path)
    errors = [d for d in diagnostics if d.level == "error"]
    assert any("bad.md" in d.path for d in errors)
    # the file is still surfaced, not silently dropped
    assert "concepts/bad" in bundle.concepts


def test_index_md_is_not_treated_as_a_concept(tmp_path: Path) -> None:
    _write(tmp_path, "index.md", '---\nokf_version: "0.1"\n---\n\n# Root\n')
    _write(tmp_path, "concepts/index.md", "# Concepts\n\n* [thing](thing.md) - a thing\n")
    _write(tmp_path, "concepts/thing.md", "---\ntype: Widget\n---\nbody\n")
    bundle, _diagnostics = read_bundle(tmp_path)
    assert "index" not in bundle.concepts
    assert "concepts/index" not in bundle.concepts
    assert set(bundle.concepts) == {"concepts/thing"}


def test_log_md_is_not_treated_as_a_concept(tmp_path: Path) -> None:
    _write(tmp_path, "log.md", "# Log\n\n## 2026-07-11\n* **Creation**: seed\n")
    _write(tmp_path, "thing.md", "---\ntype: Widget\n---\nbody\n")
    bundle, _diagnostics = read_bundle(tmp_path)
    assert "log" not in bundle.concepts


def test_root_index_okf_version_is_parsed(tmp_path: Path) -> None:
    _write(tmp_path, "index.md", '---\nokf_version: "0.1"\n---\n\n# Root\n')
    bundle, _diagnostics = read_bundle(tmp_path)
    assert bundle.okf_version == "0.1"


def test_okf_version_defaults_to_none_when_absent(tmp_path: Path) -> None:
    _write(tmp_path, "thing.md", "---\ntype: Widget\n---\nbody\n")
    bundle, _diagnostics = read_bundle(tmp_path)
    assert bundle.okf_version is None


def test_absolute_bundle_relative_link_is_resolved(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "tables/orders.md",
        "---\ntype: Table\n---\nSee [customers](/tables/customers.md).\n",
    )
    _write(tmp_path, "tables/customers.md", "---\ntype: Table\n---\nbody\n")
    bundle, _diagnostics = read_bundle(tmp_path)
    links = bundle.concepts["tables/orders"].links
    assert len(links) == 1
    assert links[0].target == "tables/customers"
    assert links[0].bundle_relative is True
    assert links[0].text == "customers"


def test_relative_link_is_resolved_against_source_directory(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "tables/inputs.md",
        "---\ntype: Table\n---\nJoins [outputs](outputs.md) and [ds](../datasets/ds.md).\n",
    )
    _write(tmp_path, "tables/outputs.md", "---\ntype: Table\n---\nbody\n")
    _write(tmp_path, "datasets/ds.md", "---\ntype: Dataset\n---\nbody\n")
    bundle, _diagnostics = read_bundle(tmp_path)
    targets = {link.target for link in bundle.concepts["tables/inputs"].links}
    assert targets == {"tables/outputs", "datasets/ds"}
    for link in bundle.concepts["tables/inputs"].links:
        assert link.bundle_relative is False


def test_link_with_anchor_fragment_strips_fragment(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "---\ntype: T\n---\nSee [b](/b.md#schema).\n")
    _write(tmp_path, "b.md", "---\ntype: T\n---\nbody\n")
    bundle, _diagnostics = read_bundle(tmp_path)
    assert bundle.concepts["a"].links[0].target == "b"


def test_broken_link_target_is_tolerated_not_raised(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "---\ntype: T\n---\nSee [ghost](/nowhere.md).\n")
    bundle, diagnostics = read_bundle(tmp_path)
    assert bundle.concepts["a"].links[0].target == "nowhere"
    assert not [d for d in diagnostics if d.level == "error"]


def test_external_url_link_is_not_extracted_as_a_concept_link(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "---\ntype: T\n---\nSee [docs](https://example.com/x).\n")
    bundle, _diagnostics = read_bundle(tmp_path)
    assert bundle.concepts["a"].links == []


def test_typed_links_frontmatter_extension_is_parsed(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.md",
        "---\n"
        "type: T\n"
        "links:\n"
        "  - target: /b.md\n"
        "    rel: calls\n"
        "    confidence: extracted\n"
        "---\n"
        "body\n",
    )
    _write(tmp_path, "b.md", "---\ntype: T\n---\nbody\n")
    bundle, _diagnostics = read_bundle(tmp_path)
    typed = bundle.concepts["a"].typed_links
    assert typed == [TypedLink(target="b", rel="calls", confidence="extracted")]


def test_recognized_frontmatter_fields_are_mapped_not_duplicated(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.md",
        "---\n"
        "type: Table\n"
        "title: A Title\n"
        "description: A description.\n"
        "resource: https://example.com/a\n"
        "tags: [x, y]\n"
        "timestamp: 2026-05-28T00:00:00Z\n"
        "---\n"
        "body text\n",
    )
    bundle, _diagnostics = read_bundle(tmp_path)
    concept = bundle.concepts["a"]
    assert concept.title == "A Title"
    assert concept.description == "A description."
    assert concept.resource == "https://example.com/a"
    assert concept.tags == ["x", "y"]
    # PyYAML auto-parses an unquoted ISO 8601 scalar into a datetime.datetime;
    # we normalize it back to an ISO string, but "Z" becomes "+00:00".
    assert concept.timestamp == "2026-05-28T00:00:00+00:00"
    assert concept.body.strip() == "body text"
    assert "title" not in concept.extra_frontmatter
    assert "description" not in concept.extra_frontmatter


def test_official_bundles_load_with_zero_errors() -> None:
    for name in ("ga4", "crypto_bitcoin", "stackoverflow"):
        bundle, diagnostics = read_bundle(FIXTURES / "okf_official" / name)
        errors = [d for d in diagnostics if d.level == "error"]
        assert errors == [], f"{name}: unexpected errors {errors}"
        assert bundle.concepts


def test_okf_minimal_fixture_has_one_intentionally_broken_link() -> None:
    bundle, diagnostics = read_bundle(FIXTURES / "okf_minimal")
    assert not [d for d in diagnostics if d.level == "error"]
    customers = bundle.concepts["tables/customers"]
    targets = {link.target for link in customers.links}
    assert "models/churn" in targets
