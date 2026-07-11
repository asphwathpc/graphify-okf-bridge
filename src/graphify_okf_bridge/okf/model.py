"""OKF v0.1 core data model: Concept, Link, Bundle.

Dependency-light and Graphify-free (see okf/__init__.py). Reader and writer
both operate on these types; the graph-specific mapping lives in
exporter.py/importer.py (Phase 2/3), not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

DiagnosticLevel = Literal["error", "warning"]


@dataclass(frozen=True)
class Diagnostic:
    """A single conformance finding — never raised, always collected.

    `level="error"` corresponds to an OKF §9 hard-conformance violation
    (unparseable frontmatter, missing/empty `type`); `level="warning"` is
    soft guidance (missing description, broken link, missing index).
    """

    path: str
    level: DiagnosticLevel
    message: str


@dataclass(frozen=True)
class Link:
    """A markdown cross-link extracted from a concept's body (OKF §5)."""

    target: str
    """Normalized concept id the link resolves to (no leading '/', no '.md')."""
    text: str
    """The link's anchor text."""
    bundle_relative: bool
    """True if the href began with '/' (bundle-root-relative, §5.1)."""


@dataclass(frozen=True)
class TypedLink:
    """One entry of the `links:` frontmatter extension (MAPPING.md §Export E7)."""

    target: str
    rel: str
    confidence: str


@dataclass
class Concept:
    """One non-reserved `.md` file in a bundle (OKF §4)."""

    concept_id: str
    """Path of the file within the bundle, '.md' suffix removed (OKF §2)."""
    type: str
    title: str | None = None
    description: str | None = None
    resource: str | None = None
    tags: list[str] = field(default_factory=list)
    timestamp: str | None = None
    extra_frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    links: list[Link] = field(default_factory=list)
    typed_links: list[TypedLink] = field(default_factory=list)


@dataclass
class Bundle:
    """A knowledge bundle: a directory tree of concepts (OKF §3)."""

    root: Path
    concepts: dict[str, Concept] = field(default_factory=dict)
    okf_version: str | None = None
