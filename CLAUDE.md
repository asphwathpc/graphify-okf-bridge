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

- Node → concept at `<node_type>/<slug>.md`; `graphify_node_id` stored in frontmatter for lossless round-trip.
- Edge → *both* a markdown link in the `## Connections` body section (so untyped OKF consumers see it) *and* a typed entry in the `links:` frontmatter extension: `{target, rel, confidence}`.
- Import: typed `links:` entries keep their rel/confidence; plain body links become `references`/`EXTRACTED` edges.
- Round-trip invariant: `import(export(g))` preserves node count, edge count, relations, confidences.

## Current status

Track phase progress here (update at the end of each session):

- [x] Phase 0 — bootstrap, fixtures, graph.json schema discovery
- [ ] Phase 1 — OKF model/reader/writer/validator
- [ ] Phase 2 — exporter
- [ ] Phase 3 — importer + round-trip
- [ ] Phase 4 — linker
- [ ] Phase 5 — skill packaging, demo, PyPI release
