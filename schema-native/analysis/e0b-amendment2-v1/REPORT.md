# E0b Amendment 2: stopped on post-load memory warning

**STOPPED before any generation request. Qwen unloaded; no retry.**

Inference-attempt source: `cb97afff5eac5275d0140d92205759268f64bfb7`. Reviewed source was fd9fa84; the required benchmark illegal-prefix/finished-constraint and non-nominal thermal stop guards were added and tested before loading, without changing model, prompts, sampling, budgets, frozen selections or analysis rules.

## Observed sequence

- Model-free native gate and frozen-input identity passed. Enforcement tests passed: **108 package tests + 12 evaluator tests**.
- The cumulative system swapout baseline was initialized immediately before loading. The pre-load guard recorded pressure normal (1), thermal nominal (0), and swapout growth zero.
- The unchanged E0 profile was used to start the dedicated Qwen server. The first post-load guard raised **memory-pressure level 2**, before the health/API check or online preflight.
- STOPPED.json was saved. The server received one graceful SIGINT and exited. No apps other than our dedicated model were stopped.
- No online preflight/smoke, determinism, C1, C2 or V generation request was sent. No baseline was imported or rerun.

## Budget and report status

| Category | Prior spending | New spending | Cap | Remaining |
|---|---:|---:|---:|---:|
| Readiness/smoke | 11 | 0 | 60 | 49 |
| Benchmark (including determinism) | 0 | 0 | 700 | 700 |

The new ledger imports the eleven historical charges under namespaced keys; it was finalized after the stop and contains no new attempts. The prior ledger and prior STOPPED.json remain unchanged. No passing online receipt exists.

sn.e0b_report was run after unloading. It reports **zero final rows, 1,500 missing rows, complete=false**, with no comparisons or decision-rule evaluation. The exact identity snapshot captured before model load was copied into the standard manifest for that partial report; an empty results file represents zero actual benchmark rows. CAMPAIGN.json documents finalization.

## Resource observations

- Stop trigger: the post-load guard reported memory-pressure warning level 2. It short-circuited before taking that check's thermal/swap samples; those values are not invented.
- After unloading: pressure **1**, Foundation thermal state **0**.
- Cumulative system-wide swapout growth from the pre-load baseline to the post-unload observation: **311.12 MiB**.
- Additional swapout bytes observed over the two-second post-unload sample: **0**.
- Server-lifetime peak process RSS: **2841264128 bytes (2.65 GiB)**. This is not total unified-memory or Metal allocation peak.
- These are sampled/global observations, not continuous telemetry or proof that Qwen caused all system activity. The memory warning alone was sufficient to stop; no inference was attempted after it.

## Oracle and look-alike counts

- Frozen-plan units: 300; planned oracle_not_applied: **32**; planned oracle_incomplete: **0**.
- Actual C2 outputs: **0**. Observed output-side oracle counts are **not measured**, not inferred from plan flags. Full planned flags remain in frozen-plan.json.gz and oracle-counts.json.
- New generation outputs and new look-alike flag instances: **0**. This is not evidence of absence of such errors; no outputs were produced.
- lookalike-flags.json lists every frozen-reference flag with its matched declared key. Those are historical E0 context only. Prefix/underscore matches are mechanical flags and may denote legitimately different keys; no keys or scores are changed.

| Historical flagged key (JSON string) | Matched declared key | Instances |
|---|---|---:|
| <code>&quot;con_date &quot;</code> | <code>&quot;con_date&quot;</code> | 4 |
| <code>&quot;con_date”: &quot;</code> | <code>&quot;con_date&quot;</code> | 1 |
| <code>&quot;o”: { &quot;</code> | <code>&quot;o&quot;</code> | 1 |
| <code>&quot;parent_id\&quot;: \&quot;r-101\&quot;, &quot;</code> | <code>&quot;parent_id&quot;</code> | 4 |
| <code>&quot;s&#x27;: [0, 50], &quot;</code> | <code>&quot;s&quot;</code> | 1 |
| <code>&quot;s”: [0, 50], &quot;</code> | <code>&quot;s&quot;</code> | 4 |
| <code>&quot;url”: &quot;</code> | <code>&quot;url&quot;</code> | 4 |
| <code>&quot;userId”: &quot;</code> | <code>&quot;userId&quot;</code> | 1 |

## What was and was not verified

- Verified: model-free C1/C2/V capability; unchanged frozen plan/model profile and original 30 selections; guard enforcement tests; creation of a pre-load swap baseline; a normal pre-load check; actual post-load memory warning and stop; graceful model exit; budget/source/evidence integrity.
- Not reached: online GGUF checksum/build/template/context checks, live smoke, the thirty determinism comparisons, any benchmark output, accuracy/latency comparisons, either co-primary/secondary test or the locked order-effect rule. No new live model-weight checksum measurement is claimed.
- experiment/, original E0 rows, all prior stopped-campaign files and prior charges are preserved. E1/E2 remain gated. No training.

**Final state: model unloaded; stopped for review. No retry or further model work.**
