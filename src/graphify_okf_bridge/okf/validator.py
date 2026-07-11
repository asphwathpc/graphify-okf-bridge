"""okf/validator.py — OKF §9 conformance checker.

Hard checks (unparseable frontmatter, missing/empty `type`) already
surface as `Diagnostic(level="error")` diagnostics from the reader; this
module adds the soft/structural checks (missing description, broken
links, missing index.md) as warnings, and exposes `--strict` promotion
via `ValidationReport.ok(strict=...)`.
"""

from __future__ import annotations

import posixpath
from collections.abc import Sequence
from dataclasses import dataclass, field

from graphify_okf_bridge.okf.model import Bundle, Diagnostic


@dataclass
class ValidationReport:
    errors: list[Diagnostic] = field(default_factory=list)
    warnings: list[Diagnostic] = field(default_factory=list)

    def ok(self, *, strict: bool = False) -> bool:
        if self.errors:
            return False
        return not (strict and self.warnings)


def validate(bundle: Bundle, diagnostics: Sequence[Diagnostic] = ()) -> ValidationReport:
    errors = [d for d in diagnostics if d.level == "error"]
    warnings = [d for d in diagnostics if d.level == "warning"]

    concept_ids = set(bundle.concepts)
    for concept in bundle.concepts.values():
        concept_path = f"{concept.concept_id}.md"
        if not concept.description:
            warnings.append(
                Diagnostic(
                    path=concept_path,
                    level="warning",
                    message="missing recommended 'description' field",
                )
            )
        for link in concept.links:
            if link.target not in concept_ids:
                warnings.append(
                    Diagnostic(
                        path=concept_path,
                        level="warning",
                        message=f"broken link to '{link.target}'",
                    )
                )
        for typed_link in concept.typed_links:
            if typed_link.target not in concept_ids:
                warnings.append(
                    Diagnostic(
                        path=concept_path,
                        level="warning",
                        message=f"broken link to '{typed_link.target}'",
                    )
                )

    concept_dirs = {posixpath.dirname(cid) for cid in bundle.concepts} | {""}
    for dir_path in sorted(concept_dirs):
        if not (bundle.root / dir_path / "index.md").exists():
            warnings.append(
                Diagnostic(
                    path=f"{dir_path}/index.md" if dir_path else "index.md",
                    level="warning",
                    message="missing index.md for this directory",
                )
            )

    return ValidationReport(errors=errors, warnings=warnings)
