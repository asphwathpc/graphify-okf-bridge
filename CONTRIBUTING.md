# Contributing to graphify-okf-bridge

Thanks for considering a contribution. This project bridges [Graphify](https://github.com/Graphify-Labs/graphify) code graphs and Google's [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) — small in scope, but the mapping rules have sharp edges, so please read this before sending a PR.

## Ground rules

1. **`spec/MAPPING.md` is normative.** If your change makes the code and MAPPING.md disagree, update MAPPING.md first — with a rationale — then the code. PRs that silently diverge from it will be asked to update the doc.
2. **TDD.** Write the failing test before the fix/feature. A bug fix without a regression test is incomplete and won't be merged.
3. **Ground truth over assumption.** Don't guess at `graph.json` or OKF bundle shape — check `tests/fixtures/tiny_graph.json` (real graphify output) and `tests/fixtures/okf_official/*` (real Google-produced bundles). If our reader rejects an official bundle, the reader is wrong, not the fixture.
4. **Determinism.** Exports must be byte-identical across runs — sort all iteration, no timestamps except the frontmatter `timestamp` field derived from input data, stable slug generation.
5. **Permissive in, strict out.** Reading foreign bundles never raises on soft violations (collect warnings instead). Bundles this tool writes must pass `okf-bridge validate --strict` with zero warnings.
6. **Precision over recall in the linker.** An ambiguous match should produce no edge plus a warning, never a guess. Every inferred edge needs a `confidence: INFERRED` and a `linker_signal` provenance key.

## Getting set up

```bash
uv sync                                  # install the dev environment
uv run pytest -m "not integration"      # fast suite — must stay under 10s
uv run ruff check . && uv run mypy src/  # lint + types — required before any PR
```

Integration tests exercise the real `graphify` CLI and need it installed separately:

```bash
uv tool install graphifyy
uv run pytest -m integration
```

## Before opening a PR

- [ ] Fast suite green, coverage didn't drop below 85%.
- [ ] `ruff check .` and `mypy src/` clean.
- [ ] If you touched a mapping rule (export/import/link behavior), `spec/MAPPING.md` reflects it.
- [ ] New behavior has a test under `tests/unit/`, `tests/roundtrip/`, or `tests/integration/` as appropriate — see the test-strategy table in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

Keep PRs scoped to one change. `export()`, `import_bundle()`, and `link()` are pure functions over models — `cli.py` should stay a thin wrapper, so new logic belongs in the pure layer with unit tests, not bolted onto the CLI.

## Finding something to work on

Look for issues tagged [`good first issue`](https://github.com/Graphify-Labs/graphify-okf-bridge/labels/good%20first%20issue) on GitHub. If nothing's tagged yet, open an issue describing what you'd like to tackle before starting — this keeps mapping-rule changes aligned with MAPPING.md up front rather than in review.

## Reporting bugs

Include the `graph.json` or OKF bundle that triggered the issue (redacted if needed) — most bugs here are shape-of-data bugs, and a repro fixture is worth more than a description.
