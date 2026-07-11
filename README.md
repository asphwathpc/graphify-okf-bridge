# graphify-okf-bridge

**One knowledge layer for code and data.** A bridge between [Graphify](https://github.com/Graphify-Labs/graphify) code knowledge graphs and Google's [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) — so AI agents can traverse one connected graph from application code to warehouse tables.

> Status: **pre-alpha, Phase 0** (scaffold). See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the roadmap and [docs/proposal.md](docs/proposal.md) for the full pitch.

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

## Remaining Phase 0 setup (do these before Phase 1)

1. **Capture real graphify output** (needs graphify on your machine):

   ```bash
   uv tool install graphifyy
   graphify install
   # in your AI assistant, from the repo root:
   #   /graphify tests/fixtures/tiny_repo
   cp graphify-out/graph.json tests/fixtures/tiny_graph.json
   ```

2. **Derive the schema**: hand Claude Code the Phase 0 prompt from IMPLEMENTATION_PLAN.md to generate `src/graphify_okf_bridge/graphify_io/schema.py` from the real `tiny_graph.json`.

3. **Vendor the official OKF bundles** as golden fixtures:

   ```bash
   git clone --depth 1 https://github.com/GoogleCloudPlatform/knowledge-catalog /tmp/kc
   mkdir -p tests/fixtures/okf_official
   cp -r /tmp/kc/okf/bundles/ga4 /tmp/kc/okf/bundles/stackoverflow /tmp/kc/okf/bundles/crypto_bitcoin tests/fixtures/okf_official/
   cp /tmp/kc/LICENSE.md tests/fixtures/okf_official/UPSTREAM_LICENSE.md
   ```

Then proceed phase by phase — every session starts with: *"Read CLAUDE.md and IMPLEMENTATION_PLAN.md. We are on Phase N. Confirm the DoD, write the phase's failing tests, then implement."*

## License

Apache-2.0. Vendored test fixtures under `tests/fixtures/okf_official/` are from [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog) (Apache-2.0).
