# E0b interpretation and gate decision

**Review accepted at `0445f22`, 2026-11-15. No rescoring, new inference or training.**

This interpretation records the completed campaign and reviewer audit. The original results,
manifest, four locked contrasts, failure labels and historical report/export adapter remain
unchanged. See [REPORT.md](REPORT.md), [report.json](report.json) and
[failure-taxonomy.json](failure-taxonomy.json).

## Supported on this model, engine and benchmark

**Schema-order enforcement by the pinned engine costs about 18 percentage points.** On pooled
select, C1 scores 70.0% and oracle-order C2 scores 88.0%. The locked C2 − C1 contrast is **+18.0 pp**,
with a 95% catalog-replicate bootstrap interval **[10.0, 26.5]** and co-primary Holm p
**5.6752469e-10**. It meets the predeclared +8-pp/positive-interval rule. Review additionally supplied
an intent-level bootstrap sensitivity interval **[9.0, 28.0]**; it supports the same gate outcome
but does not replace the locked interval. That sensitivity calculation was supplied by review,
not newly run for this document.

**Fixed separators do not improve accuracy here.** C0 scores 70.5% and C1 70.0%; C1 − C0 is
**−0.5 pp**, interval **[−1.5, 0.0]**, secondary Holm p **1.0**. This is the bounded observed
“no accuracy change” finding: it is not a formal equivalence result or a claim of exactly equal
scores. Fixed separators alone do not remove the observed order cost.

**V matches the oracle arm closely, descriptively: 265 versus 266 correct out of 300.** V uses
**1.11× F0 total tokens** across all 300 units: 855,017 / 770,786 = 1.1093. These totals count the
reused free attempt plus fresh retry where routed; they are not a fresh end-to-end timing claim.
The one-answer difference is not a statistical equivalence test. The deployable comparison is V,
not an oracle that knows the model's preferred output order.

## Not supported

**A gain of constrained over free decoding is not established.** The locked pooled-select V − F0
contrast is **+2.5 pp**, with interval **[0.0, 5.5]** touching zero and co-primary Holm p **0.0625**.
The secondary C2 − F0 contrast is also +2.5 pp with that interval and secondary Holm p **0.125**.
The order-effect result must not be presented as evidence that constrained decoding generally
outperforms free decoding or that training will improve performance.

## Descriptive review observations only

These post-run audit counts are descriptive, not additional primary tests, new scoring rules or
independent evidence of generalization:

- C2 arguments equal F0 arguments in **269/300** units.
- Constrained retry corrected **17/32 strict-router-invalid free outputs**. This selected-subset
  count is not a 17-answer net gain over the frozen evaluator baseline; strict routing and the
  preserved original evaluator need not agree on every reused free output.
- Residual C2 failures are **22 valid-wrong-value, 6 truncated and 6 look-alike-key** outcomes.
  Legal-prefix truncations stay scored. Look-alike flags are mechanical diagnostics; every
  flagged key and its matched declared key is retained in [LOOKALIKE_KEYS.md](LOOKALIKE_KEYS.md)
  and [lookalike-flags.json](lookalike-flags.json). No key was renamed or score changed.

## Limits

This is **one model, one pinned engine and approximately 50 intents**. The oracle arm is not
deployable: its schema ordering uses each task's frozen free output. The current observations do
not establish transfer to unseen schemas, other engines, models or API workloads. A sensitivity
bootstrap and repeated representations do not create additional independent intents.

The 20-pair stress-fixtures 0.4 bundle is an external example bundle, **not** a larger held-out task
set or a frozen split dataset. It did not contribute tasks or results to E0b.

## Gate decision

**Residual headroom is too small to test training credibly on this task set. E1/E2 stay gated until
a larger held-out task set exists.** The next work is design-only: independent task/family splits,
source holdouts, coverage and enforcement gates, explicit contracts and a justified sample size.
No LoRA/QLoRA infrastructure, contrastive training or model inference is authorized by this finding.

## Historical reproduction

`export_report.py` remains unchanged as the record of how this report was produced after the NumPy
boolean export error. The later one-line `sn.e0b_report` fix converts the same rule value to Python
bool for future report exports; it changes no rule or statistic. Historical reproduction must use
the frozen execution source/identity recorded in the manifest (or the reviewed `0445f22` checkout),
not rewrite that identity to match later code. No completed report was regenerated for this update.
