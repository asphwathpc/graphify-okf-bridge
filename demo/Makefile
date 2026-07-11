# demo/Makefile — dbt (jaffle-shop) + GA4 + a hand-authored jaffle-shop table
# catalog, walked end-to-end through graphify-okf-bridge. See README.md for
# the narrative and why two data bundles are involved.
#
# Requires (not part of the fast test suite — this is Phase 5c, run manually):
#   - network access (clones github.com/dbt-labs/jaffle-shop)
#   - `graphify` on PATH (`uv tool install graphifyy`)
#   - an LLM backend configured for graphify's semantic extraction pass
#     (any of GEMINI_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY / ...,
#     see `graphify extract --help`); AST-only nodes still work without one,
#     but community naming needs a backend.

PROJECT_ROOT := $(abspath ..)
GA4_BUNDLE   := $(PROJECT_ROOT)/tests/fixtures/okf_official/ga4
JAFFLE_TABLES_BUNDLE := $(abspath fixtures/jaffle_shop_tables)
OUT := $(abspath .demo-out)
JAFFLE_SHOP := $(OUT)/jaffle-shop

OKF_BRIDGE := uv run --project $(PROJECT_ROOT) okf-bridge

.PHONY: demo clean

demo: $(OUT)/merged.json
	@echo
	@echo "== graphify path: stg_orders.sql -> orders (via the linker's dbt-ref edges) =="
	graphify path "stg_orders.sql" "orders" --graph $(OUT)/merged.json
	@echo
	@echo "== graphify explain: orders (reads_from edges the linker inferred) =="
	graphify explain "orders" --graph $(OUT)/merged.json

$(JAFFLE_SHOP):
	mkdir -p $(OUT)
	graphify clone https://github.com/dbt-labs/jaffle-shop --out $(JAFFLE_SHOP)

$(JAFFLE_SHOP)/graphify-out/graph.json: $(JAFFLE_SHOP)
	cd $(JAFFLE_SHOP) && graphify . --backend ollama --model qwen2.5:7b-instruct --max-concurrency 1

$(OUT)/ga4_graph.json: $(GA4_BUNDLE)
	mkdir -p $(OUT)
	$(OKF_BRIDGE) import $(GA4_BUNDLE) -o $(OUT)/ga4_graph.json

$(OUT)/linked.json: $(JAFFLE_SHOP)/graphify-out/graph.json $(JAFFLE_TABLES_BUNDLE)
	$(OKF_BRIDGE) link $(JAFFLE_SHOP)/graphify-out/graph.json $(JAFFLE_TABLES_BUNDLE) \
		-o $(OUT)/linked.json --repo-root $(JAFFLE_SHOP)

# linked.json is already self-contained (MAPPING.md L13): okf-bridge link
# writes back the input graph's own nodes/edges *plus* synthetic nodes for
# both the new .sql source nodes and the okf: table concept targets. Merging
# the raw jaffle-shop code graph, or a separate `okf-bridge import` of the
# table bundle, in too would duplicate those nodes under a second repo tag --
# graphify merge-graphs namespaces node ids per source file, so it never
# unifies the same string id coming from two different input files.
$(OUT)/merged.json: $(OUT)/ga4_graph.json $(OUT)/linked.json
	graphify merge-graphs $(OUT)/ga4_graph.json $(OUT)/linked.json \
		--out $(OUT)/merged.json

clean:
	rm -rf $(OUT)
