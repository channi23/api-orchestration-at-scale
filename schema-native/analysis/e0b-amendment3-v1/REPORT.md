# E0b Amendment 3 — completed locked campaign

**COMPLETE — Qwen unloaded. Stop for review; E1/E2 remain gated. No training.**

Run ID: `e0b-amendment3-v1`. Frozen execution source: `30d04b1a82eb0cf631b01ad6e8dca6881b95cd12`.
This report applies only the locked contrasts and decision rule. It makes no claim about training, unseen-schema transfer or general engine completeness.

## Execution and preservation

- After the Mac restart, fresh admission passed at **6,287,589,376 bytes (5.86 GiB)** and normal pressure (1). The helper self-test passed before load.
- The original eleven readiness charges and frozen inputs were preserved. No prior swap baseline existed because the preceding attempt never loaded a model. A new baseline was created immediately before this first load, not reset during inference.
- The unchanged Qwen3-1.7B Q8_0 E0 profile loaded and passed three consecutive normal samples in the settling window. Online runtime/model/build/template/context checks and the 19 new preflight/smoke generations passed.
- **All 30 determinism requests (15 F0 + 15 C0) matched raw_content byte-for-byte.** No baseline was rerun beyond these locked checks.
- Then **all 300 C1**, **all 300 C2**, and **32 V retries** completed in the locked order. No interim accuracy was inspected. No engine/request fault, confirmed illegal prefix, pending prefix check or in-run resource pause occurred.
- There are **1,500 final arm rows** and **1,562 saved records**: final rows plus 30 control responses and 32 separately stored V retry attempts. A V aggregate is not another inference request.
- The initial resource-only STOPPED.json was archived unchanged on resume. The initial published report and stop remain under `history/pre-load-stop/` and `resource-stops/`. Both earlier stopped campaigns, frozen E0 and experiment/ are unchanged.

## Locked pooled-select comparisons

All four contrasts below use 200 paired select units and include truncations. Intervals are the locked 95% catalog-replicate bootstrap intervals. **Only approximately 50 intents are independent.** The two co-primary tests form one Holm family; the two secondary tests form a separate family.

| Locked contrast | A accuracy | B accuracy | B − A (pp) | 95% interval (pp) | Holm p |
| --- | ---: | ---: | ---: | --- | ---: |
| P1: order effect: C2 − C1 | 70.0% | 88.0% | +18.0 | [10.0, 26.5] | 5.6752469e-10 |
| P2: deployment: V − F0 | 85.5% | 88.0% | +2.5 | [0.0, 5.5] | 0.0625 |
| S1: separators: C1 − C0 | 70.5% | 70.0% | -0.5 | [-1.5, 0.0] | 1 |
| S3: oracle versus free: C2 − F0 | 85.5% | 88.0% | +2.5 | [0.0, 5.5] | 0.125 |

**Locked order-effect rule: MET.** C2 − C1 is +18.0 pp, at least +8 pp, and the interval lower bound is +10.0 pp, above zero. This is the rule as locked; no new threshold or interpretation is added.
V − F0 is +2.5 pp with interval [0.0, 5.5] and Holm p=0.0625. No additional deployment-success criterion or training decision is inferred.

## Descriptive arm totals and failure taxonomy

These totals cover all 300 units per arm (200 select + 100 arggen), so they are distinct from the pooled-select comparison table. Primary scores preserve frozen evaluator e2e_success for reused rows. Failure labels use the locked strict diagnostic precedence and may differ from frozen evaluator success totals; **no frozen E0 row was rescored**. Overlapping flags are separate columns in failure-taxonomy.json.

| Arm | Evaluator successes / 300 | Correct diagnostic | cd_truncated | invalid | wrong_tool | lookalike_key | valid_wrong_value | engine_refusal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| F0 | 256 | 248 | 0 | 32 | 0 | 0 | 20 | 0 |
| C0 | 211 | 211 | 48 | 0 | 0 | 11 | 30 | 0 |
| C1 | 210 | 210 | 22 | 0 | 0 | 33 | 35 | 0 |
| C2 | 266 | 266 | 6 | 0 | 0 | 6 | 22 | 0 |
| V | 265 | 265 | 6 | 0 | 0 | 6 | 23 | 0 |

F0/C0 are frozen reused arms. V reuses the free attempt and adds a fresh C1-style retry only when the strict router routes it; aggregate usage and recorded times are labelled, not presented as fresh end-to-end timing.
All **37 fresh capped constrained benchmark/control attempts** had native legal-prefix proofs. This count includes determinism controls and excludes duplicate V aggregates; smoke prefix proofs are retained separately in readiness-results.jsonl. Legal-prefix truncation remained a scored outcome, not a stop.

## Budget ledger

| Allowance | Historical charges | New requests | Cumulative spent | Cap | Remaining |
| --- | ---: | ---: | ---: | ---: | ---: |
| Readiness/smoke | 11 | 19 | 30 | 60 | 30 |
| Benchmark incl. determinism | 0 | 662 | 662 | 700 | 38 |

Every benchmark reservation has exactly one durable attempt record; all request keys are unique. Failed/uncertain-charge reset and automatic retry were not used. The ledger contains 692 charges total, including the eleven historical readiness charges.

## Resource observations and unload

- 103 explicit 30-second monitor samples during the resumed execution segment all recorded normal pressure (1) and nominal Foundation thermal state (0). The runner also sampled before/after generation and retained per-request checks.
- Maximum sampled cumulative system swapout growth from the fresh pre-load baseline: **0 bytes**. Maximum sampled swapout write rate: **0 bytes/s**. No in-run resource pause or timeout was recorded.
- Qwen was gracefully unloaded through the verified owned process group. Its launcher exited after the termination signal; the group-unload check confirmed no live members. The temporary idle-sleep inhibitor ended with that server.
- After unloading: pressure **1**, thermal state **0**, cumulative swapout growth **0 bytes**, and **0 additional swapout bytes** in a 2.01-second sample.
- These are global, sampled observations, not continuous telemetry, GPU-temperature measurements, process-specific swap attribution or a hardware-longevity guarantee. CPU/GPU utilization and model-lifetime peak RSS are not claimed.
- The ten-process resident-memory inventories remain **local and unpublished**. Public resource logs remove them. The old pre-load warning is historical evidence, not an in-run warning.

## Oracle and every look-alike key

Actual C2 outputs: **300**. Recorded output-side flags: **oracle_not_applied=32**, **oracle_incomplete=0**. Planned counts are separately retained in oracle-counts.json.
Every flag instance from saved benchmark/control records and tool-call smoke records is listed in lookalike-flags.json, with its pointer, key, matched declared key and record role. There are **87 record-level flag instances and 19 distinct key/match pairs**; reused and V-aggregate duplicates are explicitly labelled. These are mechanical flags and can include legitimate underscore-boundary matches. No keys were renamed and no scores changed.

# Every flagged key and its matched declared key

Full provenance for every instance is in lookalike-flags.json. Counts include labelled reused/control/aggregate records; they are not unique inference-request counts. Mechanical flags do not establish incorrectness.

| Flagged key | Matched declared key | Instances |
| --- | --- | ---: |
| <code>&quot;birthDate”: &quot;</code> | <code>&quot;birthDate&quot;</code> | 1 |
| <code>&quot;breed”: &quot;</code> | <code>&quot;breed&quot;</code> | 1 |
| <code>&quot;comments”: &quot;</code> | <code>&quot;comments&quot;</code> | 1 |
| <code>&quot;con_date &quot;</code> | <code>&quot;con_date&quot;</code> | 4 |
| <code>&quot;con_date”: &quot;</code> | <code>&quot;con_date&quot;</code> | 5 |
| <code>&quot;editions\&quot;: [&quot;</code> | <code>&quot;editions&quot;</code> | 1 |
| <code>&quot;end_date”: &quot;</code> | <code>&quot;end_date&quot;</code> | 1 |
| <code>&quot;message &quot;</code> | <code>&quot;message&quot;</code> | 2 |
| <code>&quot;name”: &quot;</code> | <code>&quot;name&quot;</code> | 17 |
| <code>&quot;o”: { &quot;</code> | <code>&quot;o&quot;</code> | 1 |
| <code>&quot;parent_id\&quot;: \&quot;r-101\&quot;, &quot;</code> | <code>&quot;parent_id&quot;</code> | 9 |
| <code>&quot;parent_id”: &quot;</code> | <code>&quot;parent_id&quot;</code> | 2 |
| <code>&quot;revision_id”: &quot;</code> | <code>&quot;revision_id&quot;</code> | 2 |
| <code>&quot;s&#x27;: [0, 50], &quot;</code> | <code>&quot;s&quot;</code> | 2 |
| <code>&quot;start_date”: &quot;</code> | <code>&quot;start_date&quot;</code> | 1 |
| <code>&quot;s”: [0, 50], &quot;</code> | <code>&quot;s&quot;</code> | 14 |
| <code>&quot;typeName”: &quot;</code> | <code>&quot;typeName&quot;</code> | 9 |
| <code>&quot;url”: &quot;</code> | <code>&quot;url&quot;</code> | 8 |
| <code>&quot;userId”: &quot;</code> | <code>&quot;userId&quot;</code> | 6 |

## Report export adapter and reproducibility

The first sn.e0b_report export computed the locked results but failed JSON serialization because order_effect_rule_met was a NumPy boolean. The model was unloaded in a finally block. The published export_report.py calls the same sn.e0b_report function and converts **only that already-computed boolean** to a Python bool before JSON export. Statistical calculations, comparisons, data and rule are unchanged; original sn/ source and the campaign manifest remain frozen. No inference was repeated.

Reproduce the export from the original unchanged checkout with the saved campaign records:

```sh
.venv/bin/python analysis/e0b-amendment3-v1/export_report.py
```

Raw records, results.jsonl.gz, manifest, frozen plan, configs, exact budget ledger, public readiness receipt/results, native prefix proofs, resource monitor/events, baseline and post-unload observations are published here. PUBLICATION.json identifies original record hashes and redactions. SHA256SUMS covers the publication files.

## What was and was not verified

Verified: native capability gate; frozen input/model/source identity; actual online runtime checks; pre-load admission and settling; 19 new smoke/preflight responses; all 30 exact determinism checks; all C1/C2/V inference; finished-output strict/constraint/raw-schema guards and capped-output prefix proofs; budgets and request uniqueness; resource sampling and owned-server unload; frozen-data preservation; complete locked report and output diagnostics.
Pre-execution regression suite: **154 package + 12 original evaluator tests = 166 passed**. No inference-code changes were made during this campaign. Publication checks independently verify all completed keys, determinism bytes, immutable source hashes, response/ledger correspondence, redaction and the boolean-only export conversion.
Not established: exhaustive engine enforcement outside tested schemas/witnesses, continuous thermal/swap behaviour between samples, unseen-schema transfer, LoRA/training outcomes, or any claim beyond the locked contrasts and decision rule. The independent stress-fixtures example bundle remains outside this repo and was not used by E0b.

**Final state: complete, model unloaded, published for review. E1/E2 remain gated. No training.**
