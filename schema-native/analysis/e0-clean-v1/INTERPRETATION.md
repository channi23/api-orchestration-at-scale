
## Completed-run interpretation

All 1,200 expected requests are saved with unique keys. The original 493 saved rows remain byte-for-byte unchanged after resumption. Engine errors, request errors and selected-raw-schema constraint violations: zero. Truncations remain model/runtime output failures and are included in accuracy, not excluded.

The constrained arms hit the 512-token limit on 95/600 requests, versus 1/600 free requests. Sampled constrained failures contain repeated whitespace. Primary pooled raw selection E2E is 85.5% free versus 70.5% constrained (-15 points). This measures this pinned setup, not general constrained-decoding effectiveness or a demonstrated training need. Investigate whitespace/token-limit behavior and test a second engine before training; any changed inference condition requires a separately named follow-up run. Preserve this completed run. E1 and E2 remain gated.

All 1,200 recorded pre-request checks show normal memory pressure, nominal thermal state and no active swap writes (the initial interval has no rate). These are sampled checks, not continuous temperature/GPU telemetry. Qwen was gracefully unloaded after completion; pressure remained normal. No other apps were closed.

The report uses the maximum across both corrected-run server lifetimes. Maximum RSS was 2980265984 bytes; those lifetimes also include readiness/preflight work. This is process RSS, not total unified-memory or Metal allocator peak.

Follow-up: [targeted whitespace diagnosis](../e0-whitespace-diagnostic-v1/REPORT.md), kept separate from this benchmark.

The [exact-engine clean-run key-order audit](KEY_ORDER.md) supports a deeper order-related mechanism: 252/501 eligible free-correct calls are outside the grammar only due to order; all 249 already accepted calls remain correct. A causal control is still needed before E1.
