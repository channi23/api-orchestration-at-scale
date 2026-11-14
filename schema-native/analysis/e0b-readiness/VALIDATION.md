# E0b readiness validation

**2026-11-14 IST: protocol LOCKED; launch BLOCKED by C3 capability failures.**

No model was loaded, no inference or training ran, and no E0 data or experiment/ files were changed. These are stored-row, validator and native matcher checks, not measured E0b results. E1/E2 remain gated.

## Implementation and locked decisions

- Base main: 45e786b; branch feat/e0b-lock. E0B_PLAN.md and both e0b JSON configs lock the procedure.
- Hard 1,000 benchmark-generation cap: 900 C1/C2/C3 + 30 determinism + up to 70 retries. Separate shared 60-generation preflight/smoke allowance. A durable reservation precedes every send; failed/uncertain requests consume budget and cannot automatically retry.
- Frozen determinism-selection.json: seeded-hash ranking, independently first 15 F0 and 15 C0. All 30 raw_content strings must match UTF-8 bytes exactly; first mismatch saves STOPPED.json and stops. No automatic full baseline rerun.
- Strict router sees raw text, catalog schemas and truncation only. No task, gold or evaluator fields. Rejects wrappers, duplicate keys, non-finite numbers/overflow, bad envelope, out-of-catalog tool and chosen-tool raw-schema invalidity.
- Oracle edits only named-tool property order, including every combinator branch. Homogeneous arrays use the first element and flag disagreement; tuples use each position. Invalid/wrapped/truncated F0 falls back. Sorted serialization, assertions, required lists and raw-validator verdicts are preserved.
- Named fixed option json-fixed-readable-v1: comma-space and colon-space separators, whitespace_flexible=false. C3 is one pinned native GBNF Jinja response_format backend, not an interchangeable engine.
- Report includes look-alike-key flags without renaming/re-scoring frozen rows. Exclusive precedence and overlapping flags are recorded. Two co-primary tests share Holm; the three secondary tests have a separate Holm family. Order gate is >=8 pp with replicate-bootstrap 95% lower bound >0; about 50 independent intents.

## Native results

| Check | Result |
|---|---:|
| C1 envelope compiles | 70/70 |
| C2 task-specific compiles | 300/300 |
| Distinct C2 serialized constraint copies | 146 |
| C1 schema-ordered gold reachability | 300/300 |
| C1 invalid witnesses accepted | 0/6696 |
| C2 invalid witnesses accepted | 0/6696 |
| C2 raw-only strict free-correct F0 reachability | 246/248 |
| Raw+minified strict free-correct compatibility | 499/501 |
| Previously order-rejected raw+minified subset | 250/252 |
| Tuple-array locations in 70 envelopes | 0 |
| C3 envelope compiles | 70/70 |
| C3 schema-ordered gold reachability | 246/300 |
| C3 invalid witnesses accepted | 120/6696 |
| C3 envelopes emitting conversion diagnostics | 12 |
| C3 envelopes failing readiness | 30/70 |
| C1: original F0 key order accepted (spaced serialization) | 137/268 |
| C3: original F0 key order accepted (spaced serialization) | 134/268 |

The 250/252 expectation concerns the earlier **raw+minified order-rejected subset**, not E0b raw-only F0. Raw-only has 248 strict free-correct calls (256 free-correct, eight wrapped); the broader check has 501 (515 free-correct, 14 wrapped). All strict values and every exception are recorded in native.json.

### Every oracle free-correct exception

| Source key | Tool | Reason |
|---|---|---|
| select|A_raw_free|C005_R03|T062_p0 | T062 | Required-but-undeclared id cannot be positioned through properties; schema not relaxed. |
| arggen|A_raw_free|single|T062_p0 | T062 | Required-but-undeclared id cannot be positioned through properties; schema not relaxed. |

Both raw-only exceptions are these same T062_p0 calls. C1/C2 have zero compile refusals. Native JSON additionally records all strict non-correct F0 acceptance results and oracle fallback/incomplete flags.

### Every unsupported/failing C3 envelope

Unsupported means failure of this locked coverage/enforcement gate, not inability to emit any valid value. All 70 compile. One extra envelope fails an incomplete-conversion warning; 29 fail gold reachability and/or bounded enforcement. All 30 names are frozen in both configs before inference.

| Envelope | Gold accepted / checked | Invalid accepted | Incomplete conversion |
|---|---:|---:|---|
| C020_R00 | 10/10 | 0 | yes |
| C005_R01 | 8/10 | 4 | yes |
| C020_R01 | 8/10 | 4 | yes |
| C005_R02 | 8/10 | 0 | no |
| C020_R02 | 8/10 | 0 | no |
| C005_R03 | 6/10 | 30 | no |
| C020_R03 | 6/10 | 30 | yes |
| C005_R04 | 8/10 | 2 | yes |
| C020_R04 | 8/10 | 2 | yes |
| C005_R05 | 8/10 | 4 | no |
| C020_R05 | 8/10 | 4 | yes |
| C005_R06 | 8/10 | 0 | yes |
| C020_R06 | 8/10 | 0 | yes |
| C005_R07 | 8/10 | 0 | no |
| C020_R07 | 8/10 | 0 | no |
| C005_R08 | 8/10 | 0 | no |
| C020_R08 | 8/10 | 0 | no |
| single:T178 | 0/2 | 0 | yes |
| single:T286 | 2/2 | 4 | no |
| single:T008 | 0/2 | 0 | no |
| single:T132 | 0/2 | 0 | no |
| single:T062 | 0/2 | 2 | no |
| single:T220 | 2/2 | 28 | no |
| single:T146 | 0/2 | 0 | no |
| single:T273 | 2/2 | 2 | yes |
| single:T055 | 2/2 | 4 | no |
| single:T089 | 0/2 | 0 | no |
| single:T152 | 0/2 | 0 | yes |
| single:T009 | 0/2 | 0 | no |
| single:T135 | 0/2 | 0 | no |

native.json includes every rejected gold unit, original-F0-order rejection, all accepted-invalid witness texts and IDs, and converter diagnostics. No schema was relaxed or unit excluded.

## Engine provenance and scope

The llguidance helper links the exact E0 bundled static library; build-time helper/library hashes are verified. The GBNF helper links the pinned libllama-common and libllama shared libraries and invokes the actual Jinja/template/autoparser implementation with the recorded Qwen template. It primes the grammar with its generation prompt as common/sampling.cpp does, using the pinned server default deepseek reasoning format with thinking disabled. Both engine checkouts must have no tracked modifications. Helpers load no weights and create no server.

- llama.cpp `11fe02151f79c41d0d4af7da708755d73b9c0da6`; llguidance `d795912fedc7d393de740177ea9ea761e7905774`.
- Static llguidance SHA-256 `fa217ef4a3e0b76db51d2ce117d98a40df9765eb73a2bca91685f45b099eef3a`.
- Shared-library/helper hashes, verification-code hashes, config hash and order-sensitive plan hash: native.json.
- 6,696 negative checks per condition are finite gold-derived mutation witnesses rejected by the original validator/router. Repeated catalog/paraphrase witnesses are not independent. This is not exhaustive schema-language equivalence or Qwen-tokenizer mask verification.
- Zero tuple-array schemas were found. Draft-7 tuple items and 2020 prefixItems behavior are covered by synthetic tests.

## Stored-row replay and diagnostic flags

| Slice | Routed | Free | C0-retry projection | Token ratio | Recorded-latency ratio |
|---|---:|---:|---:|---:|---:|
| select | 18/200 | 85.5% | 88.5% | 1.107 | 1.270 |
| arggen | 14/100 | 85.0% | 89.0% | 1.204 | 1.519 |

These are projections using saved C0 rows, not new V measurements. Actual V would make a fresh C1 retry. Four wrapped free-correct outputs per slice route under the final strict contract. Projected benchmark requests: 962; none were sent. Planned shared readiness generations: 6 adversarial + 18 C-arm smoke + 3 V smoke retries = 27/60.

Look-alike output flags: `{"A_raw_free": 0, "B_raw_cd": 6, "A2_min_free": 0, "B2_min_cd": 6}`. Rule: undeclared key matching a declared key after NFKC/trim/casefold, or a typographic quote in an undeclared key. This is not every Unicode confusable. Raw text and recorded evaluator scores are preserved.

## Tests and integrity

**80 package tests + 12 original evaluator tests passed.** Commands and excluded untouched duplicate files are recorded in TESTS.txt. Tests cover strict parsing/no gold access, named branch and every combinator, array disagreement/tuple positions, sorted-schema identity, raw-validator verdicts on 300 gold/F0 units, exact router counts, both hard budgets, stop-on-first-determinism mismatch without baseline rerun, generic-preflight bypass prevention, separate Holm families, full failure precedence, retry cost sums and frozen-row preservation.

E0 results remain 1,200 rows with SHA-256 `1e1528a8e3180e5d4d47abdcbd719d03ed0e0238fdb0c1f9c832ab3006fa8a1f`; published compressed bytes match. experiment/ and E0 analysis artifacts remain unchanged from base 45e786b. Untracked duplicate files are untouched.

## Not verified and launch status

**DO NOT START E0b.** C3 fails the declared native capability gate for 30 envelopes. Online readiness rejects that evidence before network generation or model-file access. This requires an explicit protocol/backend decision; it is not permission to drop cases, switch backend, relax schemas or spend the spare budget.

Not run: the real 30-request determinism check, tokenizer-aware online probes, live smoke, E0b inference accuracy/latency/thermal measurements, or training. Even after a reviewed native capability resolution, online checks must still pass. E1/E2 remain gated.

## Reproduce without a model/server

```bash
bash scripts/build_gbnf_audit.sh
scripts/build_native_audit.sh
python -m sn.e0b_readiness
python -m pytest -q --ignore-glob='* 2.py'
python -m pytest -q ../experiment/tests/test_evaluate.py
```

Uses the existing pinned checkout/libraries and frozen dataset; no model download, GPU model allocation or server is needed. Native helpers target the requested Apple Silicon Mac.
