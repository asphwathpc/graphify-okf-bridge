"""okf/reader.py — bundle directory -> Bundle model.

Permissive per OKF §9: this module never raises on a malformed or
non-conformant file. Every hard violation (unparseable frontmatter,
missing/empty `type`) becomes a `Diagnostic(level="error")`; callers
(okf-bridge validate) decide what to do with it. Soft/structural checks
(missing description, broken links, missing index) live in validator.py,
which consumes both the concepts and these diagnostics.
"""

from __future__ import annotations

import datetime as dt
import posixpath
import re
from pathlib import Path
from typing import Any

import frontmatter

from graphify_okf_bridge.okf.model import Bundle, Concept, Diagnostic, Link, TypedLink

RESERVED_FILENAMES = {"index.md", "log.md"}

_KNOWN_FRONTMATTER_KEYS = {
    "type",
    "title",
    "description",
    "resource",
    "tags",
    "timestamp",
    "links",
}

_LINK_RE = re.compile(r'(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
_EXTERNAL_SCHEMES = ("http://", "https://", "mailto:")


def read_bundle(root: Path) -> tuple[Bundle, list[Diagnostic]]:
    """Read every non-reserved `.md` file under `root` into a Bundle.

    Iteration is sorted for determinism. Never raises.
    """
    diagnostics: list[Diagnostic] = []
    concepts: dict[str, Concept] = {}
    okf_version: str | None = None

    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        rel_posix = rel.as_posix()
        text = path.read_text(encoding="utf-8")

        if path.name in RESERVED_FILENAMES:
            if rel_posix == "index.md":
                metadata, _body, _had_delim = _split_frontmatter(text)
                if metadata:
                    version = metadata.get("okf_version")
                    if isinstance(version, str):
                        okf_version = version
            continue

        concept_id = rel_posix.removesuffix(".md")
        metadata, body, had_delimiter = _split_frontmatter(text)

        if metadata is None:
            message = (
                "unparseable YAML frontmatter"
                if had_delimiter
                else "no parseable frontmatter block found"
            )
            diagnostics.append(Diagnostic(path=rel_posix, level="error", message=message))
            metadata = {}
            type_ = ""
        else:
            type_ = str(metadata.get("type") or "").strip()
            if not type_:
                diagnostics.append(
                    Diagnostic(
                        path=rel_posix,
                        level="error",
                        message="missing required 'type' field (OKF §9)",
                    )
                )

        concept_dir = posixpath.dirname(rel_posix)
        concepts[concept_id] = Concept(
            concept_id=concept_id,
            type=type_,
            title=metadata.get("title"),
            description=metadata.get("description"),
            resource=metadata.get("resource"),
            tags=list(metadata.get("tags") or []),
            timestamp=_normalize_timestamp(metadata.get("timestamp")),
            extra_frontmatter={
                k: v for k, v in metadata.items() if k not in _KNOWN_FRONTMATTER_KEYS
            },
            body=body,
            links=_extract_links(body, concept_dir),
            typed_links=_extract_typed_links(metadata.get("links")),
        )

    return Bundle(root=root, concepts=concepts, okf_version=okf_version), diagnostics


def _split_frontmatter(text: str) -> tuple[dict[str, Any] | None, str, bool]:
    """Returns (metadata, body, had_delimiter).

    `metadata` is None when frontmatter is absent or unparseable; callers
    use `had_delimiter` to distinguish "no frontmatter block at all" from
    "frontmatter block present but broken YAML".
    """
    if not text.lstrip("\ufeff").lstrip().startswith("---"):
        return None, text, False
    try:
        post = frontmatter.loads(text)
    except Exception:
        return None, text, True
    return post.metadata, post.content, True


def _normalize_timestamp(raw: Any) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dt.datetime | dt.date):
        return raw.isoformat()
    return str(raw)


def _resolve_href(href: str, concept_dir: str) -> tuple[str, bool] | None:
    href_no_frag = href.split("#", 1)[0]
    if not href_no_frag or href_no_frag.startswith(_EXTERNAL_SCHEMES):
        return None
    if not href_no_frag.endswith(".md"):
        return None
    bundle_relative = href_no_frag.startswith("/")
    if bundle_relative:
        norm = posixpath.normpath(href_no_frag.lstrip("/"))
    else:
        norm = posixpath.normpath(posixpath.join(concept_dir, href_no_frag))
    return norm.removesuffix(".md"), bundle_relative


def _extract_links(body: str, concept_dir: str) -> list[Link]:
    links = []
    for match in _LINK_RE.finditer(body):
        text, href = match.group(1), match.group(2)
        resolved = _resolve_href(href, concept_dir)
        if resolved is None:
            continue
        target, bundle_relative = resolved
        links.append(Link(target=target, text=text, bundle_relative=bundle_relative))
    return links


def _extract_typed_links(raw: Any) -> list[TypedLink]:
    if not isinstance(raw, list):
        return []
    typed_links = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        target, rel, confidence = entry.get("target"), entry.get("rel"), entry.get("confidence")
        if not (isinstance(target, str) and isinstance(rel, str) and isinstance(confidence, str)):
            continue
        normalized = target.split("#", 1)[0].lstrip("/")
        normalized = normalized.removesuffix(".md")
        typed_links.append(TypedLink(target=normalized, rel=rel, confidence=confidence))
    return typed_links
