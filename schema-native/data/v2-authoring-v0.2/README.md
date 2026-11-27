# v0.2 request revision and fresh review

**2026-11-25. Provisional authoring only. No approved test tasks or model campaign.**

This version applies the joint [adjudication](../../analysis/v2-authoring-review-v0.1/ADJUDICATION.md)
without rewriting v0.1 drafts, gold, catalogs, review evidence or its source manifest. The original
reviewer has now seen gold and is not blind to this lineage in the same context. A fresh first solve
is still needed. T033 and all descendants remain development-only; no other eligibility is certified.

## What changed

- All 32 parent tasks have explicit revision records and new opaque V2B task IDs. There are 24
  wording revisions, three ambiguity repairs, two answer-contract revisions, one request-contract
  revision and two unchanged controls. These remain **32 intent lineages, not 64 independent tasks**.
- The email body is quoted, the chart asks for one update with two series, the restaurant request
  drops undocumented per-person/inclusive semantics, and unnecessary wrapper/default hints are removed.
- Poll gold drops both optional votes arrays. Quiz gold drops numberAnswers, minCorrectAnswers and
  maxCorrectAnswers. **Only these two gold answers change**; all 32 new golds validate against the
  unchanged raw schemas. No source-schema bug or coverage gap is "fixed" by changing an API.
- `SYSTEM_POLICY.txt` explicitly tells the eventual model to omit unrequested optional/default fields.
  It is included in each fresh-review record. This is a prospective v2 contract, not an amendment to
  E0/E0b or permission to start E1. Later compared systems must receive the same policy.
- New five-tool catalogs cap each tool at three appearances **as a distractor**, or 9.375% of the
  32 catalogs. Author-nominated near misses are reserved before adjacent/lexical fill candidates.
  **Ten catalogs still lack two nominated near misses**, and no near-miss nomination is independently
  verified. This gate remains failed; the heuristic does not prove the pool cannot supply better ones.

The shortfalls are T012, T016, T033, T049, T064, T105, T232, T237, T243 and T254. Generic domain-adjacent
tools are not counted as close competitors simply to meet a quota. A fresh reviewer should check all
nominations, including the other 22 catalogs. These are review catalogs, not final 5/20-tool catalogs.

## Original wording controls: interpretation limits

`pairs.jsonl` retains the exact v0.1 request and gold beside each new version. Each pair receives
the **same new catalog and same policy**. The old Claude solve is not a fresh result under that changed
context and is never reused as one. The original versions are called original-wording controls;
not every original contains a hint, and two requests are deliberately unchanged.

An aggregate old-versus-new score gap would **not** directly isolate scaffolding:

- Poll/quiz change the answer obligations; restaurant changes an unsupported request qualification.
- Email/chart/badges repair ambiguity, rather than changing only a schema hint.
- Even the 24 same-gold wording candidates also change clarity, length or lexical overlap. They need
  independent semantic review before a narrower hint-only interpretation is justified.

Thus the safe prospective label is **paired wording sensitivity under fixed context**, with revision
types reported separately. No score gap or pure scaffolding effect has been measured. The separate
keyword track remains absent: target coverage is still two $ref, one allOf, no target oneOf/anyOf,
conditionals or patternProperties. This authoring batch is not a hard-schema stress dataset.

## Prospective extra-default diagnostic

`sn.v2_revision.diagnose` reports `valid_extra_default_fields` only when the call is raw-schema-valid,
selects the right tool, and removing the additional default-valued fields makes the arguments equal
to gold. It retains an overlapping extra-default flag when another mapping error exists, but that
mixed case remains valid_wrong_value. A raw-invalid call cannot become a default-only error.

The diagnostic currently recognizes **directly declared root properties only**, covering this batch's
camera NetworkSpeed example. It does not claim general default analysis through refs, combinators
or nested schemas. This limitation is explicit in every diagnostic record. Extend and review it if
a future campaign requires broader coverage; do not infer no default issue from unsupported scope.
Frozen E0/E0b taxonomy, scores and rules are untouched. Numbers compare by mathematical value,
booleans are distinct from numbers, object order is ignored and arrays/strings/keys are not repaired.

## Reproduction

From schema-native/, using the existing pinned schema checkout and environment:

```bash
.venv/bin/python -m sn.v2_revision audit --check
.venv/bin/python -m sn.v2_authoring audit --check
.venv/bin/python -m pytest -q tests/test_v2_revision.py tests/test_v2_authoring.py
```

`audit` without --check regenerates **only v0.2** derived artifacts from revisions.jsonl, nominations
and policy. Parent input hashes are verified before use. The source files are not regenerated.

Export a fresh, local ZIP without author gold, parent IDs, pair metadata or near-miss labels:

```bash
.venv/bin/python -m sn.v2_revision export-review --out /tmp/v2-authoring-v0.2-blind-review.zip
```

It refuses an existing output path. Give only that ZIP to a reviewer who has not seen the gold, or
an isolated context without gold-bearing history/retrieval; disclose prior exposure rather than
claiming a reset alone proves blindness. Do not send the PR or private revision files first.

After preserving a new solve and notes, compare them locally:

```bash
.venv/bin/python -m sn.v2_revision check-review \
  --responses /tmp/v0.2-answers.jsonl --reviewer fresh-reviewer-name \
  --out /tmp/v0.2-review-comparison.json
```

Agreement is not automatic approval, proof of independence or a Qwen evaluation result. Revised
ambiguities must be fixed or have accepted alternatives specified **before** a model campaign.
No inference, training, model download or new native engine-capability probe is part of this version.
The 800/200-intent target, wider family/source audit and final experiment contracts remain future work.
