# E0b: separate order effects from deployment performance

**LOCKED — 2026-11-14 (Asia/Kolkata), protocol e0b-locked-v1.** Base: main 45e786b.
Machine-readable definitions: configs/runs/e0b.json and e0b_smoke.json. No E0b inference has run.
E0 rows and experiment/ remain immutable. E1/E2 stay gated. This locks the design, not a claim that
all backend capabilities have passed: see analysis/e0b-readiness/VALIDATION.md for the C3 launch gate.

## Conditions and fixed budget

Raw representation only, the same 300 units: 200 selection (5/20 tools) and 100 fixed-tool argument
units. The approximately **50 intents**, not 300 units or 1,000 requests, are independent.

| Arm | Condition | Status |
|---|---|---|
| F0 | Original free decoding | Reused after the 30-request determinism gate |
| C0 | Original llguidance, schema order, flexible whitespace | Reused after the same gate |
| C1 | llguidance, schema order, fixed readable separators | 300 new requests |
| C2 | C1 with property order from that unit's F0 output | 300 new requests; oracle diagnostic only |
| C3 | Pinned llama.cpp GBNF Jinja response_format autoparser, schema order | 300 new requests, subject to capability gate |
| V | Strict validation of F0, then at most one C1 retry if invalid | Up to 70 new retries, all units scored |

**Hard cap: 1,000 benchmark generation requests = 900 C1/C2/C3 + 30 determinism + up to 70 retries.**
A **separate shared allowance of 60 generation requests** covers online preflight and smoke together.
Both use one durable campaign ledger. A reservation is written and synced before sending; failures
and uncertain in-flight attempts consume budget and are not automatically retried. Importing reused
rows is not a model request. Health/props, template rendering and tokenizer API calls do not generate
output and are recorded separately from these generation budgets. No server/model is started by code.

The frozen strict router projects 32 retries, hence 962 benchmark requests; the unused 38 requests
are not an adaptive exploration allowance. More than 70 routed units is a STOP condition, never a
reason to omit units. The path smoke has six units (T106_p0 and T103_p0 across 5/20/fixed-tool),
18 C1/C2/C3 requests and 3 V retries. Six adversarial requests plus this smoke total 27 of the 60.
Smoke is not benchmark accuracy evidence and does not authorize baseline reuse.

Retain Qwen3-1.7B Q8_0, context 8192, batch 512, microbatch 128, all 29 GPU layers, one request at a
time, greedy seed 0, thinking disabled, output cap 512 and two-second pacing. Keep memory/swap/thermal
guards. Record json-fixed-readable-v1: whitespace_flexible=false, item_separator=", ", key_separator=": ".
These restrict output serialization, not JSON value assertions or prompts.

## Determinism gate — final

**30 requests total: 15 F0 and 15 C0.** Independently rank each arm's 300 source request keys by
SHA-256(seed + NUL + source_request_key), ascending; take the first 15 in each arm. Seed:
e0b-lock-2026-11-14-v1. Selection is made and published before any model run in
analysis/e0b-readiness/determinism-selection.json. No scores influence selection.

Pass only if **all 30 raw_content strings are byte-identical in UTF-8** to E0. Do not trim, normalize,
or compare parsed values. Any mismatch, engine fault or malformed response: save the attempt, write
a STOP record, and STOP. Do not auto-rerun F0/C0 or consume the spare budget to try again. Report the
failure for a new protocol decision. Reuse has this bounded reproducibility check, not proof of
identical behavior on all other units. Reused rows/timings are explicitly labeled.

## Strict router — final

sn/router.py accepts only raw text, the current catalog's name-to-original-schema mapping and a
truncation flag. It has no access to gold values, gold tool identity or evaluator fields.
Reject wrappers, duplicate keys at any depth, NaN/Infinity and non-finite numeric overflow. Require
exact tool/arguments envelope keys, a named tool in the current catalog and raw-schema validity for
that named tool. Format assertions remain disabled as in E0. Truncated free outputs route to retry.
Semantic correctness and the gold tool never affect routing. A schema-valid wrong answer is not retried.

At most one C1 retry; a failed retry is final and counted. V costs sum free plus retry tokens and
recorded latency for every routed unit, with reuse labels. A stored-row replay is a projection,
not measured deployment latency. Using stored C0 as retry projects 88.5% select and 89.0% fixed-tool,
with 18/200 and 14/100 routed. Four wrapped free-correct outputs per slice route under this strict
contract; that choice is final and is not revised after observing retry outcomes.

## Oracle C2 rules — final

Use only F0's strictly parsed named tool and observed key order for the same unit, never gold data.
Only that tool's envelope branch is reordered; catalog/tool branches are neither reordered nor pruned.
Observed declared properties first in observed order; unobserved declared properties follow in their
original order. Preserve every assertion, property, required list and list/branch order.

Recurse through properties and **every** allOf/anyOf/oneOf/not/if/then/else branch without selecting or
pruning a branch. For homogeneous arrays the first element supplies items order. If later elements
disagree in nested object-key order/shape, retain first-element order and flag oracle_incomplete.
For tuple arrays, reorder each position from its corresponding observed element; absent positions
remain in original order. Prefix-items and additional homogeneous tails follow the same rules.
**No tuple arrays were found in the 70 frozen envelopes**; tuple behavior is covered by synthetic tests.

Invalid, wrapped, truncated or out-of-catalog F0 output: preserve schema order and flag
oracle_not_applied. Required keys stay required; unknown observed keys do not become declared
properties. Key-sorted serialization of the complete constraint copy before/after must be identical.
Test validator verdicts on gold and stored F0 values; separately test exact-engine acceptance.

C2 is an optimistic oracle diagnostic, not a deployable baseline or a universal order-insensitive
matcher. The all-representation compatibility check is distinct from E0b's raw-only denominator:
499/501 strict free-correct values reachable; among the previously order-rejected subset, 250/252.
Both exceptions are T062_p0 (select C005_R03 and fixed-tool), involving required-but-undeclared id.
Do not relax schemas to pass. Raw-only F0: 246/248 strict free-correct values reachable under C2.

## C3 — one fixed backend and serialization

**llama.cpp 11fe02151f79c41d0d4af7da708755d73b9c0da6, native GBNF through response_format with --jinja.**
Use the unchanged corrected constraint schema (no x-guidance options), pinned native GBNF defaults,
and its actual Jinja/autoparser wrapper serialization. The server default reasoning format is deepseek;
enable_thinking=false. The model's recorded chat template is SHA-256 pinned in config. The native
check invokes the same template/autoparser implementation, primes the grammar with its generation
prompt as common/sampling.cpp does, and uses the actual GBNF matcher libraries. This is not a claim
of equivalent model-tokenizer behavior; that remains an online gate. Helpers load no model or server.

All 70 envelopes are checked before inference. Compile success alone does not establish enforcement:
record schema-ordered gold reachability and validator-rejected mutation witnesses. Publish every
unsupported/failing envelope in the config and readiness evidence before any run. **The full run
must STOP before network generation if any C3 envelope fails coverage/enforcement.** No silent
exclusions, second-backend substitution, schema relaxation or automatic version upgrade is permitted.
Resolving a backend capability deficit requires an explicit protocol revision, not an opportunistic run.

## Analysis and failure taxonomy — final

Co-primary tests on pooled selection, paired exact McNemar, replicate-bootstrap 95% intervals:
P1 C2 minus C1; P2 V minus F0. **Holm across these two tests.** Secondary pooled-selection tests:
C1 minus C0, C3 minus C1, C2 minus F0, with a **separate Holm family** of three. Argument generation
and catalog-size tables are descriptive; no undeclared extra significance tests. Keep all pairs in
primary outcomes; both-finished subsets are biased descriptive summaries only.

**Order-effect rule: C2 minus C1 >= +8 percentage points and the replicate-bootstrap 95% interval's
lower endpoint > 0 on pooled selection.** Report adjusted p-values too. Acknowledge the roughly 50
independent intents and limited power. Fixed size; no interim accuracy looks. Stop on any engine fault.

Exclusive precedence:
**engine_refusal > cd_truncated > invalid > wrong_tool > lookalike_key > valid_wrong_value > correct.**
Keep overlapping flags in separate columns, including oracle_not_applied and oracle_incomplete;
these oracle statuses are not automatically model failures. Report truncation inside versus outside
strings where it can be identified. Look-alike flags use an undeclared key whose NFKC-normalized,
trimmed, case-folded form matches a declared key, or a typographic quote in an undeclared key. They
never rename a key or re-score an E0 row. Preserve the historical E0 metrics alongside new flags.

## Execution gates and commands

Model-free preparation/validation (safe now; no model/server):

```bash
bash scripts/build_gbnf_audit.sh
scripts/build_native_audit.sh
python -m sn.e0b_readiness
python -m pytest -q --ignore-glob='* 2.py'
```

After the documented native C3 capability gate has been resolved under a new approved protocol,
and only when inference is explicitly authorized, use a new e0b- campaign ID with an already
running pinned server. sn.e0b_preflight performs the shared-budget online checks/smoke and issues
a receipt; sn.run requires that receipt before the 30 determinism requests. It never starts a server.
A failed determinism check writes STOPPED.json and prevents auto-resumption. Uncertain charged
requests require inspection; no automatic replay. Reports are generated by sn.e0b_report.

For this task, **STOP after the code/tests/evidence PR. Do not start E0b. E1/E2 remain gated.**


## Amendment 1 — 2026-11-14 IST, before any E0b inference

This amendment supersedes conflicting execution rules above. **The original locked text above is
preserved byte-for-byte.** Each JSON config also embeds its exact original locked text before its
amendment record. No E0b inference, online preflight, smoke or determinism request has run.

### C3 exclusion and retained engine finding

Remove C3 and secondary contrast C3 minus C1 from E0b. The pinned GBNF backend failed the pre-declared
capability gate: **30/70 envelopes**, **246/300 schema-ordered gold calls reachable**, and **120/6,696
validator-rejected witnesses accepted**. It also shares the key-order restriction and cannot inform
either co-primary contrast. Do not substitute another backend or run C3 on a subset.

All original C3 evidence stays published in analysis/e0b-readiness/native-original-lock.json and
VALIDATION-original-lock.md, explicitly labeled a **model-free engine finding**, not E0b inference.
Its SHA-256 is pinned in both amended configs. The amended readiness command does not rerun C3;
it verifies the historical evidence hash and evaluates active C1/C2/V capability only.

### Amended budget, smoke and ordering

- Active arms: F0 and C0 reused after the unchanged determinism gate; C1, C2, then V.
- **Hard cap: 700 benchmark requests = 600 C1/C2 + 30 determinism + up to 70 retries.** The frozen
  router currently projects 32 retries, for **662** new benchmark requests. Spare capacity is not
  an exploration allowance. Failure/uncertain attempts still consume budget.
- The **shared preflight/smoke allowance remains 60**. Remove every C3 readiness request: four
  C0/C1 adversarial probes + 12 C1/C2 smoke requests + three V smoke retries = **19/60** planned
  generation requests. No replacement backend or extra arm is introduced.
- Freeze the original seed and the exact same **15 F0 + 15 C0** selections. All 30 raw_content
  values must match UTF-8 bytes. First mismatch writes STOPPED.json and stops, with no baseline rerun.
- After online preflight/smoke and all 30 determinism checks pass, import the reused baselines,
  complete **all 300 C1 requests, then all 300 C2 requests, then V retries**. No interim accuracy looks.
- Resource guards, the unchanged E0 model profile, output cap, router parser, oracle rules and
  failure precedence remain as locked above. No E0 rows or experiment/ files are changed.

### Analysis and expanded look-alike diagnostic

Co-primary family is unchanged: P1 C2 minus C1 and P2 V minus F0, Holm across two tests.
The **secondary Holm family has two tests only: C1 minus C0 and C2 minus F0**. There is no C3 contrast.
The +8-point order rule and replicate-bootstrap interval rule remain unchanged, with about 50
independent intents. Keep historical scores and all-pair outcomes; diagnostic flags do not re-score rows.

In addition to the existing NFKC/trim/casefold and typographic-quote rules, flag an **undeclared key
starting with a nonempty declared key followed by a non-alphanumeric character**, using the literal
prefix and Python Unicode isalnum boundary. Example: `parent_id": "r-101", `. Exact declared keys
are not flagged by this new rule; alphanumeric continuations such as parent_idx or parent_id2 do
not qualify. Punctuation, spaces and underscores are non-alphanumeric. No key/value is renamed.
Re-report counts on frozen E0 rows only as diagnostic flags.

### Review and execution authorization

**STOP after model-free verification, tests, documentation and pushing PR #5 for review.** Do not
load a model, run inference or train in this amendment work. Only after the user explicitly confirms
review may the existing model profile be loaded for: (a) budgeted online preflight/smoke,
(b) the frozen 30-request determinism check, and, only on an exact pass, (c) C1, C2, V and the final
sn.e0b_report readout under the 700 cap. Native capability passing does not authorize model work.
E1/E2 remain gated.
