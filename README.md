# graphify-okf-bridge

**One knowledge layer for code and data.** A bridge between [Graphify](https://github.com/Graphify-Labs/graphify) code knowledge graphs and Google's [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) — so AI agents can traverse one connected graph from application code to warehouse tables.

> Status: **pre-alpha, Phase 0 complete** (scaffold, fixtures, and graph.json schema discovery). See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the roadmap and [docs/proposal.md](docs/proposal.md) for the full pitch.

## What it will do

```
okf-bridge validate <bundle-dir>                    # OKF §9 conformance check
okf-bridge export  <graph.json> -o <bundle-dir>     # graphify -> OKF bundle
okf-bridge import  <bundle-dir> -o <graph.json>     # OKF bundle -> mergeable graphify graph
okf-bridge link    <graph.json> <bundle-dir> -o out.json   # infer code<->data edges
```

The mapping convention between Graphify's typed/confidence-tagged edges and OKF's markdown links lives in [spec/MAPPING.md](spec/MAPPING.md) — that document is normative for this repo.

## Development

```bash
uv sync                                  # install dev environment
uv run pytest                            # fast suite (integration tests deselected)
uv run pytest -m integration             # requires: uv tool install graphifyy
uv run ruff check . && uv run mypy       # lint + types
```

## Phase 0 artifacts

- `tests/fixtures/tiny_graph.json` — real graphify output captured over `tests/fixtures/tiny_repo` (AST extraction + one semantic-extraction pass), modeled exactly in `src/graphify_okf_bridge/graphify_io/schema.py`. See `spec/MAPPING.md` §1 for the observed shape and surprises (notably: `.sql` files produce zero graph nodes in a stock run).
- `tests/fixtures/okf_official/{ga4,stackoverflow,crypto_bitcoin}` — vendored official OKF bundles (Apache-2.0, `UPSTREAM_LICENSE.md` included) used as golden read fixtures.
- `spec/OKF_SPEC.md` — vendored copy of the upstream OKF v0.1 SPEC.md for reference.

Proceed phase by phase — every session starts with: *"Read CLAUDE.md and IMPLEMENTATION_PLAN.md. We are on Phase N. Confirm the DoD, write the phase's failing tests, then implement."*

## License

Apache-2.0. Vendored test fixtures under `tests/fixtures/okf_official/` are from [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog) (Apache-2.0).
