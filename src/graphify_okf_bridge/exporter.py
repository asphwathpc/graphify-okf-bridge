"""exporter.py -- graph.json -> OKF bundle (MAPPING.md §Export, E1-E11).

Pure function: `export(graph) -> Bundle`. No I/O; the CLI wrapper in cli.py
loads the graph and calls `okf.writer.write_bundle` on the result.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from graphify_okf_bridge.graphify_io.schema import Edge, Graph, Node
from graphify_okf_bridge.okf.model import Bundle, Concept, Link, TypedLink
from graphify_okf_bridge.okf.writer import SlugRegistry

_OVERVIEW_CONCEPT_ID = "overview"
_TOP_NODES_LIMIT = 10


def export(graph: Graph) -> Bundle:
    """Map a graphify `Graph` to an in-memory OKF `Bundle` (pure, deterministic)."""
    concept_id_by_node_id = _assign_concept_ids(graph.nodes)
    node_by_id = {node.id: node for node in graph.nodes}

    edges_by_source: dict[str, list[Edge]] = defaultdict(list)
    for edge in graph.links:
        edges_by_source[edge.source].append(edge)
    for edges in edges_by_source.values():
        edges.sort(key=lambda e: (e.relation, e.target))

    concepts: dict[str, Concept] = {}
    for node in graph.nodes:
        concept_id = concept_id_by_node_id[node.id]
        concepts[concept_id] = _build_concept(
            node, concept_id, edges_by_source.get(node.id, []), node_by_id, concept_id_by_node_id
        )

    concepts[_OVERVIEW_CONCEPT_ID] = _build_overview(graph, node_by_id, concept_id_by_node_id)

    return Bundle(root=Path("."), concepts=concepts, okf_version="0.1")


def _assign_concept_ids(nodes: list[Node]) -> dict[str, str]:
    registries: dict[str, SlugRegistry] = defaultdict(SlugRegistry)
    concept_id_by_node_id: dict[str, str] = {}
    for node in sorted(nodes, key=lambda n: n.id):
        registry = registries[node.file_type]
        slug = registry.register(node.label, node.id)
        concept_id_by_node_id[node.id] = f"{node.file_type}/{slug}"
    return concept_id_by_node_id


def _build_concept(
    node: Node,
    concept_id: str,
    edges: list[Edge],
    node_by_id: dict[str, Node],
    concept_id_by_node_id: dict[str, str],
) -> Concept:
    typed_links: list[TypedLink] = []
    links: list[Link] = []
    connection_lines: list[str] = []
    for edge in edges:
        target_concept_id = concept_id_by_node_id[edge.target]
        confidence = edge.confidence.lower()
        typed_links.append(
            TypedLink(target=target_concept_id, rel=edge.relation, confidence=confidence)
        )
        links.append(Link(target=target_concept_id, text=edge.relation, bundle_relative=True))
        target_title = node_by_id[edge.target].label
        connection_lines.append(
            f"- {edge.relation} [{target_title}](/{target_concept_id}.md) *({confidence})*"
        )

    body_parts: list[str] = []
    if node.file_type == "rationale":
        body_parts.append(node.label.strip())
    if connection_lines:
        if body_parts:
            body_parts.append("")
        body_parts.append("## Connections")
        body_parts.append("")
        body_parts.extend(connection_lines)
    body = "\n".join(body_parts)
    if body and not body.endswith("\n"):
        body += "\n"

    tags = [f"community:{node.community}"] if node.community is not None else []

    return Concept(
        concept_id=concept_id,
        type=node.file_type.title(),
        title=node.label,
        description=_description(node),
        resource=_resource(node),
        tags=tags,
        extra_frontmatter={"graphify_node_id": node.id},
        body=body,
        links=links,
        typed_links=typed_links,
    )


def _resource(node: Node) -> str:
    if node.source_location:
        return f"file://{node.source_file}#{node.source_location}"
    return f"file://{node.source_file}"


def _description(node: Node) -> str:
    if node.file_type == "rationale":
        return node.label.strip()
    return f"{node.file_type.title()} node `{node.label}` ({node.source_file})."


def _build_overview(
    graph: Graph, node_by_id: dict[str, Node], concept_id_by_node_id: dict[str, str]
) -> Concept:
    degree: dict[str, int] = defaultdict(int)
    for edge in graph.links:
        degree[edge.source] += 1
        degree[edge.target] += 1

    communities = sorted({n.community for n in graph.nodes if n.community is not None})

    top_nodes = sorted(degree, key=lambda node_id: (-degree[node_id], node_id))[:_TOP_NODES_LIMIT]

    lines = [
        "# Summary",
        "",
        f"* Nodes: {len(graph.nodes)}",
        f"* Edges: {len(graph.links)}",
        f"* Communities: {len(communities)}",
        "",
    ]
    if top_nodes:
        lines.append("# Top nodes by degree")
        lines.append("")
        for node_id in top_nodes:
            node = node_by_id[node_id]
            target_concept_id = concept_id_by_node_id[node_id]
            lines.append(f"* [{node.label}](/{target_concept_id}.md) - {degree[node_id]} edge(s)")
        lines.append("")

    body = "\n".join(lines).rstrip("\n") + "\n"

    return Concept(
        concept_id=_OVERVIEW_CONCEPT_ID,
        type="Overview",
        title="Graph Overview",
        description=f"Summary statistics and top nodes by degree ({len(graph.nodes)} nodes, "
        f"{len(graph.links)} edges).",
        body=body,
    )
