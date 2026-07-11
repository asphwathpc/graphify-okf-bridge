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
- [x] Phase 5 — skill packaging, demo, PyPI release
  - [x] 5a — `skill/SKILL.md` + `okf-bridge install-skill` (mirrors `graphify install`)
  - [x] 5b — MCP path documented (`demo/mcp.md`; no new server needed, graphify's own `graphify.serve` covers it)
  - [x] 5c — demo scaffolded and **executed end-to-end** against real `dbt-labs/jaffle-shop` output (local ollama/qwen2.5:7b-instruct backend, zero API cost) + GA4 imported alongside. First real run surfaced two spec gaps, now fixed and documented in MAPPING.md: L6 (`repo_root`-relative `source_file` resolution) and L7a (a `.sql` file reuses an existing same-stem `file_type: code` node instead of always minting a disconnected synthetic `sql:<path>` node — see `_existing_node_for_sql_stem` in `linker.py`, regression tests in `test_linker.py`). Recording `demo/hero.gif` (2026-07-12, via `vhs`) surfaced a demo-narrative bug: the originally-documented example query, `graphify path "stg_orders.sql" "customers"`, takes a spurious 3-hop detour through an incidental `setup.py`-references node because `orders`→`customers` isn't real dbt lineage (it's the reverse — `customers` depends on `orders`); fixed by repointing the demo (`demo/Makefile`, `demo/README.md`) at the matching pair `"stg_orders.sql" "orders"`, a clean 2-hop path ending in the linker's own `reads_from [INFERRED]` edge. Not a bridge/linker bug — graphify's own `graphify path` does undirected shortest-path, so a mismatched query pair will always find *a* path, just not an illustrative one.
  - [x] 5d — release: README quickstart done, CONTRIBUTING.md written. 3 good-first-issues filed on GitHub (asphwathpc/graphify-okf-bridge#4, #5, #6 — validator gaps for `typed_links`/`okf_version`, and silent `export`/`import` CLI output). Fixed a stale `Graphify-Labs/graphify-okf-bridge` link in CONTRIBUTING.md (actual org is `asphwathpc`) while filing. Version bumped to `0.1.0`, `v0.1.0` tag pushed (points at fcf7e60), `dist/` built and validated (ruff/mypy/pytest all green pre-build). The two upstream issues are filed: knowledge-catalog `links:` proposal (GoogleCloudPlatform/knowledge-catalog#183) and Graphify exporter-plugin offer (Graphify-Labs/graphify#1801). `graphify-okf-bridge` 0.1.0 **published to PyPI** (2026-07-12, user supplied `UV_PUBLISH_TOKEN`; confirmed live via `pypi.org/pypi/graphify-okf-bridge/0.1.0/json` → 200). Hero GIF recorded (`demo/hero.gif`, embedded in `demo/README.md`). Phase 5 complete.
  - Post-release cleanup (2026-07-12): repo had 6 open issues, not 3 — an earlier, less-detailed batch (#1–#3, filed 18:42–18:43) predated the "3 good-first-issues" batch referenced above (#4–#6, filed 18:49–18:50). Closed #2 (stale — hero GIF it asked for was already recorded/embedded) and #1 (duplicate of #6, which covers the same export/import-summary gap with fuller acceptance criteria). Remaining open: #3 (linker inline-comment stripping), #4 (validate: typed `links:` broken-target check), #5 (validate: missing `okf_version` warning), #6 (export/import CLI success summaries).
  - Fixed #6 (2026-07-12): `export` now echoes `"{N} concept(s) written to {bundle_dir}"` and `import` echoes `"{N} node(s), {M} edge(s) written to {graph_json}"` after their respective writes, matching `link`'s existing summary-line convention. Pure `cli.py` echo, no logic in `export()`/`import_bundle()` — ground rule 7. Tests added to `test_cli_export.py`/`test_cli_import.py` first (TDD), confirmed failing, then implemented.
  - Fixed #4 (2026-07-12): `validate()` in `okf/validator.py` now also checks `concept.typed_links` (the `links:` frontmatter extension) for dangling targets, sibling to the existing `concept.links` (body link) check — previously a bundle with a broken `links:` entry but no matching body link produced zero warnings. Regression test uses an in-memory `Bundle`/`Concept`/`TypedLink` fixture (no new bundle fixture files needed), per the issue's acceptance criteria. No MAPPING.md change — closes a gap in existing validator behavior, not a new mapping decision. Remaining open good-first-issues: #3 (linker inline-comment stripping), #5 (validate: missing `okf_version` warning).
  - Fixed #5 (2026-07-12): `validate()` now warns (`index.md`, "missing 'okf_version' in root index.md frontmatter") when `bundle.okf_version is None`. Confirmed via TDD (test added and shown failing before the fix). No regression risk to ground rule 5: the exporter always sets `okf_version="0.1"` (`exporter.py:40`), so bundles this tool writes never trigger the new warning — running `okf-bridge validate --strict` against the real `okf_official/ga4` fixture confirms the gap is real: Google's own GA4 bundle omits `okf_version` and now surfaces exactly this warning. No MAPPING.md change. Remaining open good-first-issue: #3 (linker inline-comment stripping).

## Implementation plan status

All phases in IMPLEMENTATION_PLAN.md (0 through 5d) are complete — v0.1.0 is on PyPI, the demo is recorded, upstream issues are filed. There is no Phase 6 defined. Further work here is either: (a) picking up the remaining open good-first-issue (#3), (b) responding to community/upstream engagement (PyPI downloads, GitHub issues/PRs, the two upstream issues), or (c) a genuinely new phase the user defines. Don't invent new phases unprompted — ask.
