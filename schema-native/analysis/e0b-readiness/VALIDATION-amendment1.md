# E0b Amendment 1 readiness validation

**2026-11-14 IST: active native capability gate PASS; user review and online gates PENDING.**

No model loading, inference or training occurred. This report covers steps 1–3 only. Step 4 requires explicit user confirmation after review. E1/E2 stay gated.

## History and amendment

E0B_PLAN.md preserves its entire original locked text as an unchanged prefix, then appends dated Amendment 1. Each config embeds the exact original locked JSON text before its amendment record. Tests compare all three originals against commit 7d19bed.

C3 and contrast C3 minus C1 are removed from active arms, preflight, smoke, scheduling and secondary testing. No backend replaces C3 and no subset is run. The pinned GBNF finding remains published as **historical model-free engine evidence** in native-original-lock.json and VALIDATION-original-lock.md; neither is rewritten. Historical TESTS-original-lock.txt is also retained.

The historical C3 finding is 30/70 failing envelopes, 246/300 schema-ordered gold reachable, and 120/6,696 invalid witnesses accepted. It shares the key-order restriction and cannot inform either co-primary contrast. The archive hash is checked by amended readiness; C3 is not rerun and no longer gates the active protocol.

## Locked active protocol

- Arms: F0/C0 reused only after exact determinism pass; C1, C2, V. Expected final unit-arm rows: 1,500.
- Hard benchmark cap: **700 = 600 C1/C2 + 30 determinism + up to 70 retries**. Frozen router projects 32 retries, hence **662** requests. Reservations are durable before-send; uncertain/failed attempts consume budget and are not automatically retried.
- Separate shared preflight/smoke allowance: **60**. Planned generations: four C0/C1 adversarial probes + 12 C1/C2 smoke requests + three V retries = **19**. All C3 readiness requests are removed.
- The exact same frozen sample remains: 15 F0 + 15 C0, original seed/hash selection. All 30 raw_content UTF-8 byte strings must match. First mismatch writes STOPPED.json and stops; no baseline rerun.
- After confirmed review and passing online gates, future execution is all C1 requests, then all C2 requests, then V retries. No interim accuracy looks.
- Model profile, resource guards, strict router, oracle rules, failure precedence and co-primary Holm family are unchanged. Secondary Holm family has only C1 minus C0 and C2 minus F0.

## Re-run model-free counts

| Check | Result |
|---|---:|
| C1 compiled envelopes | 70/70 |
| C2 compiled task-specific constraints | 300/300 |
| C1 gold reachable with fixed separators | 300/300 |
| C1 invalid mutation witnesses accepted | 0/6696 |
| C2 invalid mutation witnesses accepted | 0/6696 |
| C2 strict free-correct raw F0 reachable | 246/248 |
| All-representation strict free-correct compatibility | 499/501 |
| Previously order-rejected raw+minified subset | 250/252 |
| V replay routing, select | 18/200 |
| V replay routing, fixed-tool | 14/100 |
| Tuple-array schema locations | 0 |
| Active C1/C2/V native gate | PASS |

All free-correct oracle exceptions remain the two required-but-undeclared-id T062_p0 calls: select C005_R03 and fixed-tool. No schema was relaxed. The 250/252 denominator refers to the earlier raw+minified order-rejected subset, not raw-only F0. native.json retains every active compile/enforcement and reachability result.

These are exact bundled-engine byte/character-matcher and raw-validator checks, not model-tokenizer or exhaustive language-equivalence proof. Negative witnesses repeat across catalog/paraphrase conditions and are not independent. Replayed accuracy/cost remains a stored-row projection, not fresh E0b inference.

## Expanded look-alike flags, without rescoring

In addition to existing normalization/typographic-quote rules, the new rule requires an undeclared key starting with a nonempty declared key and a literal following character that is not Unicode alphanumeric. It flags `parent_id": "r-101", `; it does not flag the exact declared key or alphanumeric continuations. It never renames a key or changes a stored evaluator field.

| Frozen E0 arm | Before | After Amendment 1 |
|---|---:|---:|
| A_raw_free | 0 | 0 |
| B_raw_cd | 6 | 11 |
| A2_min_free | 0 | 0 |
| B2_min_cd | 6 | 6 |

Total constrained flags are now 17 (previously 12). Source hash and before/after counts are in lookalike-amendment1.json. No E0 score is recomputed or rewritten.

## Tests, integrity and what remains pending

**90 package tests + 12 original evaluator tests passed.** TESTS.txt records commands. New tests cover the punctuation-prefix rule and its alphanumeric/Unicode boundaries, historical plan/config/C3 evidence preservation, rejecting the old 1,000 cap and any C3 reintroduction, the 700/60 caps and the amended two-test secondary Holm family. Existing strict-router, oracle, determinism-stop, byte-preservation and native-gate tests continue to pass.

E0 remains 1,200 rows with SHA-256 `1e1528a8e3180e5d4d47abdcbd719d03ed0e0238fdb0c1f9c832ab3006fa8a1f`; its published compressed bytes match. experiment/ and E0 analysis artifacts remain unchanged. Original locked text, C3 evidence and all 30 selected source keys/hashes are preserved.

**STOP FOR REVIEW.** Native capability passing is not online readiness or authorization to load Qwen. Online preflight/smoke, all 30 real determinism comparisons, actual E0b inference, measured latency/accuracy and thermal behavior are not run. Only after explicit confirmation may those run, in the specified order, under the unchanged E0 model/resource profile and amended budgets. E1/E2 remain gated.

## Reproduce current model-free checks

```bash
scripts/build_native_audit.sh
python -m sn.e0b_readiness
python -m pytest -q --ignore-glob='* 2.py'
python -m pytest -q ../experiment/tests/test_evaluate.py
```

Do not invoke online preflight or sn.run for this review step. GBNF is excluded and is not rebuilt/rerun by amended readiness.
