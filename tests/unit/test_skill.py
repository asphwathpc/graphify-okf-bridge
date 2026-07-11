"""Phase 5a DoD: skill/SKILL.md passes Claude Code skill validation (parseable
frontmatter with non-empty name + description; body documents all four CLI
commands) — see IMPLEMENTATION_PLAN.md Phase 5 / Test strategy P5 row."""

from __future__ import annotations

from pathlib import Path

import yaml

SKILL_MD = (
    Path(__file__).parent.parent.parent / "src" / "graphify_okf_bridge" / "skill" / "SKILL.md"
)


def _frontmatter_and_body() -> tuple[dict, str]:
    text = SKILL_MD.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "SKILL.md must open with a YAML frontmatter block"
    _, fm_text, body = text.split("---\n", 2)
    return yaml.safe_load(fm_text), body


def test_skill_md_exists() -> None:
    assert SKILL_MD.is_file()


def test_skill_md_has_valid_frontmatter() -> None:
    frontmatter, _ = _frontmatter_and_body()
    assert frontmatter["name"] == "okf-bridge"
    assert isinstance(frontmatter["description"], str)
    assert frontmatter["description"].strip() != ""


def test_skill_md_documents_all_four_commands() -> None:
    _, body = _frontmatter_and_body()
    commands = ("okf-bridge validate", "okf-bridge export", "okf-bridge import", "okf-bridge link")
    for command in commands:
        assert command in body, f"SKILL.md body is missing an example for `{command}`"
