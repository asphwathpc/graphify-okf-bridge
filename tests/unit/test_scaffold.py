"""Phase 0 scaffold tests: fixtures exist and parse, CLI entrypoint works."""

from __future__ import annotations

from pathlib import Path

import frontmatter
from click.testing import CliRunner

from graphify_okf_bridge import __version__
from graphify_okf_bridge.cli import main

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_version() -> None:
    assert __version__


def test_cli_help_lists_all_commands() -> None:
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    for cmd in ("validate", "export", "import", "link"):
        assert cmd in result.output


def test_remaining_subcommand_stubbed_not_broken(tmp_path: Path) -> None:
    """`validate`/`export`/`import` are implemented as of Phase 1/2/3; `link` remains a stub."""
    result = CliRunner().invoke(
        main,
        [
            "link",
            str(FIXTURES / "tiny_graph.json"),
            str(FIXTURES / "okf_minimal"),
            "-o",
            str(tmp_path / "out.json"),
        ],
    )
    assert result.exit_code != 0
    assert "not implemented" in result.output


def test_import_subcommand_is_implemented(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        main, ["import", str(FIXTURES / "okf_minimal"), "-o", str(tmp_path / "out.json")]
    )
    assert result.exit_code == 0, result.output


def test_okf_minimal_fixture_is_conformant() -> None:
    """Every non-reserved .md in the minimal bundle has frontmatter with a type (spec section 9)."""
    bundle = FIXTURES / "okf_minimal"
    concept_files = [
        p for p in bundle.rglob("*.md") if p.name not in ("index.md", "log.md")
    ]
    assert concept_files, "okf_minimal fixture is missing concept documents"
    for path in concept_files:
        post = frontmatter.loads(path.read_text(encoding="utf-8"))
        assert post.metadata.get("type"), f"{path} has no non-empty 'type'"


def test_tiny_repo_fixture_has_linker_cases() -> None:
    """tiny_repo must contain the known-answer linker signals (see IMPLEMENTATION_PLAN Phase 4)."""
    repo = FIXTURES / "tiny_repo"
    sql = (repo / "analytics" / "orders_model.sql").read_text(encoding="utf-8")
    assert "ref(" in sql  # dbt ref signal
    service = (repo / "app" / "service.py").read_text(encoding="utf-8")
    assert "FROM" in service  # SQL literal signal
    assert "# WHY:" in service  # rationale node signal
