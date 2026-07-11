"""Phase 2 DoD: `okf-bridge export graph.json -o bundle-dir` produces a bundle
that `okf-bridge validate` accepts with zero errors (see IMPLEMENTATION_PLAN.md
Phase 2 step 5)."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from graphify_okf_bridge.cli import main

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_export_then_validate_exits_zero(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "tiny_bundle"
    export_result = CliRunner().invoke(
        main, ["export", str(FIXTURES / "tiny_graph.json"), "-o", str(bundle_dir)]
    )
    assert export_result.exit_code == 0, export_result.output

    validate_result = CliRunner().invoke(main, ["validate", str(bundle_dir), "--strict"])
    assert validate_result.exit_code == 0, validate_result.output


def test_export_creates_expected_directories(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "tiny_bundle"
    CliRunner().invoke(main, ["export", str(FIXTURES / "tiny_graph.json"), "-o", str(bundle_dir)])

    assert (bundle_dir / "code").is_dir()
    assert (bundle_dir / "rationale").is_dir()
    assert (bundle_dir / "concept").is_dir()
    assert (bundle_dir / "overview.md").exists()
    assert (bundle_dir / "index.md").exists()
