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
	@echo "== graphify path: stg_orders.sql -> customers (via the linker's dbt-ref edges) =="
	graphify path "stg_orders.sql" "customers" --graph $(OUT)/merged.json
	@echo
	@echo "== graphify explain: customers (now carries both dbt lineage and the GA4 import) =="
	graphify explain "customers" --graph $(OUT)/merged.json

$(JAFFLE_SHOP):
	mkdir -p $(OUT)
	graphify clone https://github.com/dbt-labs/jaffle-shop --out $(JAFFLE_SHOP)

$(JAFFLE_SHOP)/graphify-out/graph.json: $(JAFFLE_SHOP)
	cd $(JAFFLE_SHOP) && graphify .

$(OUT)/ga4_graph.json: $(GA4_BUNDLE)
	$(OKF_BRIDGE) import $(GA4_BUNDLE) -o $(OUT)/ga4_graph.json

$(OUT)/linked.json: $(JAFFLE_SHOP)/graphify-out/graph.json $(JAFFLE_TABLES_BUNDLE)
	$(OKF_BRIDGE) link $(JAFFLE_SHOP)/graphify-out/graph.json $(JAFFLE_TABLES_BUNDLE) \
		-o $(OUT)/linked.json --repo-root $(JAFFLE_SHOP)

$(OUT)/merged.json: $(JAFFLE_SHOP)/graphify-out/graph.json $(OUT)/ga4_graph.json $(OUT)/linked.json
	graphify merge-graphs $(JAFFLE_SHOP)/graphify-out/graph.json $(OUT)/ga4_graph.json $(OUT)/linked.json \
		--out $(OUT)/merged.json

clean:
	rm -rf $(OUT)
