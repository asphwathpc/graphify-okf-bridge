# graphify-okf-bridge

[![PyPI](https://img.shields.io/pypi/v/graphify-okf-bridge)](https://pypi.org/project/graphify-okf-bridge/)
[![CI](https://github.com/asphwathpc/graphify-okf-bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/asphwathpc/graphify-okf-bridge/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**One knowledge layer for code and data.** A bridge between [Graphify](https://github.com/Graphify-Labs/graphify) code knowledge graphs and Google's [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) — so AI agents can traverse one connected graph from application code to warehouse tables.

`v0.1.0` — [published on PyPI](https://pypi.org/project/graphify-okf-bridge/). See [docs/proposal.md](docs/proposal.md) for the full pitch and [spec/MAPPING.md](spec/MAPPING.md) for the normative mapping convention.

## What is this?

Organizations keep their technical knowledge in two disconnected silos. **Code knowledge** — what calls what, why a hack exists, how services connect — lives in tools like Graphify, which builds a local, queryable graph (`graph.json`) from a codebase via tree-sitter AST parsing. **Data knowledge** — what a table means, its schema, lineage, and business context — lives in data catalogs, and OKF v0.1 is Google's vendor-neutral export format for it: plain markdown files with YAML frontmatter.

Both are graph-shaped. Neither speaks the other's language. An agent debugging *"why is revenue wrong in this dashboard?"* can't today walk from the dashboard's SQL to the pipeline code that populates the table — the traversal dies at the format boundary. `graphify-okf-bridge` closes that gap with four small, composable commands:

- **`export`** — turn a Graphify `graph.json` into a browsable, git-diffable OKF bundle.
- **`import`** — pull any OKF bundle (e.g. a BigQuery dataset, a Dataplex catalog export) into a graph Graphify can merge.
- **`link`** — infer the missing edges between the two: code that reads/writes a table it never explicitly declared a Graphify edge to.
- **`validate`** — check a bundle for OKF §9 conformance.

The result is one merged graph that `graphify path` / `explain` / `query` — or an MCP client — can traverse end-to-end, from a line of application code to the warehouse table it feeds.

## How it's built

The core is pure functions over plain data models, with a thin CLI on top (`click`), so every mapping decision is unit-testable without touching disk or a real Graphify install:

- **`src/graphify_okf_bridge/okf/`** — the OKF model, reader, writer, and validator (permissive on read, strict on write — bundles this tool writes always pass `validate --strict`).
- **`exporter.py` / `importer.py`** — pure `export()` / `import_bundle()` functions implementing the Graphify ↔ OKF mapping documented in [spec/MAPPING.md](spec/MAPPING.md): each graph node becomes a `<file_type>/<slug>.md` concept; each edge becomes both a markdown link in the body (so untyped OKF consumers render it) *and* a typed entry in a `links:` frontmatter extension (`{target, rel, confidence}`), so the round-trip `import(export(g))` preserves node count, edge count, relations, and confidences exactly.
- **`linker.py`** — the highest-value piece. It resolves code↔data references that exist in neither source graph on its own, trying signals in priority order: dbt `ref()`/`source()` calls → literal SQL (`FROM`/`JOIN`/`INSERT INTO`) → exact-name fallback. Ambiguous matches produce no edge (precision over recall); every inferred edge is tagged `confidence: INFERRED` with a `linker_signal` provenance key. `.sql` files are invisible to a stock `graph.json`, so the linker scans them from disk via `--repo-root`.
- **`cli.py`** — argument parsing and I/O only; no mapping logic lives here.

Stack: Python 3.11+, `click` for the CLI, `pydantic` for models, `pyyaml` + `python-frontmatter` for reading/writing OKF markdown. Determinism is a hard requirement — exports are byte-identical across runs (sorted iteration, stable slugs, no timestamps except ones derived from input data).

```
  Codebase          graphify              OKF bundle           Consumers
  (any repo)  ───▶  graph.json  ──export──▶ *.md + YAML  ───▶  Obsidian, MkDocs,
                        ▲                       │              viz.html, LLMs,
                        │                    import            git / PR review
                        │                       ▼
                   Merged graph  ◀──link──  OKF bundle  ◀── data catalog / OKF
                   (code + data)             (external)      enrichment agent
```

## Install

```bash
uv tool install graphify-okf-bridge
# or:
pip install graphify-okf-bridge
```

From a checkout, for development:

```bash
uv sync && uv run okf-bridge --help
```

The `export`/`import`/`link`/`validate` commands work standalone on a `graph.json` and/or OKF bundle you already have. To generate a `graph.json` from a codebase, or to merge/traverse the bridged output, you'll also want Graphify itself: `uv tool install graphifyy`.

## Quickstart

```bash
okf-bridge validate <bundle-dir>                                        # OKF §9 conformance check + warnings
okf-bridge export  <graph.json> -o <bundle-dir>                         # graphify graph -> OKF bundle
okf-bridge import  <bundle-dir> -o <graph.json>                         # OKF bundle -> mergeable graphify graph
okf-bridge link    <graph.json> <bundle-dir> -o out.json --repo-root .  # infer code<->data edges
okf-bridge install-skill [--project]                                    # install the /okf-bridge Claude Code skill
```

A typical flow: `graphify .` your codebase, `okf-bridge import` a data catalog bundle, `okf-bridge link` the two, `graphify merge-graphs` them together, then `graphify path`/`explain`/`query` (or an MCP client, see [`demo/mcp.md`](demo/mcp.md)) to traverse the combined graph. Full worked example with a real public dbt project + GA4 in [`demo/README.md`](demo/README.md).

## Use cases & benefits

Merging code and data graphs turns two dead-ended silos into one traversable graph, which unlocks workflows that are painful or impossible when the two live apart:

- **Data-incident root cause.** A dashboard metric is wrong. Instead of manually cross-referencing a data catalog with a code search, walk the merged graph directly from the broken table concept back to the pipeline code — and from there to the commit that changed it.
- **Impact analysis before a schema change.** "Is it safe to drop this column?" — traverse from the table concept forward to every piece of code that reads from it, before you break something downstream.
- **Faster onboarding.** A new engineer asks "how does billing work here?" — one traversal answers it across both the application code *and* the warehouse schema, instead of two separate, disconnected docs.
- **Auditable PII/GDPR reviews.** Because OKF bundles are plain markdown, a review of "everywhere this PII field flows" is a readable, diffable markdown artifact — reviewable as a normal PR, not a query against a proprietary catalog UI.
- **Portable, tool-agnostic knowledge.** Exported bundles are just markdown + YAML — browsable in Obsidian or MkDocs, versionable in git, and readable by anyone without Graphify installed.
- **Agent-ready context over MCP.** An LLM agent debugging or extending a system gets one connected graph to query — code → pipeline → table → metric — in a single traversal, instead of stitching together two tools by hand.

## Demo

![graphify path and graphify explain traversing a graph merged by graphify-okf-bridge](demo/hero.gif)

A real public dbt project ([`dbt-labs/jaffle-shop`](https://github.com/dbt-labs/jaffle-shop)) merged with Google's official GA4 OKF sample bundle, ending in a single graph that `graphify path` walks from a dbt model file straight into its warehouse table lineage — including an edge the linker inferred that didn't exist in either source system on its own. Full walkthrough, requirements, and how to regenerate the GIF: [`demo/README.md`](demo/README.md).

## Relationship to upstream

This is an independent bridge, not a fork of either project. It depends on the public `graphifyy` PyPI package and reads/writes plain OKF bundles — no upstream code is vendored except the fixtures in `tests/fixtures/okf_official/` (Apache-2.0, `UPSTREAM_LICENSE.md` included) and a reference copy of the spec in `spec/OKF_SPEC.md`. The `links:` frontmatter extension this bridge uses to carry typed/confidence-tagged edges through OKF (§Export E7 in `spec/MAPPING.md`) has been proposed upstream to `GoogleCloudPlatform/knowledge-catalog` ([issue #183](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/183)), since OKF v0.1 links are otherwise untyped. A standalone-vs-in-tree offer is also open against Graphify itself ([graphify#1801](https://github.com/Graphify-Labs/graphify/issues/1801)).

## Development

```bash
uv sync                                  # install dev environment
uv run pytest                            # fast suite (integration tests deselected), <10s
uv run pytest -m integration             # requires: uv tool install graphifyy
uv run ruff check . && uv run mypy src/  # lint + types
```

Proceed phase by phase — every session starts with: *"Read CLAUDE.md and IMPLEMENTATION_PLAN.md. We are on Phase N. Confirm the DoD, write the phase's failing tests, then implement."*

## Repository layout

- `src/graphify_okf_bridge/okf/` — pure OKF model/reader/writer/validator (extractable as its own library later).
- `src/graphify_okf_bridge/exporter.py` / `importer.py` / `linker.py` — pure functions over the graphify ↔ OKF mapping; `cli.py` is a thin wrapper.
- `src/graphify_okf_bridge/skill/SKILL.md` — the Claude Code skill, installed via `okf-bridge install-skill`.
- `tests/fixtures/tiny_graph.json` — real graphify output captured over `tests/fixtures/tiny_repo`, modeled exactly in `src/graphify_okf_bridge/graphify_io/schema.py`. See `spec/MAPPING.md` §1 for the observed shape and surprises (notably: `.sql` files produce zero graph nodes in a stock graphify run — the linker reads them from disk instead).
- `tests/fixtures/okf_official/{ga4,stackoverflow,crypto_bitcoin}` — vendored official OKF bundles, used as golden read fixtures.
- `demo/` — end-to-end walkthrough (real dbt project + GA4) and MCP notes.

## License

Apache-2.0. Vendored test fixtures under `tests/fixtures/okf_official/` are from [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog) (Apache-2.0).
