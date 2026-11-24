# Design review and first authoring tranche

**2026-11-25. Author self-review, not an independent approval.**

The user instructed continuation after PR #7. Candidate authoring and model-free checks are now
in scope. Dataset freeze, model work and training remain gated; main and E0/E0b are unchanged.

## Design clarifications applied

1. **Untargeted is not never presented.** Actual historical catalog metadata shows 100/250 untargeted
   tools appeared as distractors in corrected E0 and 246/250 in original full-v2. Such exposure did
   not update model weights. It is separately tracked rather than silently called training leakage
   or erased to support an unseen-schema claim.
2. **Known family sibling is not a test holdout.** T033 is a new target but shares calendar_event
   with a v1 target. It is marked development-only. Other tools have not been cleared by a full
   lineage/source audit merely because exact schema hashes do not match.
3. **Validation is not independent semantic review.** All 32 draft golds validate, but zero tasks
   are independently approved. A blind packet and an agreement checker are supplied; the checker
   cannot certify reviewer independence or promote tasks.
4. **Source provenance/licences stay unresolved.** All 250 source groups/licences remain unverified
   for v2. Only declared source URIs and collection identity are recorded. No raw schema was newly
   copied into Git, and no outside source holdout is claimed.
5. **Task count is not sample size achieved.** Thirty-two author-selected drafts are a first tranche;
   218 pool tools remain unauthored, and no locked test intents exist. The provisional 800/200 goal,
   family clustering, calibration, wider stress pairs and complete cost protocol remain future work.

## Current evidence

The deterministic audit, tested against the actual draft source, reports:

| Check | Result |
| --- | ---: |
| Pool / existing target tools / new candidates | 300 / 50 / 250 |
| Candidate strata | 149 flat / 101 structured |
| Authored drafts / raw-schema-valid golds | 32 / 32 |
| Draft strata | 18 flat / 14 structured |
| Existing deterministic request-leakage findings | 0 |
| Exact canonical schema matches to legacy trainpool | 0 |
| Exact canonical schema matches to 21 exposed stress cases | 0 |
| Independently reviewed / accepted test intents | 0 / 0 |
| Native engine checks / additional model endpoint requests / training runs | 0 / 0 / 0 |

The external bundle hash matches `8bb8ab2ac1553bf7bc3ae068e615e23d776ddb0a8c2550d4cde82e206fad1132`.
Only its JSON was read to inventory IDs and hashes; no bundle code or engine probe was executed.
Historical output scores were not used to select this batch; exposure reads catalog IDs only.
The prior power analysis and historical interpretation were not recomputed or changed.

## Verification and remaining review

See [authoring instructions](../../data/v2-authoring-v0.1/README.md) for reproducible audit and blind
review commands. Targeted tests cover gold validation, parser strictness, numeric/object/array
comparison, hidden gold fields, deterministic catalogs, immutable inputs, review coverage,
unresolved disagreements, blocked self-approval, explicit dialects, blocked remote references and
honest inventory states. They are code checks, not independent answers to the 32 tasks.

**193 tests passed:** 173 package tests (158 existing plus 15 authoring cases), 12 original evaluator
tests and eight standalone power-planning tests. Both authoring and power artifacts reproduce
with their respective --check commands; git diff whitespace checks pass. Frozen experiment/,
E0/E0b publications, existing runtime code and configs remain unchanged.

The next required outside evidence is a preserved blind solve plus ambiguity notes from another
reviewer, followed by adjudication. Broader structural/renamed/request/source lineage checks and
the per-schema provenance/licence audit remain open. This report does not mark PR #7 or a dataset
as independently approved and does not authorize inference or E1/E2.
