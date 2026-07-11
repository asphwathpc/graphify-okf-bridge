# Serving a merged graph over MCP

`graphify-okf-bridge` does not ship its own MCP server for v1 — once a graph carries
both code and data nodes (`okf-bridge import` + `okf-bridge link` +
`graphify merge-graphs`, see [`demo/README.md`](README.md)), it's an ordinary
`graph.json`, and graphify's own MCP server (`graphify.serve`, part of the
`graphifyy` PyPI package) already exposes it to any MCP-capable agent.

## Run it

```bash
python -m graphify.serve --graph merged.json
# or, positionally:
python -m graphify.serve merged.json
```

Defaults to stdio transport (what Claude Code / Claude Desktop expect from a local
MCP server). Add `--transport http --host 127.0.0.1 --port 8080` to serve over
Streamable HTTP instead (useful for a shared/remote deployment; add `--api-key`,
or set `GRAPHIFY_API_KEY`, to require auth).

## What it exposes

Tools (unaffected by the bridge — they operate on whatever `graph.json` shape they're
given, and a merged code+data graph is still `directed`/`multigraph`/`nodes`/`links`
per graphify's own schema, see `spec/MAPPING.md` §1):

- `query_graph` — BFS/DFS traversal over a natural-language question
- `get_node` / `get_neighbors` / `get_community` — point lookups
- `god_nodes` / `graph_stats` — structural summaries
- `shortest_path` — e.g. `"orders.sql"` → `"events_"` across the merged graph,
  traversing the `reads_from`/`writes_to` edges `okf-bridge link` added
- `list_prs` / `get_pr_impact` / `triage_prs` — graphify's PR-impact tooling, works
  unchanged since it only depends on node/edge shape, not provenance

Resources: `graphify://report`, `graphify://stats`, `graphify://god-nodes`,
`graphify://surprises`, `graphify://questions`.

## Registering with Claude Code

Point an MCP client config at the command above, e.g. in `.mcp.json`:

```json
{
  "mcpServers": {
    "graphify": {
      "command": "python",
      "args": ["-m", "graphify.serve", "--graph", "merged.json"]
    }
  }
}
```

No `okf-bridge`-specific server is needed — the bridge's job ends at producing a
`graph.json` that graphify's own tooling (MCP server, `path`, `explain`, `query`)
already understands.
