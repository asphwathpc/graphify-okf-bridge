"""Phase 4 acceptance tests: linker.py (code graph <-> OKF data bundle).

MAPPING.md §Linking (L1-L12) is normative. The fixture pairing --
tests/fixtures/tiny_graph.json (built from tests/fixtures/tiny_repo) against
tests/fixtures/okf_minimal -- encodes known-answer cases directly in its
source comments/docstrings; test_fixture_produces_exactly_the_expected_edges
is the precision bar: any extra edge is a false positive and fails the suite.
"""

from __future__ import annotations

from pathlib import Path

from graphify_okf_bridge.graphify_io.loader import load_graph
from graphify_okf_bridge.graphify_io.schema import Graph, Node
from graphify_okf_bridge.linker import _scan_file_signals, _singular, link
from graphify_okf_bridge.okf.model import Bundle, Concept
from graphify_okf_bridge.okf.reader import read_bundle

FIXTURES = Path(__file__).parent.parent / "fixtures"
TINY_REPO = FIXTURES / "tiny_repo"


def _tiny_graph():
    return load_graph(FIXTURES / "tiny_graph.json")


def _okf_minimal():
    bundle, diagnostics = read_bundle(FIXTURES / "okf_minimal")
    assert [d for d in diagnostics if d.level == "error"] == []
    return bundle


def _tiny_result():
    return link(_tiny_graph(), _okf_minimal(), TINY_REPO)


# --- Whole-fixture acceptance test (the precision bar) ----------------------


def test_fixture_produces_exactly_the_expected_edges() -> None:
    result = _tiny_result()

    edges = {(e.source, e.target, e.relation, e.model_extra["linker_signal"]) for e in result.edges}
    assert edges == {
        ("app_service", "okf:tables/orders", "reads_from", "sql_literal"),
        ("app_service", "okf:tables/customers", "reads_from", "sql_literal"),
        ("sql:analytics/stg_orders.sql", "okf:tables/orders", "reads_from", "sql_literal"),
        ("sql:analytics/orders_model.sql", "okf:tables/customers", "reads_from", "dbt_ref"),
        ("app_models_customer", "okf:tables/customers", "reads_from", "name_match"),
    }
    assert len(result.edges) == 5


def test_every_edge_carries_inferred_confidence_and_provenance() -> None:
    result = _tiny_result()

    assert result.edges, "fixture must produce edges for this assertion to be meaningful"
    for edge in result.edges:
        assert edge.confidence == "INFERRED"
        assert 0.55 <= edge.confidence_score <= 0.95
        assert edge.model_extra is not None
        assert edge.model_extra["linker_signal"] in {"dbt_ref", "sql_literal", "name_match"}


def test_ambiguous_orders_exact_name_match_produces_warning_and_no_edge() -> None:
    result = _tiny_result()

    assert not any(
        e.target == "okf:tables/orders" and e.model_extra["linker_signal"] == "name_match"
        for e in result.edges
    )

    warnings = [d for d in result.diagnostics if d.level == "warning"]
    assert len(warnings) == 1
    assert "orders" in warnings[0].message
    assert "Order" in warnings[0].message
    assert "orders table" in warnings[0].message


def test_synthetic_nodes_cover_every_sql_source_id(tmp_path: Path) -> None:
    result = _tiny_result()

    edge_sources = {e.source for e in result.edges}
    sql_sources = {s for s in edge_sources if s.startswith("sql:")}
    assert sql_sources == {"sql:analytics/orders_model.sql", "sql:analytics/stg_orders.sql"}

    synthetic_ids = {n.id for n in result.synthetic_nodes}
    assert sql_sources <= synthetic_ids


def test_synthetic_nodes_also_cover_every_okf_target_id() -> None:
    """L13: link() output is self-contained -- every edge target gets a synthetic
    concept node too, not just sql: sources, so a single link() output file
    doesn't depend on graphify merge-graphs unifying ids across separate files."""
    result = _tiny_result()

    edge_targets = {e.target for e in result.edges}
    okf_targets = {t for t in edge_targets if t.startswith("okf:")}
    assert okf_targets == {"okf:tables/orders", "okf:tables/customers"}

    synthetic_ids = {n.id for n in result.synthetic_nodes}
    assert okf_targets <= synthetic_ids

    for node in result.synthetic_nodes:
        if node.id in okf_targets:
            assert node.file_type == "concept"
            assert node.label


def test_link_is_deterministic() -> None:
    result_a = _tiny_result()
    result_b = _tiny_result()

    assert [e.model_dump() for e in result_a.edges] == [e.model_dump() for e in result_b.edges]
    assert [n.model_dump() for n in result_a.synthetic_nodes] == [
        n.model_dump() for n in result_b.synthetic_nodes
    ]


def test_linker_edge_target_matches_importer_id_convention() -> None:
    """MAPPING.md L11: `okf-bridge link` output must compose with `okf-bridge import`."""
    from graphify_okf_bridge.importer import import_bundle

    result = _tiny_result()
    imported_graph, _ = import_bundle(_okf_minimal())
    imported_ids = {n.id for n in imported_graph.nodes}

    targets = {e.target for e in result.edges}
    assert targets <= imported_ids


# --- Trap cases: these must never produce an edge ---------------------------


def test_trap_commented_out_sql_never_matches() -> None:
    """service.py's `# LEGACY_QUERY = "SELECT * FROM events_legacy"` must be ignored."""
    result = _tiny_result()

    assert not any("events_legacy" in e.target for e in result.edges)


def test_trap_partial_string_match_never_links_to_orders() -> None:
    """BANNER = "purchase orders_are_processed_nightly" must not create a spurious edge."""
    result = _tiny_result()

    # The only legitimate 'orders' edges come from app_service (SQL literal) and
    # stg_orders.sql (SQL literal) -- never from a name-match / BANNER-derived source.
    orders_edges = [e for e in result.edges if e.target == "okf:tables/orders"]
    assert {e.source for e in orders_edges} == {"app_service", "sql:analytics/stg_orders.sql"}


def test_trap_ambiguous_session_identifier_never_links() -> None:
    """compute_revenue's local `session = "session"` must never produce an edge."""
    result = _tiny_result()

    assert not any("session" in e.target.lower() for e in result.edges)
    assert not any("session" in e.source.lower() for e in result.edges)


# --- Focused unit tests for the scanning helpers -----------------------------


def test_dbt_ref_and_source_are_extracted() -> None:
    text = "SELECT * FROM {{ ref('stg_orders') }} JOIN {{ source('warehouse', 'customers') }}"
    matches = _scan_file_signals(text, is_sql=True)
    assert ("reads_from", "stg_orders", "dbt_ref") in matches
    assert ("reads_from", "customers", "dbt_ref") in matches


def test_sql_literal_insert_into_is_writes_to() -> None:
    matches = _scan_file_signals("INSERT INTO stg_orders SELECT 1", is_sql=True)
    assert matches == [("writes_to", "stg_orders", "sql_literal")]


def test_sql_literal_from_join_is_reads_from() -> None:
    matches = _scan_file_signals("SELECT * FROM orders JOIN customers USING (id)", is_sql=True)
    assert ("reads_from", "orders", "sql_literal") in matches
    assert ("reads_from", "customers", "sql_literal") in matches


def test_sql_literal_strips_backticks_and_qualified_names() -> None:
    matches = _scan_file_signals("SELECT * FROM `project.dataset.orders`", is_sql=True)
    assert matches == [("reads_from", "orders", "sql_literal")]


def test_sql_literal_dedups_within_a_file() -> None:
    text = "SELECT * FROM orders\nUNION ALL\nSELECT * FROM orders"
    matches = _scan_file_signals(text, is_sql=True)
    assert matches == [("reads_from", "orders", "sql_literal")]


def test_python_comment_lines_are_stripped_before_scanning() -> None:
    text = '# LEGACY_QUERY = "SELECT * FROM events_legacy"\nx = 1'
    matches = _scan_file_signals(text, is_sql=False)
    assert matches == []


def test_sql_comment_lines_are_stripped_before_scanning() -> None:
    text = "-- SELECT * FROM events_legacy\nSELECT 1"
    matches = _scan_file_signals(text, is_sql=True)
    assert matches == []


def test_partial_string_identifier_never_matches_without_sql_keyword() -> None:
    matches = _scan_file_signals('BANNER = "purchase orders_are_processed_nightly"', is_sql=False)
    assert matches == []


def test_dbt_signals_are_not_extracted_from_python_files() -> None:
    text = "QUERY = \"{{ ref('stg_orders') }}\""
    matches = _scan_file_signals(text, is_sql=False)
    assert matches == []


def test_singular_strips_one_trailing_s() -> None:
    assert _singular("orders") == "order"
    assert _singular("customers") == "customer"
    assert _singular("status") == "statu"  # documented simplification, see MAPPING.md L10
    assert _singular("s") == "s"


def test_underscore_keeps_identifier_as_one_token() -> None:
    """load_customer() must not spuriously match table 'customers' via a split token."""
    matches = _scan_file_signals("FROM load_customer_log", is_sql=False)
    assert matches == [("reads_from", "load_customer_log", "sql_literal")]


# --- Table-concept scoping ---------------------------------------------------


def test_unresolved_table_name_produces_no_edge_and_no_warning() -> None:
    """A dbt ref to an uncatalogued intermediate model is normal, not an error (L5)."""
    result = _tiny_result()

    assert not any(e.target == "okf:tables/stg_orders" for e in result.edges)
    assert not any("stg_orders" in d.message for d in result.diagnostics)


def test_synthetic_node_shape() -> None:
    result = _tiny_result()

    node = next(n for n in result.synthetic_nodes if n.id == "sql:analytics/stg_orders.sql")
    assert isinstance(node, Node)
    assert node.file_type == "code"
    assert node.source_file == str(TINY_REPO / "analytics" / "stg_orders.sql")


# --- Synthetic-graph edge cases (branches the real fixture never exercises) --


def _minimal_graph(nodes: list[Node]) -> Graph:
    return Graph(directed=False, multigraph=False, nodes=nodes, links=[])


def _module_node(node_id: str, source_file: str, text: str, tmp_path: Path) -> Node:
    path = tmp_path / source_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return Node(
        id=node_id,
        label=Path(source_file).name,
        file_type="code",
        source_file=str(path),
        source_location="L1",
        origin="ast",
    )


def test_ambiguous_okf_side_table_name_produces_warning_and_no_edge(tmp_path: Path) -> None:
    """Two table concepts sharing a basename (e.g. across dataset dirs) is an L3 ambiguity."""
    node = _module_node("mod", "app.py", "SELECT * FROM widgets\n", tmp_path)
    bundle = Bundle(
        root=tmp_path,
        concepts={
            "tables/widgets": Concept(concept_id="tables/widgets", type="BigQuery Table"),
            "tables/legacy/widgets": Concept(
                concept_id="tables/legacy/widgets", type="BigQuery Table"
            ),
        },
    )
    result = link(_minimal_graph([node]), bundle, tmp_path)

    assert result.edges == []
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].level == "warning"
    assert "widgets" in result.diagnostics[0].message


def test_exact_name_fallback_with_no_candidates_produces_no_edge(tmp_path: Path) -> None:
    node = _module_node("mod", "app.py", "x = 1\n", tmp_path)
    bundle = Bundle(
        root=tmp_path,
        concepts={"tables/widgets": Concept(concept_id="tables/widgets", type="BigQuery Table")},
    )
    result = link(_minimal_graph([node]), bundle, tmp_path)

    assert result.edges == []
    assert result.diagnostics == []


def test_module_node_falls_back_when_source_location_is_missing(tmp_path: Path) -> None:
    path = tmp_path / "app.py"
    path.write_text("SELECT * FROM widgets\n", encoding="utf-8")
    node = Node(
        id="mod",
        label="app.py",
        file_type="code",
        source_file=str(path),
        source_location=None,
        origin="ast",
    )
    bundle = Bundle(
        root=tmp_path,
        concepts={"tables/widgets": Concept(concept_id="tables/widgets", type="BigQuery Table")},
    )
    result = link(_minimal_graph([node]), bundle, tmp_path)

    assert len(result.edges) == 1
    assert result.edges[0].source == "mod"


def test_relative_source_file_is_resolved_against_repo_root_not_cwd(tmp_path: Path) -> None:
    """MAPPING.md L6 (revised 2026-07-11): graphify commonly runs with CWD
    inside the target repo, so `source_file` on `_origin: ast` nodes is
    repo-relative, not CWD-relative -- and the linker is typically invoked
    later, from a different CWD. `repo_root` must be joined onto a relative
    `source_file` rather than assuming it resolves as-is."""
    repo_root = tmp_path / "jaffle-shop"
    (repo_root / "models").mkdir(parents=True)
    (repo_root / "models" / "app.py").write_text("SELECT * FROM widgets\n", encoding="utf-8")
    node = Node(
        id="mod",
        label="app.py",
        file_type="code",
        source_file="models/app.py",
        source_location="L1",
        origin="ast",
    )
    bundle = Bundle(
        root=repo_root,
        concepts={"tables/widgets": Concept(concept_id="tables/widgets", type="BigQuery Table")},
    )
    result = link(_minimal_graph([node]), bundle, repo_root)

    assert len(result.edges) == 1
    assert result.edges[0].source == "mod"
    assert result.edges[0].source_file == "models/app.py"


def test_ast_node_with_empty_source_file_is_skipped_not_crashed(tmp_path: Path) -> None:
    """MAPPING.md §1 surprise 5: real graphify output can carry a `code`/`ast`
    node with `source_file: ""` (an unattributed nested class). `Path("")`
    resolves to the cwd directory, so reading it naively raises
    `IsADirectoryError` instead of skipping a missing file -- the linker must
    exclude such nodes before attempting to read them from disk."""
    good_node = _module_node("widgets", "app.py", "SELECT * FROM widgets\n", tmp_path)
    orphan_node = Node(
        id="authheader",
        label="AuthHeader",
        file_type="code",
        source_file="",
        source_location="",
        origin="ast",
    )
    bundle = Bundle(
        root=tmp_path,
        concepts={"tables/widgets": Concept(concept_id="tables/widgets", type="BigQuery Table")},
    )
    result = link(_minimal_graph([good_node, orphan_node]), bundle, tmp_path)

    assert len(result.edges) == 1
    assert result.edges[0].source == "widgets"


def test_same_table_reached_by_two_signals_from_one_source_dedups(tmp_path: Path) -> None:
    """SQL-literal + exact-name both pointing widgets->widgets from the same source collapses."""
    node = _module_node("widgets", "app.py", "SELECT * FROM widgets\n", tmp_path)
    node = node.model_copy(update={"label": "widgets", "id": "widgets"})
    bundle = Bundle(
        root=tmp_path,
        concepts={"tables/widgets": Concept(concept_id="tables/widgets", type="BigQuery Table")},
    )
    result = link(_minimal_graph([node]), bundle, tmp_path)

    assert len(result.edges) == 1
    assert result.edges[0].model_extra["linker_signal"] == "sql_literal"


def test_sql_file_reuses_existing_same_stem_code_node_instead_of_synthetic(
    tmp_path: Path,
) -> None:
    """MAPPING.md L7a: a semantically-extracted node (no `_origin: ast`) named
    after a dbt model -- e.g. from that model's schema.yml, the real situation
    graphify produced for jaffle-shop's stg_orders -- must absorb the edges
    from its same-named `.sql` file rather than the file getting a second,
    disconnected `sql:<path>` identity."""
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "stg_orders.sql").write_text("SELECT * FROM widgets\n", encoding="utf-8")
    semantic_node = Node(
        id="stg_orders_model",
        label="stg_orders model",
        file_type="code",
        source_file="models/stg_orders.yml",
    )
    bundle = Bundle(
        root=tmp_path,
        concepts={"tables/widgets": Concept(concept_id="tables/widgets", type="BigQuery Table")},
    )
    result = link(_minimal_graph([semantic_node]), bundle, tmp_path)

    assert len(result.edges) == 1
    assert result.edges[0].source == "stg_orders_model"
    assert not any(n.id.startswith("sql:") for n in result.synthetic_nodes)


def test_sql_file_falls_back_to_synthetic_node_when_stem_match_is_ambiguous(
    tmp_path: Path,
) -> None:
    """Two distinct labels both stem-matching the file's stem is unresolvable --
    same L3 precision-over-recall policy as L10 -- so the original synthetic
    `sql:<path>` node is used, unchanged."""
    (tmp_path / "stg_orders.sql").write_text("SELECT * FROM widgets\n", encoding="utf-8")
    node_a = Node(id="a", label="stg_orders model", file_type="code", source_file="a.yml")
    node_b = Node(id="b", label="stg_orders staging", file_type="code", source_file="b.yml")
    bundle = Bundle(
        root=tmp_path,
        concepts={"tables/widgets": Concept(concept_id="tables/widgets", type="BigQuery Table")},
    )
    result = link(_minimal_graph([node_a, node_b]), bundle, tmp_path)

    assert len(result.edges) == 1
    assert result.edges[0].source == "sql:stg_orders.sql"
    assert any(n.id == "sql:stg_orders.sql" for n in result.synthetic_nodes)
