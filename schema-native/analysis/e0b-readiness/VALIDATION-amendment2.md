# E0b Amendment 2: model-free review validation

**2026-11-15 IST — native capability gate PASS; STOP for user review before model work.**

No model was loaded, no new model inference or training ran, and no future run directory or swap
baseline was initialized. E1/E2 remain gated. Amendment 2 is appended after all earlier plan text;
both configs preserve verbatim Amendment 1 text and its earlier locked history. The stopped
`e0b-amendment1-v1` campaign, including STOPPED.json and all 11 charged attempts, is unchanged.

## Actual stopped-output verification

- Request: `smoke|C1|select|UNIT|C020_R00|T103_p0`.
- Original response: HTTP 200, finish_reason length, 512 completion tokens, no fresh engine-error log.
- The native helper consumed the stored text under the **exact request grammar**, with its C1
  constraint-copy identity checked against the frozen prior plan. **Legal prefix: true; complete
  accepting value: false.** This passes the amended gate as **cd_truncated**.
- The frozen E0 `select|B_raw_cd|C020_R00|T103_p0` also finished by length at 512 tokens. This is
  the same capped outcome on the same unit; equality of the two output byte strings is not claimed.
- No schema, tokenizer/model setting, output cap, router, oracle, contrast or analysis threshold
  was changed. The helper links the exact recorded bundled llguidance static library, not a PyPI
  approximation. `amendment2-prefix-proof.json` records grammar/text/helper/library hashes.

## Gate semantics and tests

C1/C2/V smoke requires HTTP 200 and no fresh engine-error entry. A finished response must strict-parse
and validate against both the actual constraint copy and the selected tool's original raw schema.
A length finish instead requires native legal-prefix proof; it is not parsed as complete JSON.
Invalid prefixes, engine/HTTP errors, malformed or non-strict responses, constraint violations and
raw-schema violations stop and save evidence. Successful truncations persist their prefix proof.
The adversarial constant/bounds probes still must finish and validate.

Benchmark truncation alone remains a recorded/scored cd_truncated outcome, not an engine-fault stop.
Tests verify this independently of smoke. No original E0 response, key or evaluator score is modified.

## Cumulative allowance and new run identity

New configured run: **e0b-amendment2-v1**. The old run ID is refused; its STOPPED.json is never removed
or overwritten. The actual published prior budget ledger is SHA-pinned in both configs. It contains
**11 readiness charges and zero benchmark charges**. These are imported once under historical
namespaced keys into the future new ledger; new repeated probes are separate charges. Missing or
altered prior charges stop rather than resetting the budget.

- Readiness/smoke cap: **60 total, 11 already spent, 49 remaining**.
- Benchmark cap: **700 total, zero spent**. Expected unchanged benchmark count: **662**.
- The 19 planned new readiness generations would bring cumulative spending to 30/60, not 19/60.
- The frozen 15 F0 plus 15 C0 sample is unchanged. Any byte mismatch still writes STOPPED.json and
  stops without rerunning baselines. C1 then C2 then V and the Holm/threshold rules are unchanged.

Budget tests seed all 11 charges, allow exactly 49 further readiness reservations, reject the 50th,
preserve the original source bytes, and reject an existing ledger that omits the historical charges.
No real new-run ledger is created during this review.

## Observation disclosure

Smoke units are benchmark units. **Seven C1/C2 outputs were observed before the benchmark**. This
control-gate correction is informed by that observation; no analysis decision rule was changed.
The forthcoming benchmark must disclose this and must not be described as a blinded independent
replication of those units. The prior stopped campaign remains published as it occurred.

## Cumulative system swapout guard prepared for the future confirmed run

The new code requires an explicit pre-load baseline (`python -m sn.e0b_swap`) immediately before
loading Qwen, only after review confirmation. No baseline is initialized now. The same system-wide
counter baseline persists through preflight and benchmark and includes the loading window. Growth
**strictly greater than 1 GiB** stops at the next admission check; exactly 1 GiB does not satisfy the
"more than" condition. Boot/counter-reset identity mismatch or a missing baseline also stops.
Existing pressure, active-write-rate and thermal guards remain. This is admission sampling, not a
claim of continuous monitoring or process-specific swap attribution.

Tests cover the exact threshold, threshold plus one byte, reboot identity and missing baseline.
No resource or model setting is changed beyond the explicitly requested cumulative stop guard.

## Native readiness counts

| Check | Result |
|---|---:|
| C1 compiled | 70/70 |
| C2 compiled | 300/300 |
| C1 gold reachable | 300/300 |
| C1 invalid witnesses accepted | 0/6696 |
| C2 invalid witnesses accepted | 0/6696 |
| V select routed | 18/200 |
| V fixed-tool routed | 14/100 |

These remain finite model-free witnesses, not exhaustive schema-language or live-tokenizer proof.
C3 remains excluded and its original model-free finding is preserved unchanged. Earlier readiness
reports and native evidence are archived as VALIDATION-amendment1.md and native-amendment1.json;
all earlier C3 archives remain published. No analysis of new model performance has been performed.

## Test totals and final state

**105 package tests + 12 original evaluator tests passed.** TESTS.txt records exact commands. New
tests prove legal-prefix truncation passes; illegal-prefix truncation, engine errors and each schema
violation stop; finished valid JSON passes; and benchmark truncation remains a model outcome.
History/cumulative-budget/swap tests passed, and all existing oracle/router/decision-rule tests passed.
The 30 frozen selections and earlier stopped-campaign files remain unchanged. No E0 rows or
experiment/ files were altered.

**STOP FOR REVIEW.** Not run: new online preflight/smoke, real determinism checks, benchmark
inference, actual swap-window initialization, model accuracy/latency readout or training. Only
explicit user confirmation authorizes the future model sequence. E1/E2 remain gated.

## Confirmed-execution guard audit (before model loading, 2026-11-15 IST)

The user confirmed execution and explicitly required stopping on an illegal benchmark truncation, a finished constraint-copy violation and any thermal warning. The benchmark path now uses the same pinned native prefix proof for length finishes, validates finished outputs against the constraint copy as well as the named raw schema, and treats non-nominal E0b thermal states as stops. Legal-prefix truncation remains a scored model outcome. Prompts, model/sampling settings, sample selection, budgets and analysis rules are unchanged. Model-free validation: 108 package tests and 12 evaluator tests passed; active native capability passes. Native verification time falls within the runner's recorded request wall time, which already includes response evaluation. These are enforcement fixes made before the new run.
