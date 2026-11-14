# E0b: separate order effects from deployment performance

Status: prospective design after the completed E0 and external review, **not an executed or fully
locked experiment**. No E0b model inference has run. E1/LoRA and E2 remain gated. Preserve E0's
1,200 rows; never pool E0b rows with them or change an existing run's inference parameters.

## Proposed conditions

Raw representation only, the same 300 request units (200 select, 100 fixed-tool argument generation):

| Arm | Condition | Evidence needed |
|---|---|---|
| F0 | Original free decoding | Reuse only after a prospectively selected 30-request determinism check shared with C0 |
| C0 | Original schema order, flexible llguidance whitespace | Same conditional reuse; label every reused row |
| C1 | Schema order, fixed comma-space and colon-space separators | 300 new requests |
| C2 | C1 with property order derived from F0's strict output | 300 new requests; oracle diagnostic only |
| C3 | A pinned second engine in schema order | 300 new requests, after full coverage/enforcement preflight |
| V | Strict validation of F0, then at most one C1 retry if invalid | Only routed retries are new; total cost includes both attempts |

Retain the model, quantization, context, greedy settings, output cap, thinking setting, batch,
offload, concurrency and resource guards of E0. Fixed readable separators are supported by a
model-free bundled-engine check, not yet by a full accuracy run. Record every changed grammar option.
A second engine may share the same key-order restriction, so C3 alone cannot answer the order question.

## Oracle rules and verification required before C2

- Use only the order and named tool in that request's F0 output, never gold values or the gold tool.
  Reorder only the named tool's constraint branch; do not reorder catalog branches or prune alternatives.
- At each object, observed declared properties come first in observed order, followed by unobserved
  declared properties in original order. Preserve every assertion and required list.
- Recurse through properties and every combinator branch without choosing a branch. For homogeneous
  array items, use the first element's order and flag disagreement as `oracle_incomplete`; define tuple
  arrays explicitly before execution. The current audit helper does not implement these general rules.
- Invalid, wrapped or truncated F0 outputs fall back to original schema order. Record `oracle_not_applied`
  separately from failure classes and keep all 300 units in the primary comparison.
- Key-sorted serialization of the schema before and after reordering must be identical, including
  assertions and array order. Check original/raw validity and exact-engine acceptance independently.
- External review reports 250/252 order-rejected free-correct values reachable after its oracle rule;
  two T062 cases involve required-but-undeclared id. Verify with the bundled binary and report exceptions;
  do not add a property or relax the schema to make the oracle pass.

C2 is an optimistic diagnostic: exposing F0's observed order can steer the model toward its free answer.
It is not a deployable oracle or proof of a universally order-insensitive decoder.

## Strict deployment router and cost accounting

V sees only strict JSON parsing (reject wrappers, duplicate keys and nonfinite constants), exact
envelope shape, named-tool catalog membership and the selected tool's original raw-schema validity.
No gold values, semantic correctness or gold-tool identity may influence routing. Keep format assertions
consistent with the frozen evaluator. A failed retry is final; do not loop until success.

Score every unit. Sum both attempts' latency and tokens on routed units; report prompt caching policy,
reused versus fresh timings, and scheduled execution order. A stored-row replay is a projection, never
measured deployment latency or a fresh inference result.

The strict-router replay using C0 as retry was independently checked locally against saved E0 rows:

| Slice | Free E2E | Replay E2E | Routed | Total-token ratio | Summed recorded-latency ratio |
|---|---:|---:|---:|---:|---:|
| Raw select | 85.5% | 88.5% | 18/200 | 1.107 | 1.270 |
| Raw fixed tool | 85.0% | 89.0% | 14/100 | 1.204 | 1.519 |

Four wrapped outputs per slice are free-correct under the lenient evaluator but routed by this strict
contract. Lock that parser choice before inference; do not change it after seeing retry outcomes.

## Analysis, stopping and unresolved launch decisions

- Proposed co-primary select-pooled contrasts: C2 minus C1 (order intervention) and V minus F0
  (deployment). Use paired exact McNemar and catalog-replicate bootstrap intervals. Predeclare
  multiplicity control for the two primary tests and the secondary family before launch.
- Secondary: C1 minus C0, C3 minus C1, C2 minus F0; describe remaining formatting/engine differences.
  Keep all-pair outcomes primary. Conditioned both-finished tables are descriptive only.
- Report correct, cd_truncated (between tokens versus inside string), lookalike_key, valid wrong value,
  wrong tool, invalid output and engine refusal. Define precedence and retain overlapping diagnostic
  flags. `oracle_not_applied` is an intervention-status flag, not necessarily a model error.
- Add and test look-alike-key reporting before E0b: an undeclared key normalizing to a declared one,
  or a typographic quote in an undeclared key. Do not silently rename keys or re-score frozen rows.
- A fixed run size, no interim accuracy looks and stop-on-engine-fault are required. Normal memory
  pressure, no sustained active swap writes and nominal/fair thermals remain admission guards.
- The suggested order-effect gate is at least +8 points with an interval excluding zero. Lock the
  exact inferential rule and acknowledge the small number of independent intents before execution.

**Budget must be corrected before launch:** 900 new C1/C2/C3 requests + 30 proposed determinism requests
+ 32 retries projected by the frozen router = about 962 requests, excluding preflight/smoke. A 950
hard cap cannot cover that plan. The determinism sample must specify whether 30 means total requests
or 30 units per arm; the latter raises the count again. If reuse fails, rerunning F0/C0 adds 600 requests.
Freeze a sufficient budget and a separate preflight/smoke allowance before any E0b model work.

Pin C3's actual backend/version and serialization; preflight all 70 envelopes, schema-ordered gold
reachability and acceptance of original F0 order. Declare unsupported envelopes before inference.
Never treat refusal or silent fallback as a model error. A more general order-insensitive matcher
remains a research proposal; no support or complexity claim is established here.

This file records the review's design and known launch gaps. A locked machine-readable config,
tested routing/oracle code, determinism receipt and successful preflight are still required.
