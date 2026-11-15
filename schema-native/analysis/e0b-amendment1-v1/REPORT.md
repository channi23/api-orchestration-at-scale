# E0b Amendment 1: online smoke stopped

**Stopped at the locked smoke gate; model unloaded. No determinism or benchmark requests were made.**

The approved sequence began under the unchanged Qwen3-1.7B Q8_0 E0 profile: context 8192, batch 512, microbatch 128, one slot/request, 29 GPU layers, greedy seed 0, thinking disabled and a 512-token output cap. Inference source: c5f560abf3e74e352d9d5510035e7afe7fa20df2.

The four predeclared adversarial probes used their 64-token preflight cap; smoke used the unchanged 512-token cap. No approved inference setting was changed.

## Observed stop

- Request: `smoke|C1|select|UNIT|C020_R00|T103_p0`.
- HTTP 200; finish_reason `length`; 512 completion tokens.
- No fresh engine-error log entries were recorded. The locked smoke check rejects truncation, so it did not issue a passing receipt.
- Readiness budget: **11/60** generation attempts saved, comprising four adversarial checks and seven smoke attempts. Six smoke attempts finished before the seventh hit the cap. Remaining planned smoke/V checks were not sent.
- Determinism: **0/30 attempted**. Benchmark: **0/700** new requests; no F0/C0 rows imported or baselines rerun. C1/C2/V benchmark arms were not started.
- STOPPED.json was written immediately. The dedicated Qwen server then received one graceful SIGINT and exited. No other apps were closed.

## Verified and not verified

- Native capability had passed before loading. The online model/build/template/context checks and four adversarial constant/bounds checks passed before reaching smoke.
- The context-check function returned successfully before smoke. It did not persist its intermediate token counts because the final online receipt was never issued; no new maximum-token measurement is claimed here.
- Every recorded pre-request memory check was normal and every thermal check nominal. Every available active-swap-write interval was zero; the initial interval has no rate. Post-unload checks were also normal/nominal. These are sampled checks, not continuous temperature/GPU telemetry.
- System-wide swapout counters increased by **484.94 MiB** between the pre-load and post-unload observations. Thus zero recorded guard-interval rates must not be read as zero swapping across the whole operation. The delta is not process-attributed and does not establish sustained heavy swapping; model-load/runtime-verification and other unsampled windows are not covered by those rates. See swap-counter-observations.json.
- Server lifetime peak process RSS: **2943205376 bytes** (2.74 GiB), including preflight/context/smoke. This is not total unified-memory or Metal allocator peak.
- Not verified: a passing full live smoke, any of the frozen 30 determinism matches, E0b benchmark accuracy/latency, or either co-primary/secondary comparison. No locked order-effect rule is evaluated.
- sn.e0b_report produced an incomplete readout with zero final rows and all 1,500 expected final unit-arm rows missing; it emitted no paired inference. No conclusion is drawn beyond the smoke stop rule. E1/E2 remain gated; no training occurred.

## Manifest and reporting provenance

Because preflight stopped before the benchmark runner, that runner had not created its manifest/results files. Finalization wrote the unchanged approved identity manifest and an empty results.jsonl solely to permit the standard zero-benchmark partial report. CAMPAIGN.json states this explicitly. Frozen inputs, model profile, code hashes, budget ledger, raw readiness outputs, STOPPED.json and path-redacted server evidence are published alongside this report. No successful preflight receipt is claimed.

## Every look-alike key and its matched declaration

The complete instance list is in flagged-key-instances.json, with request ID, pointer, key, matched declared key and rule. The table below lists every distinct key/match pair. Frozen E0 reference entries are explicitly separated from this stopped E0b attempt. Prefix/underscore matches can denote legitimately different keys; these flags alone do not establish errors, and no key is renamed or score changed. A quote-only flag with no matching declaration is labeled none. Truncated/unparseable responses cannot receive this complete-JSON diagnostic.

| Dataset | Flagged key (JSON string) | Matched declared key | Rule | Instances |
|---|---|---|---|---:|
| frozen_E0_reference | <code>&quot;con_date &quot;</code> | <code>&quot;con_date&quot;</code> | normalized_equal | 4 |
| frozen_E0_reference | <code>&quot;con_date”: &quot;</code> | <code>&quot;con_date&quot;</code> | declared_prefix_boundary | 1 |
| frozen_E0_reference | <code>&quot;o”: { &quot;</code> | <code>&quot;o&quot;</code> | declared_prefix_boundary | 1 |
| frozen_E0_reference | <code>&quot;parent_id\&quot;: \&quot;r-101\&quot;, &quot;</code> | <code>&quot;parent_id&quot;</code> | declared_prefix_boundary | 4 |
| frozen_E0_reference | <code>&quot;s&#x27;: [0, 50], &quot;</code> | <code>&quot;s&quot;</code> | declared_prefix_boundary | 1 |
| frozen_E0_reference | <code>&quot;s”: [0, 50], &quot;</code> | <code>&quot;s&quot;</code> | declared_prefix_boundary | 4 |
| frozen_E0_reference | <code>&quot;url”: &quot;</code> | <code>&quot;url&quot;</code> | declared_prefix_boundary | 4 |
| frozen_E0_reference | <code>&quot;userId”: &quot;</code> | <code>&quot;userId&quot;</code> | declared_prefix_boundary | 1 |

Online-readiness flagged key instances: **0**. No E0b benchmark outputs exist. Frozen-reference instances are diagnostic context only, not new inference.

## Final state

**STOPPED; no automatic retry, baseline rerun, parameter change or further inference.** Results are published for review. The original E0 rows, experiment/ and locked inference settings are preserved.
