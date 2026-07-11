# CLAUDE.md — graphify-okf-bridge

Instructions for Claude Code working in this repository. Read IMPLEMENTATION_PLAN.md before any work; work proceeds strictly phase by phase.

## What this project is

A bridge between [Graphify](https://github.com/Graphify-Labs/graphify) (local code knowledge graphs, `graph.json`) and Google's [Open Knowledge Format v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) (vendor-neutral knowledge bundles: markdown + YAML frontmatter). Four capabilities: `export` (graph.json → OKF bundle), `import` (OKF bundle → mergeable graph.json), `link` (infer code↔data edges), `validate` (OKF §9 conformance).

## Ground rules

1. **spec/MAPPING.md is normative.** If implementation and MAPPING.md disagree, update MAPPING.md first (with rationale), then the code. Never silently diverge.
2. **TDD, always.** Each phase's acceptance tests (IMPLEMENTATION_PLAN.md §Test strategy) are written and failing before implementation starts. A bug fix without a regression test is incomplete.
3. **Ground truth over assumption.**
   - `tests/fixtures/tiny_graph.json` is real graphify output — model what's in it, don't guess fields.
   - `tests/fixtures/okf_official/*` are real Google-produced bundles — if our reader rejects them, our reader is wrong.
   - The OKF spec is vendored knowledge: conformance = parseable frontmatter + non-empty `type` on every non-reserved `.md`; everything else is soft. Consumers must tolerate unknown types, unknown keys, broken links (§9).
4. **Determinism.** Exports must be byte-identical across runs: sort all iteration, no timestamps except the frontmatter `timestamp` field derived from input data, stable slug generation.
5. **Permissive in, strict out.** Reading foreign bundles never raises on soft violations (collect warnings). Bundles *we* write must pass `okf-bridge validate --strict` with zero warnings.
6. **Precision over recall in the linker.** Ambiguous match → no edge + warning. Every inferred edge carries `confidence: INFERRED` and a `linker_signal` provenance key.
7. **Pure functions, thin CLI.** `export()`, `import_bundle()`, `link()` operate on models and are unit-testable; `cli.py` only parses args and does I/O.
8. **No network in tests.** All fixtures are vendored. Only `-m integration` tests may invoke the installed `graphify` binary.

## Commands

```bash
uv sync                                  # install dev env
uv run pytest -m "not integration"      # fast suite (must stay <10s)
uv run pytest -m integration             # requires: uv tool install graphifyy
uv run ruff check . && uv run mypy src/  # lint + types — required before any commit
uv run okf-bridge validate tests/fixtures/okf_official/ga4   # smoke test
```

## Definition of done (every phase)

- Phase's acceptance tests green; full fast suite green; coverage ≥85%.
- `ruff` and `mypy` clean.
- MAPPING.md updated if any mapping decision was made or changed.
- Commit message: `phase-N: <summary>`.

## Key mapping decisions (summary — MAPPING.md has the normative text)

- Node → concept at `<file_type>/<slug>.md` (`file_type` used verbatim: code/document/paper/image/rationale/concept — graph.json has no finer AST-level type); `graphify_node_id` stored in frontmatter for lossless round-trip.
- Edge → *both* a markdown link in the `## Connections` body section (so untyped OKF consumers see it) *and* a typed entry in the `links:` frontmatter extension: `{target, rel, confidence}`.
- Import: typed `links:` entries keep their rel/confidence; plain body links become `references`/`EXTRACTED` edges.
- Round-trip invariant: `import(export(g))` preserves node count, edge count, relations, confidences.
- Linker: signals in priority order dbt `ref()`/`source()` → SQL literal (`FROM`/`JOIN`/`INSERT INTO`) → exact-name fallback; table concepts are OKF concepts under `tables/`; `.sql` files (invisible to graph.json) are scanned from disk via an explicit `--repo-root`; linker edge targets reuse the importer's `okf:<concept_id>` id so `link` output composes with `import` + `graphify merge-graphs`.

## Current status

Track phase progress here (update at the end of each session):

- [x] Phase 0 — bootstrap, fixtures, graph.json schema discovery
- [x] Phase 1 — OKF model/reader/writer/validator
- [x] Phase 2 — exporter
- [x] Phase 3 — importer + round-trip
- [x] Phase 4 — linker
- [ ] Phase 5 — skill packaging, demo, PyPI release
  - [x] 5a — `skill/SKILL.md` + `okf-bridge install-skill` (mirrors `graphify install`)
  - [x] 5b — MCP path documented (`demo/mcp.md`; no new server needed, graphify's own `graphify.serve` covers it)
  - [x] 5c — demo scaffolded and **executed end-to-end** against real `dbt-labs/jaffle-shop` output (local ollama/qwen2.5:7b-instruct backend, zero API cost) + GA4 imported alongside. `graphify path "stg_orders.sql" "customers"` succeeds, ending in the linker's own cross-silo `reads_from [INFERRED]` edge. First real run surfaced two spec gaps, now fixed and documented in MAPPING.md: L6 (`repo_root`-relative `source_file` resolution) and L7a (a `.sql` file reuses an existing same-stem `file_type: code` node instead of always minting a disconnected synthetic `sql:<path>` node — see `_existing_node_for_sql_stem` in `linker.py`, regression tests in `test_linker.py`). No hero GIF recorded yet.
  - [ ] 5d — release: README quickstart done, CONTRIBUTING.md written. Still need explicit user go-ahead before executing (irreversible/externally-visible actions): filing 3 good-first-issues on GitHub, PyPI publish + `v0.1.0` tag, and the two upstream issues (knowledge-catalog `links:` proposal, Graphify exporter-plugin offer).
