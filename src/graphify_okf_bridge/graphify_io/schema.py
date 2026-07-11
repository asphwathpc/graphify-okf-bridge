"""Pydantic models for graphify's `graph.json`.

Derived from a real graphify run (`graphify extract` + `build_from_json` +
`to_json`) over ``tests/fixtures/tiny_repo``, captured verbatim as
``tests/fixtures/tiny_graph.json``. Model only what was observed there —
see spec/MAPPING.md §1 for the annotated write-up, including surprises.

graph.json is networkx's `node_link_data` format (``directed=False,
multigraph=False`` for a graphify default build), not a bespoke schema:
top-level keys are ``directed``, ``multigraph``, ``graph`` (the
`networkx` graph-attribute dict, which graphify uses to carry
``hyperedges``), ``nodes``, ``links`` (this is the edge list — there is
no top-level ``edges`` key), and graphify additionally duplicates
``hyperedges`` at the top level as a sibling of ``nodes``/``links``.

Every model uses ``extra="allow"``: reading must never raise on an
unknown key (ground rule 3 / IMPLEMENTATION_PLAN Phase 0 step 4).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# file_type is documented (graphify extraction-spec.md) as exactly one of
# these six values, but we don't enforce it here — permissive in (ground rule 5).
FileType = str


class Node(BaseModel):
    """One node in graph.json's `nodes` array.

    `id` is graphify's slug-like identifier (`{parent_dir}_{filename_stem}_{entity}`,
    collapsed to plain filename stems for some code symbols observed in
    tiny_graph.json, e.g. "order", "customer" — the AST extractor does not
    always follow the documented `{stem}_{entity}` format literally).
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    label: str
    file_type: FileType
    source_file: str
    source_location: str | None = None
    community: int | None = None
    norm_label: str | None = None
    origin: str | None = Field(default=None, alias="_origin")
    # Present only on semantically-extracted (doc/paper/image) nodes; absent
    # entirely (not null) on AST-extracted code/rationale nodes.
    source_url: str | None = None
    captured_at: str | None = None
    author: str | None = None
    contributor: str | None = None


class Edge(BaseModel):
    """One edge in graph.json's `links` array (networkx node_link_data naming)."""

    model_config = ConfigDict(extra="allow")

    source: str
    target: str
    relation: str
    confidence: str  # "EXTRACTED" | "INFERRED" | "AMBIGUOUS"
    confidence_score: float
    source_file: str
    source_location: str | None = None
    weight: float = 1.0
    context: str | None = None


class Hyperedge(BaseModel):
    """An n-ary grouping edge; graphify caps these at 3 per extraction chunk."""

    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    nodes: list[str]
    relation: str
    confidence: str
    confidence_score: float | None = None
    source_file: str


class GraphAttrs(BaseModel):
    """networkx's `graph` attribute dict — graphify stores hyperedges here."""

    model_config = ConfigDict(extra="allow")

    hyperedges: list[Hyperedge] = Field(default_factory=list)


class Graph(BaseModel):
    """Top-level graph.json document."""

    model_config = ConfigDict(extra="allow")

    directed: bool
    multigraph: bool
    graph: GraphAttrs = Field(default_factory=GraphAttrs)
    nodes: list[Node]
    links: list[Edge]
    # Duplicated from `graph.hyperedges` at the top level by graphify's writer.
    hyperedges: list[Hyperedge] = Field(default_factory=list)
    built_at_commit: str | None = None
