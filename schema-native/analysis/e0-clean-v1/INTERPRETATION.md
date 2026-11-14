
# Completed-run interpretation

All 1,200 expected requests are saved with unique keys. The original 493 saved rows remain byte-for-byte unchanged after resumption. Engine errors, request errors and selected-raw-schema constraint violations: zero. Truncations remain model/runtime output failures and are included in accuracy, not excluded.

Primary pooled raw selection E2E is **85.5% free versus 70.5% constrained (-15 points)** in this pinned setup. The leading explanation is an order-related constraint effect, not a demonstrated inability to understand schema semantics. The [exact-engine key-order audit](KEY_ORDER.md) finds that 252/501 eligible free-correct calls are outside the grammar solely due to key order. Their constrained counterparts are 140 correct, 40 wrong and 72 truncated; all 249 calls already accepted in their original order remain correct. Fourteen wrapped free-correct outputs are excluded from this strict-contract diagnostic only. A controlled intervention is still required for a causal conclusion.

The constrained arms hit the 512-token limit on 95/600 requests, versus 1/600 free requests. All 95 constrained truncations remain legal grammar prefixes. Repeated whitespace is one escape path after the model diverges from the enforced serialization; compact JSON removes that path but can leave repetition inside strings. A second order-enforcing engine alone cannot isolate the order effect. The prospective [E0b design](../../E0B_PLAN.md) therefore includes an oracle-order diagnostic as well as a deployment baseline and an engine control. Changed conditions require a separate run ID; this completed run remains frozen. E1 and E2 stay gated.

Schema-valid wrong outputs may include undeclared look-alike keys permitted by additional properties. That is another serialization artifact; this report's historical `valid_wrong` count does not independently establish a learned-semantics deficit. The current reordering helper follows `properties` and `items`, not arbitrary combinator branches. The zero `other_rejection` count applies to the tested frozen outputs, not general schema support.

All 1,200 recorded pre-request checks show normal memory pressure, nominal thermal state and no active swap writes (the initial interval has no rate). These are sampled checks, not continuous temperature/GPU telemetry. Qwen was gracefully unloaded after completion; pressure remained normal. No other apps were closed.

The report uses the maximum across both corrected-run server lifetimes. Maximum RSS was 2980265984 bytes; those lifetimes also include readiness/preflight work. This is process RSS, not total unified-memory or Metal allocator peak.

Follow-up: [targeted whitespace diagnosis](../e0-whitespace-diagnostic-v1/REPORT.md), kept separate from this benchmark.

External review supplied by the user independently reproduced the row-level order audit using PyPI llguidance 1.0.1. That shares the version number, not the exact bundled binary. It supports merging this documented engineering milestone; it is not a model-inference replication or a GitHub approval submission. No general claim about constrained decoding or case for training follows from these results.
