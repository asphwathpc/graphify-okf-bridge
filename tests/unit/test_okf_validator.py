"""Phase 1 acceptance tests: okf/validator.py.

Hard checks (§9) become errors; soft guidance becomes warnings; `--strict`
promotion is a caller-level decision (ValidationReport.ok(strict=...)).
"""

from __future__ import annotations

from pathlib import Path

from graphify_okf_bridge.okf.model import Bundle, Concept, TypedLink
from graphify_okf_bridge.okf.reader import read_bundle
from graphify_okf_bridge.okf.validator import validate

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_official_bundles_pass_validation_with_zero_errors() -> None:
    for name in ("ga4", "crypto_bitcoin", "stackoverflow"):
        bundle, diagnostics = read_bundle(FIXTURES / "okf_official" / name)
        report = validate(bundle, diagnostics)
        assert report.errors == [], f"{name}: {report.errors}"
        assert report.ok(strict=False)


def test_okf_minimal_broken_link_is_a_warning_not_an_error() -> None:
    bundle, diagnostics = read_bundle(FIXTURES / "okf_minimal")
    report = validate(bundle, diagnostics)
    assert report.errors == []
    assert any("nowhere" in w.message or "churn" in w.message for w in report.warnings)
    assert report.ok(strict=False)
    assert not report.ok(strict=True)


def test_missing_type_produces_error_and_fails_strict_and_lenient(tmp_path: Path) -> None:
    (tmp_path / "thing.md").write_text("---\ntitle: No Type\n---\nbody\n", encoding="utf-8")
    bundle, diagnostics = read_bundle(tmp_path)
    report = validate(bundle, diagnostics)
    assert report.errors != []
    assert not report.ok(strict=False)
    assert not report.ok(strict=True)


def test_missing_description_is_a_soft_warning(tmp_path: Path) -> None:
    (tmp_path / "thing.md").write_text("---\ntype: Widget\n---\nbody\n", encoding="utf-8")
    bundle, diagnostics = read_bundle(tmp_path)
    report = validate(bundle, diagnostics)
    assert report.errors == []
    assert any("description" in w.message.lower() for w in report.warnings)


def test_broken_typed_link_target_is_a_soft_warning() -> None:
    concept = Concept(
        concept_id="code/thing",
        type="code",
        description="d",
        typed_links=[TypedLink(target="code/nowhere", rel="references", confidence="INFERRED")],
    )
    bundle = Bundle(root=Path("."), concepts={"code/thing": concept})
    report = validate(bundle)
    assert report.errors == []
    assert any("code/nowhere" in w.message for w in report.warnings)


def test_missing_index_is_a_soft_warning(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "thing.md").write_text(
        "---\ntype: Widget\ndescription: d\n---\nbody\n", encoding="utf-8"
    )
    bundle, diagnostics = read_bundle(tmp_path)
    report = validate(bundle, diagnostics)
    assert report.errors == []
    assert any("index" in w.message.lower() for w in report.warnings)


def test_missing_okf_version_is_a_soft_warning() -> None:
    bundle = Bundle(root=Path("."), concepts={}, okf_version=None)
    report = validate(bundle)
    assert report.errors == []
    version_warnings = [w for w in report.warnings if "okf_version" in w.message]
    assert len(version_warnings) == 1
    assert version_warnings[0].path == "index.md"


def test_present_okf_version_produces_no_warning() -> None:
    bundle = Bundle(root=Path("."), concepts={}, okf_version="0.1")
    report = validate(bundle)
    assert report.errors == []
    assert not any("okf_version" in w.message for w in report.warnings)
