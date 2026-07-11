---
name: okf-bridge
description: "Use when the user wants to export a graphify code knowledge graph to Google's Open Knowledge Format (OKF), import an OKF/Knowledge-Catalog bundle into a graphify graph, link code to data concepts (dbt refs, SQL literals, table names), or check an OKF bundle for spec conformance. Bridges Graphify's graph.json and OKF markdown+YAML bundles so one connected graph can span application code and warehouse tables."
---

# /okf-bridge

Bridge between [Graphify](https://github.com/Graphify-Labs/graphify) code knowledge graphs
(`graph.json`) and Google's [Open Knowledge Format v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
(vendor-neutral markdown + YAML knowledge bundles). Four commands: `validate`, `export`,
`import`, `link`.

## Usage

```
okf-bridge validate <bundle-dir>                            # OKF §9 conformance check + warnings
okf-bridge validate <bundle-dir> --strict                    # promote warnings to errors

okf-bridge export <graph.json> -o <bundle-dir>               # graphify graph -> OKF bundle
okf-bridge import <bundle-dir> -o <graph.json>                # OKF bundle -> mergeable graphify graph

okf-bridge link <graph.json> <bundle-dir> -o <out.json>       # infer code<->data edges
okf-bridge link <graph.json> <bundle-dir> -o <out.json> --repo-root .   # scan .sql files graph.json has no nodes for

okf-bridge install-skill                                      # install this skill for the current user
okf-bridge install-skill --project                             # install into the current repo's .claude/ instead
```

## When to reach for each command

- **`validate`** — the user shares or points at an OKF bundle (an existing `Google-Cloud-Platform/knowledge-catalog`-style directory of markdown + YAML frontmatter, or one this tool wrote) and wants to know if it's spec-conformant. Non-strict mode never fails on soft issues (unknown types/keys, broken links) — only missing/empty frontmatter `type` is a hard error.
- **`export`** — the user has run `graphify` over a codebase (`graphify-out/graph.json`) and wants a portable, human-browsable knowledge bundle: markdown per node, typed `links:` frontmatter *and* a `## Connections` section per edge, generated `index.md`/`overview.md`. Output always passes `okf-bridge validate --strict` with zero warnings.
- **`import`** — the user has an OKF bundle (official Google sample, or a vendor/team-authored one) and wants it as a graphify-mergeable `graph.json`, e.g. to run `graphify merge-graphs code.json data.json` and then query/explain/path across both.
- **`link`** — the user has *both* a code graph and a data bundle already and wants the cross-silo edges that neither side captures on its own: dbt `ref()`/`source()` calls, `FROM`/`JOIN`/`INSERT INTO` table literals in SQL (and Python string literals), and unambiguous exact-name matches. Every inferred edge is `confidence: INFERRED` with a `linker_signal` provenance tag — ambiguous matches are dropped with a warning, never guessed. `--repo-root` matters here: graphify's structural pass is Python-only, so `.sql` files are invisible to `graph.json` and must be scanned from disk.

## Typical end-to-end flow

```
graphify .                                        # build the code graph (graphify-out/graph.json)
okf-bridge import path/to/data_bundle -o data.json
okf-bridge link graphify-out/graph.json path/to/data_bundle -o linked.json --repo-root .
graphify merge-graphs graphify-out/graph.json data.json --out merged.json
graphify merge-graphs merged.json linked.json --out merged.json
graphify path "orders.sql" "events_"              # now traverses code -> table
```

See `demo/README.md` in the `graphify-okf-bridge` repo for a full worked example
(dbt project + the vendored GA4 bundle), and `demo/mcp.md` for exposing the merged
graph over MCP (`python -m graphify.serve --graph merged.json`).

## Notes for the agent

- Read `okf-bridge --help` (or each subcommand's `--help`) if a flag isn't listed above — it is the source of truth.
- `export`/`import`/`link` are pure functions under the hood (`exporter.export`, `importer.import_bundle`, `linker.link`); the CLI is a thin wrapper. Prefer running the CLI commands over reading the library internals unless debugging.
- The mapping convention (node/edge → concept/link, confidence handling, linker signal priority) is normative in this repo's `spec/MAPPING.md` — cite it rather than guessing when asked *why* something maps a particular way.
