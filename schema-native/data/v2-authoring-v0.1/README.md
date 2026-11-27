# v2 candidate authoring, first review batch

**2026-11-25. Provisional assistant-authored material, not a frozen or approved benchmark.**
The user authorized candidate authoring after the draft design in PR #7. No local model was loaded,
no inference request was sent to a model endpoint and no training ran. These are drafts composed
by Codex in the current chat, not human-authored; at the initial snapshot they had no independent review.

**Subsequent review:** a self-reported blind solve of all 32 tasks has now been received and
[compared against gold](../../analysis/v2-authoring-review-v0.1/RESPONSE.md). All answers agree,
but wording/difficulty concerns remain and no test task is approved. The files and zero-review
counts below remain the original authoring snapshot; review receipt is recorded separately.

## What exists

- `drafts.jsonl`: 32 distinct request/gold drafts, 18 flat and 14 structured schemas. Every request
  supplies the intended values or documented role mapping. Gold is validator-checked against the
  unchanged raw schema, with no additional model used to generate or verify it.
- `inventory.jsonl`: all 250 previously untargeted pool tools, schema hashes, declared dialect,
  prior catalog exposure, known v1-family siblings and exact training/stress-schema overlap.
- `stress-inventory.json`: IDs and fingerprints of 20 exposed external example pairs and one
  future control; no gold values or raw schemas were copied from the bundle. This is an inventory,
  not a proof that no renamed or structurally related example overlaps.
- `manifest.json`, `validation.json`: reproducible input hashes, policy and exact counts. There are
  **zero independent reviews, zero accepted test intents and zero engine checks**.

The remaining 218 pool candidates have no draft yet. The 800-test/200-development intent goal
remains a provisional plan, not a count achieved by this batch. Pair, rename and order controls,
additional sources and the larger family-disjoint dataset have not been authored.

## Findings that affect eligibility

Of the 250 candidates, **100** appeared in catalogs actually used by corrected E0 and **246**
appeared in catalogs used by the original full-v2 experiment. Those earlier appearances were
distractors, not new training examples; they did not update Qwen's weights. Record them separately
and do not advertise these as never-presented schemas.

T033 shares `calendar_event` with a v1 target, so it is **development-only**. Other candidates are
unassigned, not certified held-out. There are no exact canonical schema matches to the 1,983-row
legacy trainpool or the external stress example schemas. This does not clear semantic, renamed,
structural, request-level or source-group overlap; those audits remain open.

All 250 original API/project source groups and schema licences are **unverified** for the intended
v2 release. We do not infer a per-schema licence from the collection README. Raw schemas remain in
the existing pinned checkout and are referenced by hash; they are not newly copied into Git.
Collection identity alone is not an API-source holdout or a permission conclusion.

This first batch was selected by the author for varied nesting, arrays, references, enum/role/unit
mapping, omissions and literal handling, without using candidate-model outcomes. It is not random,
representative, proven hard, or an independently powered sample. None of its tasks executes a real
API, sends email, accesses the fictional file paths, registers accounts or changes devices.

## Reproduce the audit

From schema-native/, using the existing lightweight environment and pinned schema checkout:

```bash
.venv/bin/python -m sn.v2_authoring audit --check
.venv/bin/python -m pytest -q tests/test_v2_authoring.py
```

To deliberately regenerate these **provisional** inventory artifacts after an authoring edit:

```bash
.venv/bin/python -m sn.v2_authoring audit
```

Validation uses the raw schema's declared draft, or explicitly labelled draft 7 when absent.
Format assertions are disabled for this legacy-pool authoring tranche, as in v1; an unknown
explicit dialect and remote reference retrieval fail closed. No schema is lowered, flattened or
relaxed. This does not resolve the future v2 format policy or demonstrate native engine support.
The existing six-word/name/identifier leakage checks are reused, not claimed as a complete leakage audit.

## Independent blind review, still needed

Give a separate reviewer **only a newly exported blind packet and the instructions below**, not
drafts.jsonl, its reasoning notes or the author gold. The packet includes each request and a
deterministic five-tool catalog with raw schemas. It contains no selected-tool field, gold, eval
fields or revealing tool ID in its task identifier. The catalog is a **review aid**, not the final
5/20-tool experiment catalog or a validated tool-confusability design. It is chosen from descriptions
and known families without consulting outputs. The reviewer must flag multiple plausible tools.

```bash
.venv/bin/python -m sn.v2_authoring export-review --out /tmp/v2-authoring-blind.jsonl
```

The export refuses to overwrite existing evidence. It includes source schemas locally so a reviewer
can solve the tasks; it is not automatically published to GitHub or another service. The source
files in this PR are public drafts, so future test-freezing must account for exposure. A reviewer
who already read the gold cannot later claim the same solve was blind.

Reviewer instructions:

1. Solve each request using only its offered tool descriptions and schemas. Return one JSONL record
   per task with exactly `task_id`, `tool` and `arguments`. Do not execute any tool.
2. Separately record ambiguity, missing information, multiple plausible calls, unnatural wording,
   undocumented mappings or an inability to preserve all requested details. Do not guess to force
   agreement. Review request meaning, not just whether an arbitrary answer validates.
3. Preserve that first solve before examining the draft gold. Then compare and adjudicate every
   disagreement. Correct the source with a versioned record; do not treat matching answers as
   proof of schema understanding or approve by majority vote.

Optional model-free comparison after the blind answers have been saved:

```bash
.venv/bin/python -m sn.v2_authoring check-review \
  --responses /tmp/v2-authoring-answers.jsonl \
  --reviewer external-reviewer-name \
  --out /tmp/v2-authoring-comparison.json
```

That command reports schema validity and agreement, refuses the author's own identity, and
**never approves tasks or verifies independence**. The reviewer's notes and provenance must still
be reviewed. Object order is ignored, JSON-equivalent numeric values compare equally, booleans
are not numbers, arrays keep order, and keys/strings are not repaired or normalized.

## Stop condition

Independent semantic review and lineage/source/licence work are required before expansion into a
frozen test set. No split freeze, online smoke, model campaign, training or cost claim is authorized
by these draft artifacts. E1/E2 remain gated.
