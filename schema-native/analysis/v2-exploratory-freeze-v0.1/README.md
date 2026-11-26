# v2 exploratory dataset freeze

The exploratory dataset was frozen on 2026-11-27 from the
[three private candidate tranches](../v2-holdout-candidate-c-v0.1/README.md).
The sealed local manifest SHA-256 is
`837044af132bd981996749cef38509fa7056566be472b14ccaec1946d70ac7f6`.
This locks the data and scorer. A separate reviewed campaign is required for model requests.

| Track | Intents | Size 1 | Size 5 | Size 20 |
| --- | ---: | ---: | ---: | ---: |
| API tool calling | 69 | — | 69 | 60 |
| Assertion pairs | 17 | 34 | — | — |
| Description-grounding pairs | 7 | 14 | — | — |
| Total | 93 | 48 | 69 | 60 |

The 177 rows cover six reserved API source groups and 24 stress pairs. Each pair contributes one
intent. The matched catalog-size comparison covers the 60 API intents with both sizes.
The earlier API tranche contributes nine additional five-tool intents. Each five-tool view
is an ordered subset of its 20-tool view where both exist.

The freeze uses the reviewed revisions from each tranche. It preserves the four pre-existing
lineage holds and adds one wording hold for an exact-case search filter that has an unreviewed
clarification. An earlier search revision had already fixed phrase syntax in the expected call.
The five excluded cases retain their original reviews and stay outside the frozen roster.
All selected tasks have a saved gold-blind answer matching the chosen expected call exactly.

The receipts of the prior Claude review and follow-up for tranche A were rechecked. That
reviewer reported that personal context was loaded. The other first solves came from isolated
Codex contexts. These establish reviewer agreement on the visible contracts and do not measure
difficulty for Qwen, coverage of live endpoint behavior or absence from base-model pretraining.
The final roster is for exploratory use. Confirmatory approval remains at zero intents.

## Locked artifacts and scoring

- `inference/requests.jsonl` holds request IDs, policy, catalogs, visible requests and offline
  token counts. It contains no expected answers or scoring metadata. The HTTP message renderer
  uses the task policy, request and catalog only.
- `scoring/expected.jsonl` holds the reviewed calls and analysis strata. Source, lineage and
  exclusion files also stay in the scoring directory.
- `manifest.json` pins both directories, original and revised data/review receipts, the profile,
  template, tokenizer, validator and scoring implementation. The ordered request keys are
  selected by a fixed seed. A restage or prompt change needs a new release.
- The scorer requires the full response ledger in the frozen order. It reports intended-tool
  accuracy, validity against the emitted tool's raw schema and exact-call accuracy separately.
  It averages exact accuracy within each intent and reports tracks separately, plus pair success
  and the matched 5/20 comparison. JSON objects compare by contents, arrays and strings compare
  exactly, numeric values compare numerically, and booleans stay distinct from numbers.
- A schema-valid wrong call on the intended tool can carry an omitted-expected-key flag and a
  narrower flag if the missing key's expected value equals its schema default annotation.
  These flags record omissions. Whether a case reflects a benchmark policy, the user's
  requested meaning, or both requires its adjudicated task context.

One expected call is frozen per retained row. Future multiple-answer contracts need a
versioned and reviewed equivalence rule. Validation alone cannot decide semantic equivalence.

## Context and launch boundary

Compact serialization preserves the reviewed catalog contents and order. Offline prompt counts
are 202–7,792 with a 512-token output reserve under the 9,216-token profile. All 177 rows fit.
The tokenizer reproducer matched the 87 saved live calibration lengths. This turn generated zero
Qwen responses. Online context checks, resource admission and the untuned baseline are pending.

A first campaign proposal uses one free-decoding attempt per request, a hard cap of 177
generation requests and an exact online tokenizer check before generation. It needs its own
run identity, resource and stop rules, budget and source-bound approval. Keep the frozen
examples out of prompt and training development. E1/E2 remain gated.

## Research decisions informed by the review

The frozen exploratory baseline can measure available headroom without waiting for the proposed
confirmatory set. Any authoring or prompt changes guided by model outputs belong on development
material kept outside the frozen set. Use separate breakdowns for schema invalidity, schema-valid
wrong values, description-grounding failures and omitted requested values.

The Stripe development miss omitted the requested limit of 5. That tool's description gives 10
as its default. The raw schema allowed the omission, so this is evidence about fulfilling the
request, with no failure of the static schema assertion. The E0b free-first router is a useful
comparator on schemas where its retry backend passes the capability gate. A larger untuned model
is another comparator. Whether it matches a tuned 1.7B system remains a separate measurement.

## Reproduce privately

```bash
umask 077
.venv/bin/python -m sn.v2_holdout_freeze check \
  --outputs /private/outputs --tokenizer /private/qwen-tokenizer.json \
  --out /private/v2-exploratory-freeze-v0.1
```

The offline scorer was exercised with a synthetic completed ledger containing the reviewed
answers. All 177 rows and all expected track and pair counts reproduced. Synthetic answers
were only a software check.

All 265 tests passed (245 package, 12 original evaluator and eight power-planning).
