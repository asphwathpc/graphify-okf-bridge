"""Phase 0 acceptance test: tiny_graph.json (real graphify output) loads
through the pydantic models in graphify_io/schema.py with zero validation
errors. See IMPLEMENTATION_PLAN.md Phase 0 step 6.
"""

from __future__ import annotations

from pathlib import Path

from graphify_okf_bridge.graphify_io.loader import load_graph
from graphify_okf_bridge.graphify_io.schema import Edge, Hyperedge, Node

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_tiny_graph_json_parses_with_zero_errors() -> None:
    graph = load_graph(FIXTURES / "tiny_graph.json")
    assert graph.nodes
    assert graph.links


def test_nodes_have_required_fields() -> None:
    graph = load_graph(FIXTURES / "tiny_graph.json")
    for node in graph.nodes:
        assert node.id
        assert node.file_type
        assert node.source_file


def test_ast_nodes_lack_semantic_only_fields() -> None:
    """AST-extracted nodes never carry the semantic-extraction-only fields."""
    graph = load_graph(FIXTURES / "tiny_graph.json")
    ast_nodes = [n for n in graph.nodes if n.origin == "ast"]
    assert ast_nodes
    for node in ast_nodes:
        assert node.source_url is None
        assert node.author is None


def test_sql_files_produced_no_nodes() -> None:
    """Documented surprise (MAPPING.md §1): graphify's AST pass is Python-only
    and semantic extraction skips the `code` category, so .sql files in
    tiny_repo produce zero graph nodes in a stock run."""
    graph = load_graph(FIXTURES / "tiny_graph.json")
    sql_nodes = [n for n in graph.nodes if n.source_file.endswith(".sql")]
    assert sql_nodes == []


def test_edges_reference_declared_confidence_levels() -> None:
    graph = load_graph(FIXTURES / "tiny_graph.json")
    for edge in graph.links:
        assert edge.confidence in {"EXTRACTED", "INFERRED", "AMBIGUOUS"}


def test_hyperedge_source_file_may_be_null() -> None:
    """Real graphify output (captured from a `graphify .` run over jaffle-shop
    for the Phase 5c demo) has hyperedges with `source_file: null` when the
    grouped nodes have no single natural originating file — MAPPING.md §1
    surprise 4."""
    Hyperedge.model_validate(
        {
            "id": "dbt_project_yml_packages_yml_requirements_txt_taskfile_yml",
            "label": "Project Configuration and Dependencies",
            "nodes": [
                "src_dbt_project_yml_jaffle_shop",
                "src_packages_yml_jaffle_shop",
                "src_requirements_txt_jaffle_shop",
                "src_taskfile_yml_jaffle_shop",
            ],
            "relation": "participate_in",
            "confidence": "EXTRACTED",
            "confidence_score": 0.75,
            "source_file": None,
        }
    )


def test_node_and_edge_models_are_permissive_to_unknown_keys() -> None:
    Node.model_validate(
        {
            "id": "x",
            "label": "X",
            "file_type": "code",
            "source_file": "a.py",
            "some_future_key": "unknown",
        }
    )
    Edge.model_validate(
        {
            "source": "a",
            "target": "b",
            "relation": "calls",
            "confidence": "EXTRACTED",
            "confidence_score": 1.0,
            "source_file": "a.py",
            "some_future_key": "unknown",
        }
    )
