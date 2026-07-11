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

**§1 correction before implementation:** the original draft of E1/E2 (below)
assumed an AST-level `node_type` finer than what graph.json actually carries
(`Code Class`, `Code Function`, …). The real schema only has the coarse
`file_type` enum (`code`/`document`/`paper`/`image`/`rationale`/`concept`,
§1) — there is no per-node signal distinguishing a class from a function.
Per ground rule 1/4 (MAPPING.md wins, update it first), E1/E2 are revised to
map directly off `file_type` rather than inventing a classifier. Likewise E5
originally assumed a community *label*; graph.json's `community` field is a
bare int with no label anywhere in the document, so tags carry the int only.

| # | Rule | Level |
|---|------|-------|
| E1 | Every node maps to exactly one concept document at `<file_type>/<slug>.md` (`file_type` used verbatim as the directory: `code/`, `document/`, `paper/`, `image/`, `rationale/`, `concept/`). | MUST |
| E2 | Frontmatter `type` is `file_type` title-cased (`Code`, `Document`, `Paper`, `Image`, `Rationale`, `Concept`), never empty (OKF §9). | MUST |
| E3 | Frontmatter carries `graphify_node_id: <original id>` for lossless identity round-trip. | MUST |
| E4 | Node source location → `resource: file://<source_file>#<source_location>` (`source_location` is graphify's own `"L<n>"` string, used as-is); omit the fragment when `source_location` is `null`. | MUST |
| E5 | Community membership → `tags: [community:<community-int>]`; omitted when `community` is `null`. | SHOULD |
| E6 | For `file_type: rationale` nodes, `label` (graphify's own extracted docstring / `# WHY:` / `# NOTE:` text — already truncated by graphify where applicable, not further truncated here) → markdown body. Other file types get an empty body except for the generated `## Connections` section (E7). | SHOULD |
| E6b | Frontmatter `description` is synthesized (never left empty): rationale nodes reuse `label` verbatim; all other nodes get `` `<type>` node `<label>` (`<source_file>`) `` — ground rule 5 requires bridge-authored bundles to pass `validate --strict` with zero warnings, and the validator warns on missing `description`. | MUST |
| E7 | Every edge appears **twice**, rendered once from the edge's `source` concept: as a markdown link in a `## Connections` body section (visible to untyped OKF consumers, §5.3) and as a typed entry in the `links:` frontmatter extension (§4.1 permits arbitrary keys):<br>`links: [{target: /<path>.md, rel: <relation>, confidence: <lowercased edge.confidence>}]`. `confidence` is graphify's `EXTRACTED`/`INFERRED`/`AMBIGUOUS` lowercased verbatim — MAPPING originally enumerated only `extracted\|inferred`; `ambiguous` is preserved too rather than dropped (ground rule: never silently diverge / drop information). | MUST |
| E8 | Bundle root gets `index.md` with `okf_version: "0.1"` frontmatter; every directory gets a generated `index.md` (§6). Root `log.md` generation (§7) is **deferred**: OKF marks it optional (MAY), and graph.json carries no date field anywhere (`built_at_commit` is a commit hash, not a timestamp) — synthesizing a wall-clock date to populate the required `## YYYY-MM-DD` heading would violate ground rule 4 (determinism: no timestamps except ones derived from input data). Revisit if/when graphify exposes a build timestamp. | MUST (index) / DEFERRED (log) |
| E9 | Output is deterministic: byte-identical across runs on the same input (sorted iteration, stable slugs, no wall-clock timestamps). | MUST |
| E10 | Slug registry is bijective per directory: node id ↔ concept id within its `file_type` bucket; collisions resolved with deterministic numeric suffixes. Slugs are generated from `label`, not `id` (friendlier filenames); the registry keeps identity via `node_id`. | MUST |
| E11 | Graph highlights (node/edge counts, top nodes by degree) → `overview.md` at bundle root, `type: Overview`, degree ranking sorted `(-degree, node_id)` for determinism. Hyperedges are **not** exported in v0.1 — OKF has no n-ary relationship primitive and typed `links:` are binary; revisit if/when a multi-target convention is proposed upstream (see docs/proposal.md roadmap v0.4). | SHOULD |

## 3. Import: OKF bundle → graph.json

| # | Rule | Level |
|---|------|-------|
| I1 | Every non-reserved concept → one node, **except** the bundle-root `overview` concept with `type: Overview` and no `graphify_node_id` — that file is exporter-synthesized aggregate reporting (E11), not a graph entity, so importing it back would inflate the node count on every round-trip. A foreign bundle that happens to have its own unrelated `overview.md` is unaffected by this exclusion unless it also matches `type: Overview` with no `graphify_node_id`. Id = `graphify_node_id` if present, else `okf:<concept_id>`. | MUST |
| I2 | Frontmatter `type` → node `file_type` (lowercased; this inverts exporter rule E2's `.title()`). `resource` → node `source_file`/`source_location`: an `file://<path>#<loc>` resource splits on the first `#`; a bare `file://<path>` yields no `source_location`; a non-`file://` resource (e.g. a foreign bundle's `https://` URL) is carried through verbatim as `source_file` since graph.json has no separate field for an external resource URI; a missing `resource` falls back to `source_file: okf:<concept_id>` so the field is never empty. `title` → `label` (falls back to the concept id's basename when `title` is absent). A `community:<int>` tag → node `community`; every other tag, plus `description` and non-empty `body`, is preserved losslessly as `okf_tags`/`okf_description`/`okf_body` extra keys (graph.json's `Node` has no dedicated slots for them — ground rule 3 forbids inventing fields not observed in real graphify output, so foreign metadata rides along as `extra="allow"` keys instead). The original (pre-lowercase) `type` string is preserved as `okf_type` for lossless carry of compound/foreign type names (e.g. `BigQuery Table`). | MUST |
| I3 | Typed `links:` entries → edges with declared `rel` and `confidence` (uppercased; inverts exporter rule E7's `.lower()`). Since `graph.json` edges require `confidence_score` and `source_file` fields that OKF has no equivalent for, they are synthesized: `confidence_score` is `1.0` for `EXTRACTED`, `0.75` for `INFERRED`/`AMBIGUOUS` (a documented placeholder — the exact original score is not recoverable from a bundle); `source_file` reuses the *source* concept's own resolved `source_file` (I2), matching graph.json's convention that an edge's `source_file` is where the edge was extracted from. | MUST |
| I4 | Plain body links with no matching `links:` entry (matched by target concept id only, ignoring `rel` — an edge's typed entry and body-link line always share the same target per E7) → edges with relation `references`, confidence `EXTRACTED` (the link is explicit in the source document). | MUST |
| I5 | Reading is permissive per OKF §9: unknown types, unknown keys, and broken links produce warnings, never errors. A `links:` entry or body link whose target concept id doesn't resolve within the bundle is dropped with a warning rather than raising or producing a dangling edge. | MUST |
| I6 | Round-trip guarantee: `import(export(g))` preserves node count, edge count, relations, and confidences. Titles, slugs, and `confidence_score` may normalize (see I2/I3). | MUST |
| I7 | Output is consumable by `graphify merge-graphs` unmodified: `directed: false`, `multigraph: false` (graphify's default build shape, §1), empty `hyperedges` (hyperedge import is out of scope — the exporter doesn't emit them either, E11). | MUST |

## 4. Linking: code graph ↔ data bundle

| # | Rule | Level |
|---|------|-------|
| L1 | Signals, priority order: (1) dbt `ref()`/`source()`; (2) SQL table identifiers after `FROM`/`JOIN`/`INSERT INTO` in string literals; (3) exact identifier↔table-name match, only when unambiguous on both sides. | MUST |
| L2 | Linker edges: relation `reads_from` or `writes_to`, confidence `INFERRED`, plus `linker_signal: dbt_ref \| sql_literal \| name_match`. | MUST |
| L3 | Ambiguity policy: ambiguous match → **no edge**, emit warning. Never guess. Precision over recall. | MUST |
| L4 | Commented-out code and partial-string matches never produce edges. | MUST |
| L5 | **Table concepts** are OKF concepts whose `concept_id` starts with `tables/` (matches all vendored bundles, §1); the table's match-name is `posixpath.basename(concept_id)`, lowercased. A name with zero matching table concepts is silently skipped (e.g. a dbt ref to an uncatalogued intermediate model — normal, not an error); a name matching **more than one** table concept is the L3 ambiguity case (warning, no edge). | MUST |
| L6 | **Repo root**: `linker.link()` takes an explicit `repo_root: Path` (CLI: `--repo-root`, default `.`) used *only* to discover source files absent from `graph.json` (`*.sql`, per §1 surprise 1 — graphify's structural pass is Python-only). Existing node `source_file` values are read as-is (already resolved relative to CWD by graphify itself) — `repo_root` is never joined onto them. This is a deliberate, explicit input rather than inferred from the graph: the very files the linker most needs to find (`.sql`) are, by construction, invisible to `graph.json`, so no path-common-prefix trick over existing nodes can discover a sibling directory that contains only files the graph never saw. | MUST |
| L7 | **Scan granularity is per-file, not per-node.** For every `file_type: code` / `_origin: ast` node's `source_file` (deduplicated), and for every `*.sql` file found under `repo_root`, the whole file text is scanned once. Rationale: `source_location` is a single line pointer, not a span, so it cannot bound "the text belonging to this node" for a multi-line SQL string; scanning the file once and dedup­ing matches is simpler and avoids fabricating span-inference logic. The **edge source** for a `.py` file is that file's *module node* (the node with the lowest line number among its `_origin: ast` nodes — ties broken by node id); for a `.sql` file (no nodes) it is a synthetic node `sql:<path relative to repo_root>`, `file_type: code`, emitted alongside the edges so the output graph stays self-consistent. Semantically-extracted nodes (no `_origin: "ast"`, e.g. `app_service_revenue_query` in the tiny fixture — see §1 surprise 4) are excluded from file/module inference: their `source_file` is relative to the *document* they were extracted from, not the code tree, and using them would misattribute edges. | MUST |
| L8 | **Comment stripping**: a whole line is dropped before scanning if its lstripped text starts with `#` (Python) or `--` (SQL). Inline (end-of-line) comments are out of scope for v1 — no fixture case requires them, and guessing at string-vs-comment context without a real tokenizer risks false negatives on legitimate matches, which is the wrong failure mode for this linker (ground rule: don't add unvalidated speculative parsing). | MUST |
| L9 | **dbt signal** (SQL files only): `{{ ref('X') }}` → target `X`; `{{ source('A', 'B') }}` → target `B` (the table, not the source name `A` — v1 does not disambiguate by dataset). **SQL-literal signal** (both `.py` and `.sql` files): regex `\b(FROM\|JOIN\|INSERT\s+INTO)\s+([A-Za-z_][A-Za-z0-9_.]*)` after stripping backticks from the line; `INSERT INTO` → `writes_to`, `FROM`/`JOIN` → `reads_from`; a qualified name (`schema.table`) resolves against its last dot-segment. Matches are deduplicated per `(source, target, relation)` within a file (a table mentioned twice in one file produces one edge). | MUST |
| L10 | **Exact-name fallback algorithm**: for each table concept (L5), compute its singular stem (strip one trailing `s`). Scan every graph node with `file_type` in `{code, concept}` (rationale/document/paper/image prose is excluded — a docstring *describing* "the customers table" is not itself a code identifier named `customers`, and would otherwise make every fixture case ambiguous by accident) — tokenize its `label` on runs of `[a-z0-9_]` (underscore stays part of a word, so `load_customer` is one token, not a false hit on `customer`), singularize each token the same way, and collect nodes whose token set contains the stem — **grouped by raw `label`** (not by node id) so that AST re-mentions of the same surface identifier (§1 surprise 3: a bare local-variable node like `order` sharing a label with its class node `app_models_order`) collapse into one logical candidate instead of manufacturing false ambiguity. If more than one *distinct label* remains a candidate (e.g. the class `Order` **and** the unrelated concept node `docs_adr_0001_orders_table`, semantically extracted from ADR-0001's prose mention of "the `orders` table" — a real second reference to the same name, not an AST artifact), the match is ambiguous (L3): warning, no edge. If exactly one distinct label remains, the canonical source node is the one whose id is *not* identical to its own `norm_label` (prefers a qualified definition site like `app_models_customer` over a bare usage-site node like `customer`; ties broken lexicographically). | MUST |
| L11 | **Linker edge target id** is `okf:<table-concept-id>` — the same id an `okf-bridge import` of the same bundle would assign that concept (Import rule I1), so `okf-bridge link`'s output composes with `okf-bridge import` + `graphify merge-graphs` without inventing a second identity for the same table. | MUST |
| L12 | **Confidence score rubric** (graph.json's documented INFERRED range is 0.55–0.95, §1): `dbt_ref` 0.95 (explicit, unambiguous reference syntax), `sql_literal` 0.75 (regex-matched, medium trust), `name_match` 0.55 (weakest — heuristic fallback, hence lowest priority in L1). | SHOULD |

**§1 addendum (surprise 4, found during Phase 4):** semantically-extracted nodes can carry a `source_file` relative to the *document being processed*, not the code tree — e.g. `app_service_revenue_query` (`file_type: code`, no `_origin`) has `source_file: "docs/adr-0001.md"` even though it represents a Python constant (`REVENUE_QUERY` in `app/service.py`); its `source_location` is `null`. Only `_origin: "ast"` nodes have filesystem-resolvable `source_file`/`source_location`. `linker.py` (L7) filters on `_origin: "ast"` for this reason.

## 5. Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-11 | Initial convention drafted. | Baseline from proposal + OKF v0.1 spec review. |
| 2026-07-11 | §1 filled from a real graphify capture; `.sql` files produce no graph nodes in a stock run. | graphify's AST pass is Python-only and semantic extraction skips the `code` file category entirely — `linker.py` (Phase 4) must read `.sql` sources from disk, not from graph.json. |
| 2026-07-11 | §Export (E1/E2/E5) revised to map off `file_type` instead of an invented AST-level node type; §Export (E8) defers `log.md` generation. | graph.json has no finer type signal than `file_type` and no community label or build date — MAPPING.md is corrected to ground truth before Phase 2 implementation, per ground rule 1/4. |
| 2026-07-11 | §Import (I1-I3) detailed before Phase 3 implementation: the synthetic `overview` concept is excluded from import; node/edge reconstruction for fields graph.json requires but OKF has no equivalent for (`file_type` casing, `source_file` for non-`file://` resources, `confidence_score`, edge `source_file`) is pinned down; foreign tags/description/body ride along as `okf_*` extra keys. | graph.json's `Node`/`Edge` schemas (§1) have several required-in-practice fields (`confidence_score`, edge `source_file`) and no generic metadata slot (no `description`, no free-form `tags`) — importing official/foreign bundles that don't carry Graphify-shaped data needs a documented, deterministic fallback rather than an undocumented one invented mid-implementation. |
| 2026-07-11 | §Linking (L5-L12) detailed before Phase 4 implementation: table concepts scoped to `tables/` directory; explicit `repo_root` input (never inferred) for discovering `.sql` files; per-file (not per-node) scan granularity with module-node/synthetic-node edge sources; exact-name fallback dedupes AST re-mentions by raw label before checking ambiguity; linker edge targets reuse the importer's `okf:<concept_id>` id so `link` output composes with `import` + `graphify merge-graphs`. | The tiny fixture was deliberately built (Phase 0) with a real ambiguity trap: `docs_adr_0001_orders_table`, semantically extracted from ADR-0001's prose, is a second, legitimate reference to "orders" alongside the `Order` class — collapsing AST duplicates by label (not id) is what lets `customers` resolve unambiguously while `orders` correctly stays ambiguous (L3), rather than both or neither matching by accident. |
