# MAPPING.md — Graphify ↔ OKF mapping convention

**Normative for this repository.** If code and this document disagree, this document wins; change it first (with rationale in the PR), then the code.

Referenced specs: [OKF v0.1 SPEC.md](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) · Graphify `graph.json` (observed schema, §1).

---

## 1. graph.json observed schema

Captured from a real graphify run (`graphify extract` AST pass + a semantic-extraction
subagent over `tests/fixtures/tiny_repo`, then `build_from_json` → `cluster` →
`to_json`) — see `tests/fixtures/tiny_graph.json`. Modeled in
`graphify_io/schema.py` (`Graph`, `Node`, `Edge`, `Hyperedge`; all `extra="allow"`).

**Top-level shape is networkx's `node_link_data` format, not a bespoke one:**

| Key | Type | Notes |
|---|---|---|
| `directed` | bool | `false` for a default (undirected) graphify build. |
| `multigraph` | bool | `false`. |
| `graph` | object | networkx's graph-attribute dict. graphify stores `hyperedges` here. |
| `nodes` | array | see Node shape below. |
| `links` | array | **this is the edge list** — there is no top-level `edges` key. |
| `hyperedges` | array | graphify duplicates `graph.hyperedges` here too, at the top level. |
| `built_at_commit` | string \| null | git commit the source tree was at when built. |

**Node:** `id` (slug, `[a-z0-9_]`, e.g. `app_models_basemodel`, but the AST
extractor does not always follow the documented `{parent_dir}_{stem}_{entity}`
convention — plain code symbol names like `order`/`customer` were observed
un-prefixed), `label`, `file_type` (`code`/`document`/`paper`/`image`/`rationale`/`concept`),
`source_file` (repo-relative path), `source_location` (`"L<n>"` string or
`null`), `community` (int), `norm_label`. Doc/paper/image (semantically
extracted) nodes additionally carry `source_url`, `captured_at`, `author`,
`contributor` — **these keys are entirely absent (not null) on AST-extracted
code/rationale nodes**, not just empty. AST nodes instead carry a leading-underscore
`_origin: "ast"` key.

**Edge (`links[]`):** `source`, `target`, `relation` (`contains`, `imports_from`,
`method`, `inherits`, `uses`, `references`, `rationale_for`, `shares_data_with`,
`semantically_similar_to`, …), `confidence` (`EXTRACTED`/`INFERRED`/`AMBIGUOUS`),
`confidence_score` (float — always `1.0` for EXTRACTED; discrete rubric
0.55–0.95 for INFERRED), `source_file`, `source_location`, `weight`, optional
`context` (e.g. `"parameter_type"`, `"return_type"`, `"import"`).

**Hyperedge:** `id`, `label`, `nodes` (list of node ids, 3+), `relation`
(`participate_in`/`implement`/`form`), `confidence`, `confidence_score`,
`source_file`. Capped at 3 per extraction chunk by convention, not enforced
by the schema.

**Surprises found during Phase 0 capture:**

1. **`.sql` files produce zero graph nodes.** graphify's `detect()` classifies
   `.sql` as `code`, and structural (AST) extraction only understands Python —
   it silently skips `.sql` files. Semantic (LLM) extraction only runs over
   `document`/`paper`/`image` categories, so `.sql` files get **no extraction
   pass at all** in a stock run. `tiny_graph.json` therefore has zero nodes for
   `analytics/orders_model.sql` and `analytics/stg_orders.sql` despite those
   files existing in `tiny_repo` for Phase 4's dbt-ref/SQL-literal linker
   fixtures. **Implication for Phase 4:** the linker cannot rely on SQL content
   already being present as graph nodes/edges — it must read `.sql` source
   files directly from disk (resolved via the repo root, not from graph.json)
   to find `ref()`/`source()` calls and table literals, then match against
   OKF table concepts. This is now normative for `linker.py`.
2. **Edges are keyed `links`, not `edges`**, and `hyperedges` appears twice
   (once nested under `graph`, once duplicated at the top level) — both are
   graphify's `to_json`/networkx serialization behavior, not a bug in this
   bridge. `schema.py` models both locations.
3. Node ids are not always fully qualified per the documented
   `{parent_dir}_{filename_stem}_{entity}` scheme — e.g. a local variable
   named `order` typed as class `Order` produced the bare id `order`, colliding
   in shape (though not value, here) with the class node `app_models_order`.
   The exporter's slug registry (E10) must not assume graphify ids are already
   collision-free across node types.

## 2. Export: graph.json → OKF bundle

| # | Rule | Level |
|---|------|-------|
| E1 | Every node maps to exactly one concept document at `<node_type_plural_slug>/<slug>.md`. | MUST |
| E2 | Frontmatter `type` is a human-readable namespaced value (`Code Class`, `Code Function`, `Doc`, `Rationale`, …), never empty (OKF §9). | MUST |
| E3 | Frontmatter carries `graphify_node_id: <original id>` for lossless identity round-trip. | MUST |
| E4 | Node source location → `resource: file://<relpath>#L<line>`. | MUST |
| E5 | Community membership → `tags: [community:<label>]`. | SHOULD |
| E6 | Docstrings and `# WHY:` / `# NOTE:` rationale → markdown body. | SHOULD |
| E7 | Every edge appears **twice**: as a markdown link in a `## Connections` body section (visible to untyped OKF consumers, §5.3) and as a typed entry in the `links:` frontmatter extension (§4.1 permits arbitrary keys):<br>`links: [{target: /<path>.md, rel: <relation>, confidence: extracted\|inferred}]` | MUST |
| E8 | Bundle root gets `index.md` with `okf_version: "0.1"` frontmatter; every directory gets a generated `index.md` (§6); root gets `log.md` with a Creation entry (§7). | MUST |
| E9 | Output is deterministic: byte-identical across runs on the same input (sorted iteration, stable slugs, no wall-clock timestamps). | MUST |
| E10 | Slug registry is bijective: node id ↔ concept id; collisions resolved with deterministic numeric suffixes. | MUST |
| E11 | Graph highlights (god nodes, communities) → `overview.md` at bundle root, `type: Overview`. | SHOULD |

## 3. Import: OKF bundle → graph.json

| # | Rule | Level |
|---|------|-------|
| I1 | Every non-reserved concept → one node. Id = `graphify_node_id` if present, else `okf:<concept_id>`. | MUST |
| I2 | Frontmatter `type` → node type; `resource` → node source; `title`/`description`/`tags`/body → node metadata. | MUST |
| I3 | Typed `links:` entries → edges with declared `rel` and `confidence`. | MUST |
| I4 | Plain body links with no matching `links:` entry → edges with relation `references`, confidence `EXTRACTED` (the link is explicit in the source document). | MUST |
| I5 | Reading is permissive per OKF §9: unknown types, unknown keys, and broken links produce warnings, never errors. Broken-link edges are dropped with a warning. | MUST |
| I6 | Round-trip guarantee: `import(export(g))` preserves node count, edge count, relations, and confidences. Titles and slugs may normalize. | MUST |
| I7 | Output is consumable by `graphify merge-graphs` unmodified. | MUST |

## 4. Linking: code graph ↔ data bundle

| # | Rule | Level |
|---|------|-------|
| L1 | Signals, priority order: (1) dbt `ref()`/`source()`; (2) SQL table identifiers after `FROM`/`JOIN`/`INSERT INTO` in string literals; (3) exact identifier↔table-name match, only when unambiguous on both sides. | MUST |
| L2 | Linker edges: relation `reads_from` or `writes_to`, confidence `INFERRED`, plus `linker_signal: dbt_ref \| sql_literal \| name_match`. | MUST |
| L3 | Ambiguity policy: ambiguous match → **no edge**, emit warning. Never guess. Precision over recall. | MUST |
| L4 | Commented-out code and partial-string matches never produce edges. | MUST |

## 5. Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-11 | Initial convention drafted. | Baseline from proposal + OKF v0.1 spec review. |
| 2026-07-11 | §1 filled from a real graphify capture; `.sql` files produce no graph nodes in a stock run. | graphify's AST pass is Python-only and semantic extraction skips the `code` file category entirely — `linker.py` (Phase 4) must read `.sql` sources from disk, not from graph.json. |
