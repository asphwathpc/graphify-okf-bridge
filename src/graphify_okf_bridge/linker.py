"""linker.py -- cross-silo edge inference between a Graphify code graph and an
OKF data bundle (MAPPING.md §4, L1-L12).

Pure-ish function: `link(graph, bundle, repo_root) -> LinkResult`. It does read
source files from disk (L6/L7 -- `.sql` files never become graph.json nodes,
so there is no way around it), but takes every input explicitly and performs
no other I/O. Precision over recall throughout: ambiguous or unresolved
matches never produce an edge, only a diagnostic.
"""

from __future__ import annotations

import posixpath
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from graphify_okf_bridge.graphify_io.schema import Edge, Graph, Node
from graphify_okf_bridge.okf.model import Bundle, Diagnostic

_TABLES_PREFIX = "tables/"
_INFERRED_CONFIDENCE = "INFERRED"
_READS_FROM = "reads_from"
_WRITES_TO = "writes_to"

_SIGNAL_DBT_REF = "dbt_ref"
_SIGNAL_SQL_LITERAL = "sql_literal"
_SIGNAL_NAME_MATCH = "name_match"

# MAPPING.md L12: dbt refs are explicit and most trustworthy, SQL literals are
# regex-matched free text, exact-name is the weakest heuristic fallback.
_CONFIDENCE_SCORE_BY_SIGNAL = {
    _SIGNAL_DBT_REF: 0.95,
    _SIGNAL_SQL_LITERAL: 0.75,
    _SIGNAL_NAME_MATCH: 0.55,
}

_DBT_REF_RE = re.compile(r"\{\{\s*ref\(\s*['\"]([A-Za-z0-9_]+)['\"]\s*\)\s*\}\}")
_DBT_SOURCE_RE = re.compile(
    r"\{\{\s*source\(\s*['\"]([A-Za-z0-9_]+)['\"]\s*,\s*['\"]([A-Za-z0-9_]+)['\"]\s*\)\s*\}\}"
)
_SQL_TABLE_RE = re.compile(
    r"\b(FROM|JOIN|INSERT\s+INTO)\s+([A-Za-z_][A-Za-z0-9_.]*)", re.IGNORECASE
)
_WORD_RE = re.compile(r"[a-z0-9_]+")
_LINE_NUMBER_RE = re.compile(r"L(\d+)")

# MAPPING.md L10: candidates are definitions/usages (code) and semantically-extracted
# named entities (concept) -- free-text prose (rationale/document/paper/image) is too
# noisy for identifier matching (a docstring about "the customers table" is not itself
# a code identifier named "customers").
_EXACT_NAME_CANDIDATE_TYPES = {"code", "concept"}


@dataclass
class LinkResult:
    """Output of `link()`: new edges, any synthetic nodes they reference, diagnostics."""

    edges: list[Edge] = field(default_factory=list)
    synthetic_nodes: list[Node] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def link(graph: Graph, bundle: Bundle, repo_root: Path) -> LinkResult:
    """Infer `reads_from`/`writes_to` edges from `graph`'s code to `bundle`'s tables."""
    diagnostics: list[Diagnostic] = []
    table_concepts = _table_concepts(bundle)

    ast_nodes_by_file = _ast_nodes_by_file(graph)
    module_node_by_file = {
        file: _module_node(nodes) for file, nodes in ast_nodes_by_file.items()
    }

    result = LinkResult(diagnostics=diagnostics)
    seen_synthetic_ids: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()

    def emit(source_id: str, source_file: str, table_name: str, relation: str, signal: str) -> None:
        concept_ids = table_concepts.get(table_name.lower(), [])
        if not concept_ids:
            return
        if len(concept_ids) > 1:
            diagnostics.append(
                Diagnostic(
                    path=source_file,
                    level="warning",
                    message=(
                        f"ambiguous table match for '{table_name}': "
                        f"{', '.join(sorted(concept_ids))}"
                    ),
                )
            )
            return
        target_id = f"okf:{concept_ids[0]}"
        key = (source_id, target_id, relation)
        if key in seen_edges:
            return
        seen_edges.add(key)
        fields: dict[str, Any] = {
            "source": source_id,
            "target": target_id,
            "relation": relation,
            "confidence": _INFERRED_CONFIDENCE,
            "confidence_score": _CONFIDENCE_SCORE_BY_SIGNAL[signal],
            "source_file": source_file,
            "linker_signal": signal,
        }
        result.edges.append(Edge(**fields))

    for file in sorted(ast_nodes_by_file):
        source_id = module_node_by_file[file]
        text = Path(file).read_text(encoding="utf-8")
        for relation, table_name, signal in _scan_file_signals(text, is_sql=False):
            emit(source_id, file, table_name, relation, signal)

    for sql_file in sorted(repo_root.rglob("*.sql")):
        rel = sql_file.relative_to(repo_root).as_posix()
        source_id = f"sql:{rel}"
        source_file = sql_file.as_posix()
        if source_id not in seen_synthetic_ids:
            seen_synthetic_ids.add(source_id)
            result.synthetic_nodes.append(
                Node(id=source_id, label=sql_file.name, file_type="code", source_file=source_file)
            )
        text = sql_file.read_text(encoding="utf-8")
        for relation, table_name, signal in _scan_file_signals(text, is_sql=True):
            emit(source_id, source_file, table_name, relation, signal)

    for node, source_file, table_name in _exact_name_matches(graph, table_concepts, diagnostics):
        emit(node.id, source_file, table_name, _READS_FROM, _SIGNAL_NAME_MATCH)

    result.synthetic_nodes.sort(key=lambda n: n.id)
    result.edges.sort(key=lambda e: (e.source, e.target, e.relation))
    return result


def _table_concepts(bundle: Bundle) -> dict[str, list[str]]:
    """MAPPING.md L5: table concepts live under `tables/`; match by basename."""
    result: dict[str, list[str]] = defaultdict(list)
    for concept_id in bundle.concepts:
        if concept_id.startswith(_TABLES_PREFIX):
            name = posixpath.basename(concept_id).lower()
            result[name].append(concept_id)
    return result


def _ast_nodes_by_file(graph: Graph) -> dict[str, list[Node]]:
    """MAPPING.md L7: only `_origin: ast` code nodes have filesystem-resolvable paths."""
    by_file: dict[str, list[Node]] = defaultdict(list)
    for node in graph.nodes:
        if node.file_type == "code" and node.origin == "ast":
            by_file[node.source_file].append(node)
    return by_file


def _line_number(location: str | None) -> int:
    if location is None:
        return 10**9
    match = _LINE_NUMBER_RE.match(location)
    return int(match.group(1)) if match else 10**9


def _module_node(nodes: list[Node]) -> str:
    return min(nodes, key=lambda n: (_line_number(n.source_location), n.id)).id


def _scan_file_signals(text: str, *, is_sql: bool) -> list[tuple[str, str, str]]:
    """MAPPING.md L8/L9: strip whole-line comments, then run the dbt + SQL-literal regexes.

    Returns deduplicated (relation, table_name, linker_signal) triples.
    """
    comment_prefix = "--" if is_sql else "#"
    lines = [line for line in text.splitlines() if not line.lstrip().startswith(comment_prefix)]

    matches: set[tuple[str, str, str]] = set()

    if is_sql:
        clean_text = "\n".join(lines)
        for dbt_match in _DBT_REF_RE.finditer(clean_text):
            matches.add((_READS_FROM, dbt_match.group(1).lower(), _SIGNAL_DBT_REF))
        for dbt_match in _DBT_SOURCE_RE.finditer(clean_text):
            matches.add((_READS_FROM, dbt_match.group(2).lower(), _SIGNAL_DBT_REF))

    for line in lines:
        for sql_match in _SQL_TABLE_RE.finditer(line.replace("`", "")):
            keyword, identifier = sql_match.group(1), sql_match.group(2)
            relation = _WRITES_TO if keyword.lower().startswith("insert") else _READS_FROM
            table_name = identifier.split(".")[-1].lower()
            matches.add((relation, table_name, _SIGNAL_SQL_LITERAL))

    return sorted(matches)


def _singular(word: str) -> str:
    return word[:-1] if len(word) > 1 and word.endswith("s") else word


def _exact_name_matches(
    graph: Graph, table_concepts: dict[str, list[str]], diagnostics: list[Diagnostic]
) -> list[tuple[Node, str, str]]:
    """MAPPING.md L10: exact-name fallback, deduped by label, ambiguous across labels."""
    results: list[tuple[Node, str, str]] = []

    for table_name, concept_ids in sorted(table_concepts.items()):
        if len(concept_ids) != 1:
            continue  # already flagged as ambiguous by the caller's higher-priority signals
        stem = _singular(table_name)

        candidates_by_label: dict[str, list[Node]] = defaultdict(list)
        for node in graph.nodes:
            if node.file_type not in _EXACT_NAME_CANDIDATE_TYPES:
                continue
            tokens = _WORD_RE.findall(node.label.lower())
            stems = {_singular(t) for t in tokens}
            if stem in stems:
                candidates_by_label[node.label].append(node)

        if not candidates_by_label:
            continue

        if len(candidates_by_label) > 1:
            diagnostics.append(
                Diagnostic(
                    path=concept_ids[0],
                    level="warning",
                    message=(
                        f"ambiguous exact-name match for table '{table_name}': "
                        f"{', '.join(sorted(candidates_by_label))}"
                    ),
                )
            )
            continue

        (nodes,) = candidates_by_label.values()
        chosen = min(nodes, key=lambda n: (n.id == (n.norm_label or ""), n.id))
        results.append((chosen, chosen.source_file, table_name))

    return results
