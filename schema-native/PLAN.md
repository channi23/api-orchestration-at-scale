# Plan — schema-native stages

Written before any new model run. Predictions below are fixed now so they can be wrong.

## Hypotheses

- **H1 (decoding).** For untuned Qwen3-1.7B, constrained decoding raises end-to-end success on Raw by
  less than the measured upper bound of +7.6 points, and leaves the count of schema-valid wrong-value
  outputs unchanged or higher.
- **H2 (training adds to decoding).** A LoRA adapter trained only on schemas from other families raises
  end-to-end success of the constrained system on unseen tools, and the gain comes from fewer
  schema-valid wrong-value outputs.
- **H3 (schema sensitivity).** Training on minimal schema pairs (one keyword changed, different correct
  output) transfers to unseen schemas better than the same amount of ordinary tool-calling data.

## Stage 1 — E0: decoding only (no training)

`configs/runs/e0_decoding.json`. 4 arms × (100 arggen + 100 tasks × 2 catalog sizes) = 1,200 requests.

Primary comparison: `B_raw_cd` vs `A_raw_free`, end-to-end success, select family, paired, exact McNemar,
95% CI from the replicate bootstrap.

Predictions (from `analysis/ceiling-full-v2`), sizes 5 and 20 pooled, Raw:
- free: about 86% (finished experiment: 92% and 80%).
- constrained: between 86% and 93%; point prediction 89%.
- schema-valid wrong-value failures: not lower under constrained decoding.

Read-out and gate:
| Result | Meaning | Next |
|---|---|---|
| Constrained ≥ 95% | The benchmark is nearly solved by decoding alone. No room to show a training effect. | Build the harder task set first (stage 2a), then train. |
| Constrained 86–95%, valid-wrong share ≥ half of failures | Remaining errors are semantic. | Go to stage 2. |
| Constrained < free | Constraint tax or engine fault. | Check `engine_error` rows and the engine audit; repeat with a second engine before any conclusion. |

Also report: engine refusals, tokens, p50/p95 latency, and the same table for minified.

## Stage 2a — task set v2 (needed for power)

The frozen v1 set has an effective sample size of about 102. To detect a 5-point paired difference at
80% power needs about 310–630 independent pairs.

- Author one task for each of the 250 pool tools that are not yet targets (same rules, same leakage
  audit as v1). v1 stays frozen and is reported separately.
- Add a keyword stress set of about 120 tasks on schemas built by deterministic edits of pool
  schemas: `oneOf` with a discriminator, `if/then/else`, `not`, `dependentRequired`, `$ref` to `$defs`,
  `additionalProperties: false`, `unevaluatedProperties: false`, array bounds, numeric and string bounds,
  one recursive schema family. Every gold answer is validator-checked.
- Add about 60 impossible or ambiguous requests (required value missing, no suitable tool). The correct
  output is an explicit abstention, added to the output contract as a third envelope branch.

## Stage 2 — E1: training × decoding

`configs/runs/e1_lora.json`. Arms A–E of the brief, plus `Bm_min_cd` so that E has a like-for-like
untuned partner.

Training data: `sn.synth` on the 1,761 training schemas (families disjoint from validation; all disjoint
from the 300 test tools). Report the teacher, the keep rate, and the reject reasons.

Primary comparison: `E_min_lora_cd` vs `Bm_min_cd`, end-to-end success on unseen tools.
Success criterion for H2: Δ ≥ +5 points with a 95% CI excluding 0, and a drop in schema-valid
wrong-value failures. H2 is rejected for this setting if the CI lies below +3 points.

Controls that must be reported next to it:
- C vs A (LoRA, no constraint) and B vs C (constraint vs LoRA).
- A LoRA trained on a public flat tool-calling corpus of equal token count, to separate "learned the
  output contract" from "learned schemas".
- Training loss on the answer only (`mask_prompt: true`), one seed first, then 3 seeds for the primary.

## Stage 3 — E2: schema-contrastive training (the novel part)

For each training schema, apply one meaning-changing edit (make an optional field required, narrow an
enum, add a bound, add a conditional requirement, swap a `oneOf` branch) and keep request text fixed.
The validator decides the new gold answer or marks the request impossible. Train on the pairs.

Evaluation is metamorphic, on unseen schemas only:
- **Invariance**: meaning-preserving rewrites (minify, key order, `$ref` inline ↔ `$defs`, `allOf`
  flattening) must not change the answer. Score: share of pairs with identical normalized arguments.
- **Sensitivity**: meaning-changing edits must change the answer in the validator-determined way.
  Score: share of pairs where both members are correct.

H3 is supported if the contrastive adapter beats the equal-size ordinary adapter on sensitivity by
≥ 5 points on unseen schemas, with constrained decoding on in both.

## Stage 4 — hybrid selection (only if a harder selection set exists)

Selection is at ceiling here and BM25 matches the model. Build catalogs that contain several tools of
the same function family first. Then compare, on the same tasks: BM25 top-k, LLM logit scoring of the
tool-name position (one prefill, no extra model), and a fine-tuned Laya checkpoint over
schema-derived tool cards. Report accuracy, ECE, Brier, risk–coverage and latency. Laya's own
documentation says to keep one choice question to about 20 options, so the decision model sits after
a shortlist, not in place of it.

## What would falsify the direction

- E0 shows constrained decoding alone reaches ≥ 95% on v1 **and** on the v2 stress set.
- E1 shows no LoRA gain on unseen tools once decoding is constrained (CI below +3 points).
- E2 shows the contrastive adapter is no better than ordinary data on sensitivity.
- A larger untuned model that fits in 16 GB (for example a 4-bit 4B model) with constrained decoding
  matches the tuned 1.7B system at similar latency. Then the result is "use a bigger model".

## E0 implementation clarification (before any new inference)

The historical structural-rescue “upper bound” is a descriptive estimate from the stored free
outputs, not a mathematical limit on constrained accuracy. Constraints change token probabilities
and may change valid-but-wrong outputs too. H1's valid-wrong prediction remains empirical.

E0 has mandatory offline/online preflight, content-pinned resume, explicit run completeness, and a
12-request smoke separate from the 1,200-request benchmark. E1 training/export commands stay gated
until the real E0 readout and unseen-schema v2/stress data are reviewed. E2 remains deferred.
