"""okf/writer.py — Bundle model -> bundle directory.

Responsibilities: stable slug generation, frontmatter emission (`type`
first), auto-generated `index.md` per directory (§6), root `index.md`
with `okf_version` frontmatter (§11 — the only place frontmatter is
permitted in an `index.md`). Output is deterministic: sorted iteration
everywhere, no wall-clock timestamps.
"""

from __future__ import annotations

import posixpath
import re
from pathlib import Path
from typing import Any

import yaml

from graphify_okf_bridge.okf.model import Bundle, Concept

_SLUG_INVALID_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lowercase, hyphenate, and strip leading/trailing hyphens. Idempotent."""
    return _SLUG_INVALID_RE.sub("-", text.lower()).strip("-")


class SlugRegistry:
    """Assigns collision-free slugs deterministically (MAPPING.md E10).

    Registering the same `node_id` twice returns the same slug; registering
    a different `node_id` under a colliding preferred slug appends a
    deterministic numeric suffix (`-2`, `-3`, …), guaranteeing a bijective
    node-id <-> slug mapping.
    """

    def __init__(self) -> None:
        self._owner_by_slug: dict[str, str | None] = {}
        self._slug_by_node: dict[str, str] = {}

    def register(self, preferred: str, node_id: str | None = None) -> str:
        if node_id is not None and node_id in self._slug_by_node:
            return self._slug_by_node[node_id]

        base = slugify(preferred) or "concept"
        candidate = base
        counter = 2
        while candidate in self._owner_by_slug and not (
            node_id is not None and self._owner_by_slug[candidate] == node_id
        ):
            candidate = f"{base}-{counter}"
            counter += 1

        self._owner_by_slug[candidate] = node_id
        if node_id is not None:
            self._slug_by_node[node_id] = candidate
        return candidate

    def slug_for(self, node_id: str) -> str:
        return self._slug_by_node[node_id]


def write_bundle(bundle: Bundle, out_dir: Path) -> None:
    """Serialize `bundle` to `out_dir`, deterministically."""
    out_dir.mkdir(parents=True, exist_ok=True)

    all_dirs: set[str] = {""}
    for concept_id in bundle.concepts:
        all_dirs.update(_ancestor_dirs(concept_id))

    for concept_id in sorted(bundle.concepts):
        concept = bundle.concepts[concept_id]
        path = out_dir / f"{concept_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render_concept(concept), encoding="utf-8")

    for dir_path in sorted(all_dirs):
        index_path = out_dir / dir_path / "index.md"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        if dir_path == "":
            content = _render_root_index(bundle, all_dirs)
        else:
            content = _render_index_body(dir_path, bundle, all_dirs)
        index_path.write_text(content, encoding="utf-8")


def _ancestor_dirs(concept_id: str) -> list[str]:
    parts = concept_id.split("/")[:-1]
    dirs = [""]
    acc: list[str] = []
    for part in parts:
        acc.append(part)
        dirs.append("/".join(acc))
    return dirs


def _direct_subdirs(dir_path: str, all_dirs: set[str]) -> list[str]:
    return sorted(e for e in all_dirs if e != dir_path and posixpath.dirname(e) == dir_path)


def _render_concept(concept: Concept) -> str:
    fm: dict[str, Any] = {"type": concept.type}
    if concept.title is not None:
        fm["title"] = concept.title
    if concept.description is not None:
        fm["description"] = concept.description
    if concept.resource is not None:
        fm["resource"] = concept.resource
    if concept.tags:
        fm["tags"] = list(concept.tags)
    if concept.timestamp is not None:
        fm["timestamp"] = concept.timestamp
    for key in sorted(concept.extra_frontmatter):
        fm[key] = concept.extra_frontmatter[key]
    if concept.typed_links:
        fm["links"] = [
            {"target": f"/{tl.target}.md", "rel": tl.rel, "confidence": tl.confidence}
            for tl in concept.typed_links
        ]

    fm_yaml = yaml.safe_dump(fm, sort_keys=False, default_flow_style=False, allow_unicode=True)
    body = concept.body if concept.body.endswith("\n") else concept.body + "\n"
    return f"---\n{fm_yaml}---\n\n{body}"


def _render_root_index(bundle: Bundle, all_dirs: set[str]) -> str:
    version = bundle.okf_version or "0.1"
    fm_yaml = yaml.safe_dump({"okf_version": version}, sort_keys=False, default_flow_style=False)
    body = _render_index_body("", bundle, all_dirs)
    return f"---\n{fm_yaml}---\n\n{body}"


def _render_index_body(dir_path: str, bundle: Bundle, all_dirs: set[str]) -> str:
    concepts_here = sorted(
        (c for c in bundle.concepts.values() if posixpath.dirname(c.concept_id) == dir_path),
        key=lambda c: c.concept_id,
    )
    subdirs = _direct_subdirs(dir_path, all_dirs)

    lines: list[str] = []
    if concepts_here:
        lines.append("# Concepts")
        lines.append("")
        for concept in concepts_here:
            name = posixpath.basename(concept.concept_id)
            title = concept.title or name
            suffix = f" - {concept.description}" if concept.description else ""
            lines.append(f"* [{title}]({name}.md){suffix}")
        lines.append("")
    if subdirs:
        lines.append("# Subdirectories")
        lines.append("")
        for subdir in subdirs:
            name = posixpath.basename(subdir)
            lines.append(f"* [{name}]({name}/index.md)")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"
