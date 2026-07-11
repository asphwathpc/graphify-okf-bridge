"""Phase 5a DoD: `okf-bridge install-skill` copies skill/SKILL.md into the
user's Claude Code skills directory and registers it in CLAUDE.md, mirroring
graphify's own `graphify install` mechanism (see IMPLEMENTATION_PLAN.md Phase 5
step 5a: "read graphify install's implementation first")."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from graphify_okf_bridge.cli import main


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


def test_install_skill_user_scope_copies_skill_file(fake_home: Path) -> None:
    result = CliRunner().invoke(main, ["install-skill"])
    assert result.exit_code == 0, result.output

    dst = fake_home / ".claude" / "skills" / "okf-bridge" / "SKILL.md"
    assert dst.is_file()
    assert dst.read_text(encoding="utf-8").startswith("---\n")


def test_install_skill_user_scope_registers_in_claude_md(fake_home: Path) -> None:
    CliRunner().invoke(main, ["install-skill"])

    claude_md = fake_home / ".claude" / "CLAUDE.md"
    assert claude_md.is_file()
    content = claude_md.read_text(encoding="utf-8")
    assert "okf-bridge" in content
    assert "~/.claude/skills/okf-bridge/SKILL.md" in content


def test_install_skill_is_idempotent(fake_home: Path) -> None:
    CliRunner().invoke(main, ["install-skill"])
    claude_md = fake_home / ".claude" / "CLAUDE.md"
    first = claude_md.read_text(encoding="utf-8")

    result = CliRunner().invoke(main, ["install-skill"])
    assert result.exit_code == 0, result.output
    second = claude_md.read_text(encoding="utf-8")

    assert first == second
    assert second.count("# okf-bridge") == 1


def test_install_skill_appends_to_existing_claude_md(fake_home: Path) -> None:
    claude_dir = fake_home / ".claude"
    claude_dir.mkdir(parents=True)
    claude_md = claude_dir / "CLAUDE.md"
    claude_md.write_text("# My preferences\n\nSome existing instructions.\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["install-skill"])
    assert result.exit_code == 0, result.output

    content = claude_md.read_text(encoding="utf-8")
    assert "Some existing instructions." in content
    assert "# okf-bridge" in content


def test_install_skill_project_scope(
    fake_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = CliRunner().invoke(main, ["install-skill", "--project"])
    assert result.exit_code == 0, result.output

    dst = project_dir / ".claude" / "skills" / "okf-bridge" / "SKILL.md"
    assert dst.is_file()

    claude_md = project_dir / ".claude" / "CLAUDE.md"
    assert claude_md.is_file()
    assert ".claude/skills/okf-bridge/SKILL.md" in claude_md.read_text(encoding="utf-8")

    # Project scope must never touch the user's home directory.
    assert not (fake_home / ".claude" / "skills" / "okf-bridge").exists()
