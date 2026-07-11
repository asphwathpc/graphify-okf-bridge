# Demo: dbt + GA4, one connected graph

This walks a real public dbt project ([`dbt-labs/jaffle-shop`](https://github.com/dbt-labs/jaffle-shop))
and Google's official [GA4 OKF sample bundle](https://github.com/GoogleCloudPlatform/knowledge-catalog)
through the full `graphify-okf-bridge` pipeline, ending with a single merged
`graph.json` that `graphify path` can traverse from a dbt model file straight
into its warehouse table lineage.

## Why two data bundles?

jaffle-shop's own tables (`customers`, `orders`, `order_items`, ...) don't
appear anywhere in GA4's schema (GA4's only table is `events_`) — pairing an
unrelated code repo with an unrelated data bundle would make the linker
(deliberately high-precision, see `spec/MAPPING.md` §4) correctly find **zero**
edges, which would make for an anticlimactic demo. So this demo uses two data
sources for two different things:

- **[`fixtures/jaffle_shop_tables/`](fixtures/jaffle_shop_tables/)** — a small,
  hand-authored OKF bundle documenting a few of jaffle-shop's *own* tables
  (built from the real `ref()`/`source()` calls in jaffle-shop's model SQL —
  see the bundle's `index.md`). This is what `okf-bridge link` connects to the
  cloned repo, and what makes `graphify path` find a real path.
- **[GA4](../tests/fixtures/okf_official/ga4/)** (vendored, already in this
  repo's test fixtures) — imported (`okf-bridge import`) and merged in
  alongside, to demonstrate that a bridge-imported *foreign, unrelated*
  bundle merges cleanly into the same graph without breaking anything. It
  isn't expected to gain any linker edges to jaffle-shop, and that's correct
  behavior, not a gap.

## Run it

```bash
cd demo
make demo
```

Requires: network (clones jaffle-shop), `graphify` on `PATH` (`uv tool install
graphifyy`), and an LLM backend configured for graphify's own semantic
extraction pass (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, ... —
see `graphify extract --help`). AST-only code extraction works without one;
graphify's community *naming* step wants a backend.

`make demo` (see [`Makefile`](Makefile)) does, in order:

1. `graphify clone https://github.com/dbt-labs/jaffle-shop` — clone the dbt project.
2. `graphify .` inside the clone — build its code graph.
3. `okf-bridge import tests/fixtures/okf_official/ga4` — GA4 → a mergeable graph.json.
4. `okf-bridge link <jaffle-shop graph> demo/fixtures/jaffle_shop_tables --repo-root <jaffle-shop clone>`
   — infer `reads_from`/`writes_to` edges from the real `{{ ref(...) }}` calls
   in jaffle-shop's `.sql` files (invisible to `graph.json` itself per
   `spec/MAPPING.md` §1 surprise 1 — the linker reads them from disk).
5. `graphify merge-graphs <code> <ga4> <linked>` — one graph.
6. `graphify path "stg_orders.sql" "customers"` — traverses
   `stg_orders.sql` → (dbt ref, `reads_from`) → the `orders` table concept →
   (dbt ref) → the `customers` table concept, entirely through edges that
   didn't exist in either source system on its own.
7. `graphify explain "customers"` — shows the merged node's neighbors
   spanning both the dbt lineage and (harmlessly) the unrelated GA4 import.

`make clean` removes `.demo-out/` (the clone + generated graphs; nothing here
is committed to the repo).

## MCP

Once you have `merged.json`, see [`mcp.md`](mcp.md) for exposing it to an
agent over `python -m graphify.serve --graph merged.json`.
