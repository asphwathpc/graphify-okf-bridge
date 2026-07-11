# graphify-okf-bridge

**One knowledge layer for code and data.** A bridge between [Graphify](https://github.com/Graphify-Labs/graphify) code knowledge graphs and Google's [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) — so AI agents can traverse one connected graph from application code to warehouse tables.

> Status: **Phase 5 in progress** (core pipeline — export/import/link/validate — is done; skill packaging, demo, and release are underway). See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the roadmap and [docs/proposal.md](docs/proposal.md) for the full pitch.

## Quickstart

```bash
uv tool install graphify-okf-bridge   # (once published — see IMPLEMENTATION_PLAN.md Phase 5d)
# or, from a checkout:
uv sync && uv run okf-bridge --help

okf-bridge validate <bundle-dir>                            # OKF §9 conformance check + warnings
okf-bridge export  <graph.json> -o <bundle-dir>              # graphify graph -> OKF bundle
okf-bridge import  <bundle-dir> -o <graph.json>               # OKF bundle -> mergeable graphify graph
okf-bridge link    <graph.json> <bundle-dir> -o out.json --repo-root .   # infer code<->data edges
okf-bridge install-skill [--project]                          # install the /okf-bridge Claude Code skill
```

A typical flow: `graphify .` your codebase, `okf-bridge import` a data catalog bundle, `okf-bridge link` the two, `graphify merge-graphs` them together, then `graphify path`/`explain`/`query` (or an MCP client, see [`demo/mcp.md`](demo/mcp.md)) traverse the combined graph. Full worked example with a real public dbt project + GA4 in [`demo/README.md`](demo/README.md).

The mapping convention between Graphify's typed/confidence-tagged edges and OKF's markdown links — including the linker's signal priority and ambiguity policy — lives in [spec/MAPPING.md](spec/MAPPING.md) and is normative for this repo.

## Relationship to upstream

This is an independent bridge, not a fork of either project. It depends on the public `graphifyy` PyPI package and reads/writes plain OKF bundles — no upstream code is vendored except the fixtures in `tests/fixtures/okf_official/` (Apache-2.0, `UPSTREAM_LICENSE.md` included) and a reference copy of the spec in `spec/OKF_SPEC.md`. The `links:` frontmatter extension this bridge uses to carry typed/confidence-tagged edges through OKF (§Export E7 in `spec/MAPPING.md`) is a candidate for upstream proposal to `GoogleCloudPlatform/knowledge-catalog`, since OKF v0.1 links are otherwise untyped.

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
