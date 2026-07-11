# MAPPING.md — Graphify ↔ OKF mapping convention

**Normative for this repository.** If code and this document disagree, this document wins; change it first (with rationale in the PR), then the code.

Referenced specs: [OKF v0.1 SPEC.md](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) · Graphify `graph.json` (observed schema, §1).

---

## 1. graph.json observed schema

> **TBD — Phase 0.** To be filled from `tests/fixtures/tiny_graph.json` (real graphify output). Model only observed fields; unknown keys are preserved (`extra="allow"`).

Expected shape (to verify): nodes with `id`, `label`, `type`, `source` (file + line), `community`; edges with `source`, `target`, `relation` (`calls`, `imports`, `inherits`, `uses`, `method`, `references`, …), `confidence` (`EXTRACTED` | `INFERRED`).

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
