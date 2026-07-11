"""Phase 1 DoD: `okf-bridge validate <bundle-dir>` exits 0 on a conformant
bundle, exits non-zero on hard violations, and `--strict` promotes warnings.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from graphify_okf_bridge.cli import main

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_validate_ga4_exits_zero() -> None:
    result = CliRunner().invoke(main, ["validate", str(FIXTURES / "okf_official" / "ga4")])
    assert result.exit_code == 0, result.output


def test_validate_okf_minimal_exits_zero_without_strict() -> None:
    result = CliRunner().invoke(main, ["validate", str(FIXTURES / "okf_minimal")])
    assert result.exit_code == 0, result.output


def test_validate_okf_minimal_exits_nonzero_with_strict() -> None:
    result = CliRunner().invoke(
        main, ["validate", str(FIXTURES / "okf_minimal"), "--strict"]
    )
    assert result.exit_code != 0


def test_validate_bundle_with_missing_type_exits_nonzero(tmp_path: Path) -> None:
    (tmp_path / "thing.md").write_text("---\ntitle: No Type\n---\nbody\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["validate", str(tmp_path)])
    assert result.exit_code != 0
