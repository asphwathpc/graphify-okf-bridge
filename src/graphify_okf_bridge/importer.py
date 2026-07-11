"""importer.py -- OKF bundle -> graph.json (MAPPING.md §Import, I1-I7).

Pure function: `import_bundle(bundle) -> (Graph, diagnostics)`. No I/O; the
CLI wrapper in cli.py calls okf.reader.read_bundle then
graphify_io.loader.save_graph on the result.
"""

from __future__ import annotations

import posixpath
from typing import Any

from graphify_okf_bridge.graphify_io.schema import Edge, Graph, Node
from graphify_okf_bridge.okf.model import Bundle, Concept, Diagnostic, Link, TypedLink

_OVERVIEW_CONCEPT_ID = "overview"
_OVERVIEW_TYPE = "Overview"
_COMMUNITY_TAG_PREFIX = "community:"
_EXTRACTED_SCORE = 1.0
_DEFAULT_INFERRED_SCORE = 0.75
_REFERENCES_RELATION = "references"
_EXTRACTED_CONFIDENCE = "EXTRACTED"


def import_bundle(bundle: Bundle) -> tuple[Graph, list[Diagnostic]]:
    """Map an OKF `Bundle` to a graphify-compatible `Graph` (pure, deterministic)."""
    diagnostics: list[Diagnostic] = []

    importable = {
        concept_id: concept
        for concept_id, concept in bundle.concepts.items()
        if not _is_synthetic_overview(concept)
    }
    node_id_by_concept_id = {
        concept_id: _node_id(concept) for concept_id, concept in importable.items()
    }

    nodes = [
        _build_node(importable[concept_id], node_id_by_concept_id[concept_id])
        for concept_id in sorted(importable)
    ]

    edges: list[Edge] = []
    for concept_id in sorted(importable):
        edges.extend(
            _edges_for_concept(
                importable[concept_id], node_id_by_concept_id, diagnostics
            )
        )

    graph = Graph(directed=False, multigraph=False, nodes=nodes, links=edges)
    return graph, diagnostics


def _is_synthetic_overview(concept: Concept) -> bool:
    return (
        concept.concept_id == _OVERVIEW_CONCEPT_ID
        and concept.type == _OVERVIEW_TYPE
        and "graphify_node_id" not in concept.extra_frontmatter
    )


def _node_id(concept: Concept) -> str:
    graphify_id = concept.extra_frontmatter.get("graphify_node_id")
    if isinstance(graphify_id, str) and graphify_id:
        return graphify_id
    return f"okf:{concept.concept_id}"


def _split_resource(resource: str | None, concept_id: str) -> tuple[str, str | None]:
    if resource is None:
        return f"okf:{concept_id}", None
    if resource.startswith("file://"):
        rest = resource.removeprefix("file://")
        path, sep, fragment = rest.partition("#")
        return path, fragment if sep else None
    return resource, None


def _split_tags(tags: list[str]) -> tuple[int | None, list[str]]:
    community: int | None = None
    other: list[str] = []
    for tag in tags:
        suffix = tag.removeprefix(_COMMUNITY_TAG_PREFIX)
        if community is None and suffix != tag and suffix.isdigit():
            community = int(suffix)
            continue
        other.append(tag)
    return community, other


def _build_node(concept: Concept, node_id: str) -> Node:
    source_file, source_location = _split_resource(concept.resource, concept.concept_id)
    community, other_tags = _split_tags(concept.tags)

    fields: dict[str, Any] = {
        "id": node_id,
        "label": concept.title or posixpath.basename(concept.concept_id),
        "file_type": concept.type.lower(),
        "source_file": source_file,
        "source_location": source_location,
        "community": community,
        "okf_type": concept.type,
    }
    if concept.description:
        fields["okf_description"] = concept.description
    if other_tags:
        fields["okf_tags"] = other_tags
    if concept.body.strip():
        fields["okf_body"] = concept.body

    return Node(**fields)


def _edge_source_file(concept: Concept) -> str:
    source_file, _ = _split_resource(concept.resource, concept.concept_id)
    return source_file


def _edges_for_concept(
    concept: Concept,
    node_id_by_concept_id: dict[str, str],
    diagnostics: list[Diagnostic],
) -> list[Edge]:
    source_id = node_id_by_concept_id[concept.concept_id]
    edges: list[Edge] = []
    typed_targets: set[str] = set()

    for typed_link in concept.typed_links:
        typed_targets.add(typed_link.target)
        edge = _typed_link_edge(concept, source_id, typed_link, node_id_by_concept_id, diagnostics)
        if edge is not None:
            edges.append(edge)

    for link in concept.links:
        if link.target in typed_targets:
            continue
        edge = _plain_link_edge(concept, source_id, link, node_id_by_concept_id, diagnostics)
        if edge is not None:
            edges.append(edge)

    return edges


def _typed_link_edge(
    concept: Concept,
    source_id: str,
    typed_link: TypedLink,
    node_id_by_concept_id: dict[str, str],
    diagnostics: list[Diagnostic],
) -> Edge | None:
    target_id = node_id_by_concept_id.get(typed_link.target)
    if target_id is None:
        diagnostics.append(
            Diagnostic(
                path=f"{concept.concept_id}.md",
                level="warning",
                message=f"broken link to '{typed_link.target}'",
            )
        )
        return None

    confidence = typed_link.confidence.upper()
    return Edge(
        source=source_id,
        target=target_id,
        relation=typed_link.rel,
        confidence=confidence,
        confidence_score=_EXTRACTED_SCORE if confidence == _EXTRACTED_CONFIDENCE
        else _DEFAULT_INFERRED_SCORE,
        source_file=_edge_source_file(concept),
    )


def _plain_link_edge(
    concept: Concept,
    source_id: str,
    link: Link,
    node_id_by_concept_id: dict[str, str],
    diagnostics: list[Diagnostic],
) -> Edge | None:
    target_id = node_id_by_concept_id.get(link.target)
    if target_id is None:
        diagnostics.append(
            Diagnostic(
                path=f"{concept.concept_id}.md",
                level="warning",
                message=f"broken link to '{link.target}'",
            )
        )
        return None

    return Edge(
        source=source_id,
        target=target_id,
        relation=_REFERENCES_RELATION,
        confidence=_EXTRACTED_CONFIDENCE,
        confidence_score=_EXTRACTED_SCORE,
        source_file=_edge_source_file(concept),
    )
