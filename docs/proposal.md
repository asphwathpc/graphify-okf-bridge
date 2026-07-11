# graphify-okf-bridge

**One knowledge layer for code and data.** An open-source bridge that makes [Graphify](https://github.com/Graphify-Labs/graphify) a first-class producer and consumer of Google's [Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) — so AI agents can traverse one connected graph from application code all the way to warehouse tables and business metrics.

---

## Problem

Organizations hold their technical knowledge in two disconnected silos:

- **Code knowledge** — what calls what, why a hack exists, how services connect. Graphify captures this as a local, queryable knowledge graph (`graph.json`), built with tree-sitter AST parsing across ~40 languages.
- **Data knowledge** — what a table means, its schema, lineage, and business context. Google's Knowledge Catalog captures this, and OKF v0.1 is its vendor-neutral export format: plain markdown files with YAML frontmatter, organized in a directory hierarchy.

An agent debugging *"why is revenue wrong in this dashboard?"* cannot today traverse from the dashboard's SQL to the pipeline code that populates the table. The two graphs speak different formats, so the traversal dies at the boundary.

Both sides are graph-shaped. Neither speaks the other's language. That is the entire gap this project closes.

## Solution

Two commands and a mapping convention:

1. **`graphify export okf`** — converts a Graphify `graph.json` into a valid OKF bundle (markdown + YAML frontmatter), browsable in Obsidian, MkDocs, Notion, or OKF's own `viz.html` viewer, and versionable in git.
2. **`graphify import okf <bundle>`** — merges any OKF bundle (e.g., a BigQuery dataset enriched by the OKF reference agent) into an existing Graphify graph, resolving cross-silo links (SQL table names in code ↔ table concepts in the bundle).
3. **A mapping convention** — a documented, reversible mapping between Graphify's typed/confidence-tagged edges and OKF's markdown links. This convention is itself a contribution candidate for the OKF v0.x spec, which currently has no way to express edge types or provenance.

## Architecture

```
                         ┌─────────────────────────────────────┐
                         │            graphify-okf-bridge      │
                         │                                     │
  ┌──────────────┐       │  ┌───────────┐      ┌────────────┐  │      ┌──────────────────┐
  │  Codebase    │       │  │ Exporter  │─────▶│ OKF bundle │  │      │ Consumers        │
  │  (any repo)  │──────▶│  │ graph.json│      │ *.md + YAML│──┼─────▶│ Obsidian, MkDocs,│
  └──────────────┘  ▲    │  │  → OKF    │      └────────────┘  │      │ viz.html, LLMs,  │
                    │    │  └───────────┘                      │      │ git / PR review  │
              graphify   │                                     │      └──────────────────┘
              (tree-     │  ┌───────────┐      ┌────────────┐  │
               sitter)   │  │ Importer  │◀─────│ OKF bundle │◀─┼── OKF enrichment agent
                         │  │ OKF →     │      │ (external) │  │    (BigQuery, Dataplex,
  ┌──────────────┐       │  │ graph.json│      └────────────┘  │     Unity Catalog, …)
  │ Merged graph │◀──────┼──┴───────────┘                      │
  │ code + data  │       │  ┌────────────────────────────────┐ │
  └──────┬───────┘       │  │ Linker: resolves cross-silo    │ │
         │               │  │ refs (SQL strings in code ↔    │ │
         ▼               │  │ table concepts in bundle)      │ │
   graphify query /      │  └────────────────────────────────┘ │
   path / explain /      └─────────────────────────────────────┘
   MCP server
```

### Components

**Exporter (`export okf`).** Walks `graph.json`; each node becomes `<type>/<slug>.md` with frontmatter (`type`, `resource` = `file:line`, `tags` = community labels, `timestamp`) and a body containing the node's docstring/rationale (`# NOTE:` / `# WHY:` comments Graphify already extracts). Edges become markdown links in a `## Connections` section. Auto-generates `index.md` per directory for OKF's progressive-disclosure pattern.

**Importer (`import okf`).** Parses a bundle's frontmatter + link graph into Graphify node/edge records and merges via Graphify's existing `merge-graphs`. Imported edges are tagged `EXTRACTED` (explicit markdown link) per Graphify's confidence model.

**Linker.** The high-value piece. Heuristics + optional LLM pass that connect the two halves: string-literal SQL table references, dbt `ref()`/`source()` calls, ORM model ↔ table name matches, and config-file dataset IDs each produce an `INFERRED` edge from a code node to a data concept.

**Edge-semantics convention.** OKF links carry no type or provenance. Proposal: encode both in a frontmatter `links:` block —

```yaml
links:
  - target: tables/orders.md
    rel: writes_to        # calls | imports | inherits | writes_to | reads_from | …
    confidence: inferred   # extracted | inferred
```

— while keeping the plain markdown link in the body so untyped consumers (Obsidian, viz.html) still work. This is backward-compatible with OKF v0.1 ("bundles can carry arbitrary extra frontmatter keys") and is the piece to propose upstream.

## MVP scope

Deliberately a bridge, not a platform:

1. `export okf` producing bundles that pass OKF spec validation and render in the reference `viz.html`.
2. `import okf` round-tripping the OKF sample bundles (GA4, Stack Overflow, Bitcoin) into a Graphify graph without loss.
3. Linker v1: dbt `ref()`/`source()` and literal SQL table-name matching only.
4. **One killer demo**: a public dbt project + the GA4 BigQuery OKF bundle, merged, answering `graphify path "orders_model.sql" "events_ table"` end to end. Recorded as a GIF for the README.

Out of scope for MVP: bidirectional sync, non-BigQuery catalogs, real-time updates, any hosted service.

## Roadmap

- **v0.1 (weeks 1–4):** exporter + spec validation + viz.html rendering.
- **v0.2 (weeks 5–8):** importer + merge; round-trip tests on the three official sample bundles.
- **v0.3 (weeks 9–12):** linker v1; the dbt + GA4 demo; publish to PyPI as a Graphify plugin or PR to Graphify core.
- **v0.4:** propose the `links:` edge-semantics convention to the OKF spec via issue/PR on `GoogleCloudPlatform/knowledge-catalog`; add Unity Catalog/Collibra bundle fixtures contributed by the community.

## Why now, and why this will land

- OKF is at **v0.1 with almost no third-party producers**. The spec explicitly invites external tools ("export pipelines from existing catalogs… or scripts walking a database"); a Graphify exporter would be among the first real interoperability demos, which is exactly the kind of contribution early specs amplify.
- Graphify already has the primitives: `merge-graphs`, an MCP server, typed edges, and a wiki exporter — the bridge is a natural extension, making an upstream PR plausible rather than a fork.
- Both projects are Apache-2.0-compatible and actively maintained, so licensing is clean.

## Impact

- **Agents get end-to-end context**: code → pipeline → table → metric in one traversal, over MCP, instead of two dead-ended silos.
- **Graphify graphs become portable**: git-diffable markdown, readable without Graphify installed.
- **Data catalogs gain code-level lineage** — historically their weakest layer — for free.

Real-world workflows unlocked: data-incident root-cause (broken metric → offending commit), impact analysis before dropping a column, onboarding ("how does billing work here?" answered across schema and code), and auditable GDPR-style PII-flow reviews as markdown PRs.

## Risks

- **Lossy mapping.** Graphify edge types/confidence don't exist in OKF. Mitigated by the frontmatter convention; round-trip tests enforce reversibility.
- **Spec drift.** OKF is v0.1 and may change. Mitigated by pinning to spec versions and keeping the mapping layer isolated in one module.
- **Linker false positives.** Table-name string matching is noisy. Mitigated by tagging all linker output `INFERRED` and starting with high-precision signals (dbt refs) only.
- **Upstream appetite.** Graphify or OKF maintainers may not want it in-tree. Mitigated by shipping standalone-first (plugin architecture), upstreaming opportunistically.

## Project logistics

- **License:** Apache 2.0 (matches both upstreams).
- **Language:** Python (matches Graphify's CLI and OKF's reference agent).
- **Repo layout:** `bridge/exporter.py`, `bridge/importer.py`, `bridge/linker.py`, `spec/MAPPING.md` (the convention doc), `tests/fixtures/` (official OKF sample bundles), `demo/` (dbt + GA4 walkthrough).
- **First three good-first-issues:** add a language to linker heuristics, add an OKF sample-bundle fixture, render `Connections` sections in the wiki exporter.
