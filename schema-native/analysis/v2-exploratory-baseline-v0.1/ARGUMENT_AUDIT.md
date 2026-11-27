# Exploratory v2 argument audit

The offline audit on 2026-11-27 reproduced the scores for all 177 saved responses
across 93 intents. Its largest actionable finding is incomplete or excessive argument
selection. Of the 44 calls that chose the right tool and passed its schema while
missing the expected call, 39 added a field, omitted a field, or did both.

| Difference from the expected arguments | Calls | Distinct intents | API intents with the difference at both catalog sizes |
| --- | ---: | ---: | ---: |
| Added field | 26 | 18 | 8 |
| Omitted field | 22 | 18 | 4 |
| Changed value at an existing field | 7 | 6 | 1 |

Rows overlap. Nine calls added and omitted fields, sometimes placing the requested
value under a different valid key. Request text review found omissions of limits,
filters and flags the user asked for. Six calls added at least one value that matched
a directly declared schema default. Matching an annotation does not establish why
Qwen emitted the value. One intent produced 58 of the 96 added fields across its
two catalog sizes, which illustrates why the table counts intents as well as calls.

The 24 calls with schema-invalid arguments covered 19 intents. The validator reported
`pattern` for four calls and `additionalProperties`, `enum`, `maxProperties`,
`required` and `type` for three each. A call can violate several keywords.
Across all 76 wrong calls, 48 passed the schema of the emitted tool, including four
that chose the wrong tool. A retry triggered solely by validation failure would miss
those 48. Grammar reachability and retry accuracy remain separate questions.

## Candidate development test

The baseline policy already asks Qwen to preserve requested values and omit
unrequested defaults.
Try one focused second pass that reviews the first call against the original request
and the selected tool's visible schema. Keep the tool fixed. Ask the review to include
stated filters, limits and flags, use the declared field names, and remove values that
have no support in the request or a schema requirement. Keep the expected answer
outside inference.

Use all 11 calls from the separate [API development pilot](../v2-dev-free-v0.1/PILOT_RESULTS.md),
where the first pass already completed and two recorded errors cover omitted and
extra arguments. Compare each revised call with its saved first call. Record exact
corrections, regressions, prompt and completion tokens, and added latency. This is a
development check against known mistakes. The previous
[checklist experiment](../v2-keyword-repairs-v0.1/RESULTS.md) left all 32 stress outcomes
unchanged, so the candidate needs a measured gain to justify its extra call.

The [measured development comparison](../v2-argument-review-v0.1/RESULTS.md)
completed all 11 reviews. Exact accuracy stayed at 9/11 with 32.0% more tokens.

## Verification

The audit checks the frozen manifest, response ledger, validator version and scorer
files against their pinned hashes. It reproduces the original private score byte for
byte before counting differences. It compares object keys recursively and compares
arrays as whole values under the frozen equality rule. A missing parent counts as
one missing field. Direct default matching follows `properties` without resolving
references or branches.

From `schema-native/`, use a new destination to reproduce the
[aggregate](argument-audit.public.json):

```bash
umask 077
audit_dir=$(mktemp -d)
.venv/bin/python -m sn.v2_exploratory_audit \
  --freeze ../../../outputs/v2-exploratory-freeze-v0.1 \
  --responses runs/v2-exploratory-free-v0.1/results.jsonl \
  --out "$audit_dir/argument-audit.json"
cmp "$audit_dir/argument-audit.json" analysis/v2-exploratory-baseline-v0.1/argument-audit.public.json
```

The published audit contains counts and hashes. Requests, responses, expected
arguments, field names and per-intent findings stay private. The audit ran with zero
new inference requests. The aggregate reproduced byte for byte, and a changed copy
of the ledger was rejected before audit output. All 275 tracked tests passed
(255 package, 12 original evaluator and eight power-planning). E1 and E2 stay gated.
