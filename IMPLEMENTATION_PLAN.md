# graphify-okf-bridge — Implementation Plan

Step-by-step plan to build, test, and ship the bridge as a new open-source repo. Designed so each phase is a self-contained unit of work you can hand to Claude Code with the prompt included at the end of each phase. Work strictly in phase order; every phase ends with green tests and a commit.

**Grounding facts (verified against upstream, July 2026):**

- OKF v0.1 conformance (SPEC.md §9): every non-reserved `.md` file must have parseable YAML frontmatter with a non-empty `type` field; `index.md`/`log.md` are reserved and follow §6/§7. Everything else is soft guidance. Consumers must tolerate unknown types, unknown keys, and broken links.
- OKF links are untyped markdown links; relationship meaning lives in prose (§5.3). Bundle-relative links start with `/` and are recommended.
- Bundles may declare `okf_version: "0.1"` in root `index.md` frontmatter (the only index.md allowed frontmatter).
- Graphify: PyPI package `graphifyy`, output is `graphify-out/graph.json` (+ `graph.html`, `GRAPH_REPORT.md`), edges carry `EXTRACTED`/`INFERRED` confidence tags and typed relations (`calls`, `imports`, `inherits`, `uses`, `method`, `references`, …), has `merge-graphs a.json b.json`, and an MCP server (`python -m graphify.serve --graph …`).
- Official OKF sample bundles to use as fixtures: `bundles/ga4/`, `bundles/stackoverflow/`, `bundles/crypto_bitcoin/` in `GoogleCloudPlatform/knowledge-catalog`.

---

## Repo overview

**Name:** `graphify-okf-bridge` · **License:** Apache-2.0 · **Language:** Python ≥3.11 · **Tooling:** `uv`, `ruff`, `pytest`, `mypy`, GitHub Actions

```
graphify-okf-bridge/
├── pyproject.toml               # package: graphify_okf_bridge, CLI: okf-bridge
├── LICENSE                      # Apache-2.0
├── README.md
├── CLAUDE.md                    # instructions for Claude Code (provided separately)
├── CONTRIBUTING.md
├── spec/
│   └── MAPPING.md               # the Graphify↔OKF mapping convention (normative for this repo)
├── src/graphify_okf_bridge/
│   ├── __init__.py
│   ├── cli.py                   # okf-bridge export|import|link|validate|demo
│   ├── okf/
│   │   ├── model.py             # Bundle, Concept, Link dataclasses
│   │   ├── reader.py            # bundle dir -> model (permissive, per spec §9)
│   │   ├── writer.py            # model -> bundle dir (index.md, log.md generation)
│   │   └── validator.py         # conformance checker (spec §9) + warnings for soft guidance
│   ├── graphify_io/
│   │   ├── schema.py            # graph.json pydantic models (from Phase 0 discovery)
│   │   └── loader.py            # load/save graph.json
│   ├── exporter.py              # graph.json -> OKF bundle
│   ├── importer.py              # OKF bundle -> graph.json (mergeable)
│   ├── linker.py                # cross-silo edge inference (dbt refs, SQL literals)
│   └── skill/                   # Claude Code skill packaging (Phase 5)
│       └── SKILL.md
├── tests/
│   ├── unit/
│   ├── roundtrip/
│   ├── integration/
│   └── fixtures/
│       ├── tiny_repo/           # ~10-file toy codebase for real graphify runs
│       ├── tiny_graph.json      # committed graphify output of tiny_repo
│       ├── okf_minimal/         # hand-written minimal bundle (spec Appendix A clone)
│       └── okf_official/        # vendored GA4 / stackoverflow / crypto_bitcoin bundles
├── demo/
│   ├── README.md                # dbt + GA4 walkthrough
│   └── Makefile
└── .github/workflows/ci.yml
```

**CLI surface (final):**

```
okf-bridge validate <bundle-dir>                     # OKF §9 conformance + warnings
okf-bridge export  <graph.json> -o <bundle-dir>      # graphify -> OKF
okf-bridge import  <bundle-dir> -o <graph.json>      # OKF -> graphify (merge-ready)
okf-bridge link    <graph.json> <bundle-dir> -o out.json   # add cross-silo INFERRED edges
okf-bridge demo                                      # runs the dbt+GA4 end-to-end demo
```

---

## Phase 0 — Bootstrap & schema discovery (Day 1–2)

The only phase with manual/exploratory work. Everything later depends on knowing `graph.json`'s real shape.

**Steps**

1. `git init graphify-okf-bridge`; create `pyproject.toml` (hatchling or uv build backend, `[project.scripts] okf-bridge = "graphify_okf_bridge.cli:main"`), LICENSE, README stub, `.gitignore`, ruff + mypy + pytest config.
2. CI: `.github/workflows/ci.yml` — matrix py3.11/3.12/3.13, jobs: `ruff check`, `mypy`, `pytest --cov` (fail under 85%).
3. Create `tests/fixtures/tiny_repo/`: a deliberately cross-linked toy project — 2 Python modules with imports/inheritance/calls, 1 SQL file referencing a table name, 1 dbt-style model with `ref()`, 1 markdown doc, 1 `# WHY:` comment. Small enough to eyeball, rich enough to exercise every edge type.
4. **Schema discovery:** install graphify (`uv tool install graphifyy`), run `/graphify tests/fixtures/tiny_repo` (or CLI equivalent), commit the resulting `graph.json` as `tests/fixtures/tiny_graph.json`. Read it and write `src/graphify_okf_bridge/graphify_io/schema.py` as pydantic models matching the observed structure exactly (nodes: id/label/type/source/community/…; edges: source/target/relation/confidence). Document any surprises in `spec/MAPPING.md` §"graph.json observed schema".
5. Vendor fixtures: copy the three official OKF bundles into `tests/fixtures/okf_official/` (they're Apache-2.0; keep their LICENSE notice). Hand-write `okf_minimal/` mirroring SPEC.md Appendix A.
6. First test: `test_fixtures_exist_and_parse` — graph.json loads through the pydantic models with zero validation errors.

**Definition of done:** CI green on a repo containing only fixtures, schema models, and one passing test. Tag `v0.0.1`.

> **Claude prompt (Phase 0):** "Bootstrap a Python project per Phase 0 of IMPLEMENTATION_PLAN.md. I've placed graphify's real output at tests/fixtures/tiny_graph.json — read it and derive exact pydantic models in graphify_io/schema.py. Don't guess fields; model only what's in the file, and make unknown-key handling permissive (`model_config = ConfigDict(extra='allow')`)."

---

## Phase 1 — OKF core: model, reader, writer, validator (Day 3–5)

Pure OKF implementation, no Graphify involvement. This module should be extractable later as its own `okf-python` library — keep it dependency-light (pyyaml + python-frontmatter or hand-rolled parsing, plus a markdown link extractor).

**Steps**

1. `okf/model.py`: `Concept` (concept_id, type, title, description, resource, tags, timestamp, extra_frontmatter: dict, body: str, links: list[Link]), `Link` (target_concept_id, anchor_text, bundle_relative: bool), `Bundle` (root, concepts, indexes, logs, okf_version).
2. `okf/reader.py`: walk a directory; parse frontmatter + body for every non-reserved `.md`; extract links (both `/absolute` and `./relative`, resolving relative against the file's directory); **never raise** on soft violations — collect `Warning` records instead (spec §9 permissive consumption). Parse the optional `links:` frontmatter extension (see MAPPING.md) when present.
3. `okf/writer.py`: serialize a `Bundle` to disk. Responsibilities: stable slug generation (lowercase, `-`, collision suffixing), frontmatter emission with required `type` first, auto-generated `index.md` per directory (§6 format: sections, `* [Title](url) - description`), root `index.md` with `okf_version: "0.1"` frontmatter, optional `log.md` seeding (§7: `## YYYY-MM-DD` + `**Creation**:` entries), **deterministic output** (sorted iteration everywhere — byte-identical re-runs are a test invariant).
4. `okf/validator.py`: hard checks (§9: parseable frontmatter, non-empty `type`, reserved-file structure) → errors; soft checks (missing description, broken links, missing index) → warnings. Wire to `okf-bridge validate` with `--strict` to promote warnings.

**Test plan for this phase** (details in §Test strategy): unit tests per parser edge case; the three official bundles must load with **zero errors**; writer determinism test; reader(writer(bundle)) == bundle equivalence test.

**Definition of done:** `okf-bridge validate tests/fixtures/okf_official/ga4` exits 0; all Phase 1 tests green.

> **Claude prompt (Phase 1):** "Implement Phase 1 of IMPLEMENTATION_PLAN.md (okf/ package). TDD: write the failing tests listed in the Test strategy §Phase-1 rows first, then implement until green. The official bundles in tests/fixtures/okf_official are ground truth — if your reader rejects anything in them, your reader is wrong, not the bundle."

---

## Phase 2 — Exporter: graph.json → OKF bundle (Day 6–9)

**Mapping rules (write these into `spec/MAPPING.md` §Export before coding):**

| Graphify | OKF |
|---|---|
| node | one concept doc at `<node_type>/<slug>.md` (e.g. `classes/api-router.md`, `docs/adr-0001.md`) |
| node type | frontmatter `type` (namespaced: `Code Class`, `Code Function`, `Doc`, `Rationale`, …) |
| node source (`file L123`) | frontmatter `resource: file://<relpath>#L<line>` |
| community id + label | frontmatter `tags: [community:<label>]` |
| docstring / `# WHY:` / `# NOTE:` rationale | markdown body |
| edge | markdown link in body under `## Connections` **plus** typed entry in frontmatter `links:` block |
| edge relation + confidence | `links: [{target, rel, confidence}]` frontmatter extension (spec §4.1 permits arbitrary keys) |
| whole graph | bundle with root `index.md` (`okf_version: "0.1"`), per-directory indexes, `log.md` with a Creation entry |
| god nodes / report highlights | `overview.md` concept at bundle root (`type: Overview`) |

**Steps**

1. Write MAPPING.md §Export as the normative doc. Every rule above gets a MUST/SHOULD.
2. Implement `exporter.py`: graph model → `Bundle` model → `okf.writer`. Keep it a pure function `export(graph: Graph) -> Bundle` plus a thin CLI wrapper (testability).
3. Slug registry to guarantee node-id ↔ concept-id mapping is bijective; emit `graphify_node_id` as an extra frontmatter key so the importer can recover identity losslessly.
4. Body rendering: `## Connections` section with prose-ish lines (`- calls [`get_request_handler`](/functions/get-request-handler.md) *(extracted)*`) so untyped OKF consumers (viz.html, Obsidian) still see the relationships as normal links (§5.3).
5. CLI: `okf-bridge export tests/fixtures/tiny_graph.json -o /tmp/tiny_bundle`, then `okf-bridge validate /tmp/tiny_bundle` → 0 errors.
6. Manual check: generate viz.html for the exported bundle using the OKF repo's visualizer; confirm the graph renders. Screenshot into `demo/`.

**Definition of done:** tiny_graph exports to a conformant bundle; every node became a concept; every edge appears both as a markdown link and a `links:` entry; export is deterministic.

> **Claude prompt (Phase 2):** "Implement Phase 2 per IMPLEMENTATION_PLAN.md and spec/MAPPING.md §Export. Start from the failing tests in tests/unit/test_exporter.py and tests/roundtrip/. Export must be a pure function over the pydantic models; CLI is a wrapper. Determinism is a hard requirement — two runs must produce byte-identical trees."

---

## Phase 3 — Importer: OKF bundle → graph.json (Day 10–13)

**Mapping rules (MAPPING.md §Import):** concept → node (id = `graphify_node_id` if present, else `okf:<concept_id>`); frontmatter `type` → node type; `resource` → node source; typed `links:` entries → edges with their declared rel/confidence; plain body links without a `links:` entry → edges with relation `references`, confidence `EXTRACTED` (the link is explicit in the source document); tags/description/body → node metadata carried through for graph queries.

**Steps**

1. Write MAPPING.md §Import (normative), including the round-trip guarantee: `import(export(g))` preserves node count, edge count, relations, and confidences (titles/slugs may normalize).
2. Implement `importer.py` as pure function `import_bundle(bundle: Bundle) -> Graph`.
3. Output must be **mergeable by graphify itself**: verify `graphify merge-graphs tiny_graph.json imported_ga4.json` succeeds (integration test, requires graphify installed — mark `@pytest.mark.integration`).
4. CLI: `okf-bridge import tests/fixtures/okf_official/ga4 -o ga4_graph.json`.

**Definition of done:** all three official bundles import cleanly; round-trip property holds on tiny_graph; graphify's own `merge-graphs`, `explain`, and `path` commands work against an imported+merged graph.

> **Claude prompt (Phase 3):** "Implement Phase 3 per IMPLEMENTATION_PLAN.md and MAPPING.md §Import. The round-trip test in tests/roundtrip/test_lossless.py is the acceptance bar: import(export(tiny_graph)) must preserve nodes, edges, relations, confidences. Official bundles are import-only fixtures (no round-trip — they weren't produced by us)."

---

## Phase 4 — Linker: connect code to data (Day 14–18)

The differentiating feature. v1 is deliberately high-precision, low-recall.

**Signals (in priority order):**

1. **dbt**: `ref('model')` / `source('src','table')` in `.sql` files → edge `code_node --reads_from--> table_concept`.
2. **SQL literals**: `FROM`/`JOIN`/`INSERT INTO` table identifiers inside string literals in code (regex over node source text, backtick/qualified-name aware) → matched against OKF table concept titles + resource URIs.
3. **Exact-name fallback**: code identifier == table name (case-insensitive) → only when unambiguous (single candidate on both sides).

Every linker edge: relation `reads_from`/`writes_to`, confidence `INFERRED`, plus provenance metadata (`linker_signal: dbt_ref | sql_literal | name_match`) so users can audit and filter.

**Steps**

1. MAPPING.md §Linking: signals, tie-breaking, ambiguity policy (ambiguous → no edge, log a warning; never guess).
2. Implement `linker.py`: `link(code_graph, data_bundle) -> list[Edge]` + CLI `okf-bridge link`.
3. Extend `tiny_repo` fixture with known-answer cases: 2 dbt refs, 2 SQL literals, 1 exact-name match, **and** 3 trap cases that must NOT link (ambiguous name, commented-out SQL, partial-string match).
4. Precision harness: `tests/unit/test_linker.py` asserts exactly the expected edge set — no extras (false positives fail the suite).

**Definition of done:** on the fixture, linker produces exactly the 5 expected edges and none of the 3 traps; `graphify path` traverses code→table on the merged graph.

> **Claude prompt (Phase 4):** "Implement Phase 4 per IMPLEMENTATION_PLAN.md. The fixture encodes known answers including negative traps — the test asserts the exact edge set, so any false positive is a failure. When a match is ambiguous, emit no edge and a warning. Precision over recall throughout."

---

## Phase 5 — Packaging, plugin, demo, release (Day 19–24)

**5a. Claude Code skill/plugin.** Create `src/graphify_okf_bridge/skill/SKILL.md` so `/okf-bridge` works inside Claude Code (and any assistant graphify supports): frontmatter with name + trigger description ("use when the user wants to export a graphify graph to OKF, import an OKF/Knowledge-Catalog bundle, or link code to data concepts"), body documenting the four CLI commands with examples. Add `okf-bridge install-skill` that copies it into the user's skills directory (mirror how `graphify install` registers itself — read its implementation first). Optionally publish as a Claude Code plugin bundle (zip with `.skill` extension) attached to the GitHub release.

**5b. MCP path.** No new server needed for v1: document that `python -m graphify.serve --graph merged.json` exposes the merged graph over MCP. Add `demo/mcp.md` showing it.

**5c. Killer demo.** `demo/`: clone a small public dbt project (e.g. jaffle-shop) + the vendored GA4 bundle → `graphify` the dbt repo → `okf-bridge import` + `link` + `graphify merge-graphs` → run `graphify path "orders.sql" "events_"` → record terminal GIF (vhs or asciinema) for the README hero.

**5d. Release.**

1. README rewrite: hero GIF, 30-second quickstart, mapping-convention summary, "relationship to upstream" section.
2. CONTRIBUTING.md + the three good-first-issues filed on GitHub.
3. Publish `graphify-okf-bridge` to PyPI via CI on tag (`uv publish`, trusted publishing). Tag `v0.1.0`.
4. Upstream outreach: issue on `GoogleCloudPlatform/knowledge-catalog` proposing the `links:` typed-edge frontmatter convention (link MAPPING.md); issue/PR on `Graphify-Labs/graphify` offering the exporter as a plugin.

**Definition of done:** `uv tool install graphify-okf-bridge && okf-bridge demo` works on a clean machine; skill loads in Claude Code; v0.1.0 on PyPI; two upstream issues filed.

> **Claude prompt (Phase 5):** "Execute Phase 5 per IMPLEMENTATION_PLAN.md. First read how `graphify install` registers its skill and mirror that mechanism for install-skill. Then build the demo Makefile end-to-end and only record the GIF once `make demo` passes from a clean checkout."

---

## Test strategy

**Layers**

| Layer | Location | Runs | What it proves |
|---|---|---|---|
| Unit | `tests/unit/` | every commit, no network, <10s | parsers, slugger, mapping rules, linker signals — one test file per module, table-driven cases |
| Round-trip | `tests/roundtrip/` | every commit | `reader(writer(b)) == b` for bundles; `import(export(g)) ≅ g` for graphs (node/edge/relation/confidence-preserving); determinism (two exports byte-identical) |
| Golden fixtures | `tests/unit/test_official_bundles.py` | every commit | the 3 vendored official bundles parse with 0 errors; snapshot the parsed concept counts so upstream-format drift is caught when fixtures are re-vendored |
| Integration | `tests/integration/` (`-m integration`) | CI nightly + pre-release | real `graphifyy` installed: build tiny_repo graph fresh, export, validate, import, `graphify merge-graphs` / `explain` / `path` all succeed |
| Conformance | `okf-bridge validate` self-test | every commit | every bundle this tool ever writes passes its own §9 validator with 0 errors and 0 warnings |

**Per-phase acceptance tests (write these first — they are the TDD backlog):**

- *P1:* frontmatter edge cases (missing `type` → error; unknown keys preserved; empty file → error; body-only file → error); link extraction (absolute, relative, anchors, broken targets tolerated); index.md is not treated as a concept; `okf_version` read from root index; official-bundle zero-error load; writer determinism.
- *P2:* every node maps to exactly one concept; bijective slug registry (collision case included); edge appears in both body and `links:`; exported bundle passes strict validation; `graphify_node_id` present on every concept.
- *P3:* round-trip preservation counts; plain-link-without-`links:`-entry becomes `references/EXTRACTED` edge; import of bundle with unknown types succeeds (permissive); merge with real graphify (integration).
- *P4:* exact expected edge set on fixture (5 positives, 3 negative traps); provenance metadata present on every linker edge; ambiguity produces warning + no edge.
- *P5:* `make demo` exits 0 from clean checkout (integration); skill file passes Claude Code skill validation; `pip install` from built wheel exposes working `okf-bridge` entrypoint.

**Policies:** coverage ≥85% enforced in CI (exporter/importer/linker target ≥95%); no test may touch the network (fixtures are vendored); integration tests are the only ones allowed to invoke graphify; every bug fix lands with a regression test; property-based tests (hypothesis) for the slugger and frontmatter round-trip.

---

## Working with Claude — execution protocol

1. Create the repo, drop in this file and `CLAUDE.md`, complete Phase 0 steps 3–4 yourself (running graphify locally to capture `tiny_graph.json` — this is the one step Claude can't do for you if graphify needs your assistant runtime), then hand Claude the Phase 0 prompt.
2. One phase per session. Start each session with: *"Read CLAUDE.md and IMPLEMENTATION_PLAN.md. We are on Phase N. Confirm the DoD, then write the phase's failing tests, then implement."*
3. Never let a phase end without: tests green, `ruff` + `mypy` clean, MAPPING.md updated if any mapping decision changed, and a commit with message `phase-N: <summary>`.
4. If Claude discovers the real `graph.json` schema differs from an assumption in this plan, the rule is: **update MAPPING.md first, then code** — the mapping doc stays normative.

## Milestones

| Tag | Contents | Target |
|---|---|---|
| v0.0.1 | Phase 0: scaffold + fixtures + CI | Day 2 |
| v0.0.2 | Phase 1: OKF core + validator | Day 5 |
| v0.0.3 | Phase 2: exporter | Day 9 |
| v0.0.4 | Phase 3: importer + round-trip | Day 13 |
| v0.0.5 | Phase 4: linker | Day 18 |
| **v0.1.0** | Phase 5: skill, demo, PyPI, upstream issues | Day 24 |
