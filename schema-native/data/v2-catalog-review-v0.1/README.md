# Development catalog review v0.1

Three five-tool catalogs are ready for a fresh blind solve. Each version replaces one weak
distractor with a source-backed candidate. The v0.3 request, gold arguments, policy, target
position and other tool positions are preserved. `catalogs.jsonl` records the original tool
order as a control. The packet includes only the three new catalogs, so a reviewer sees each
request once. This is a qualitative catalog review with three existing intent lineages.

| Target | Candidate | Tool removed | Distinction in the request |
| --- | --- | --- | --- |
| T254 `set_data_retention` | X001 log-group retention | T198 content owner | Lifespan of data-source objects in seconds. The candidate takes a log-group name prefix and offers a day-count enum. |
| T131 `track_calories` | X003 food quantity log | T216 Redshift storage | Daily calorie target and servings as text. X003 has numerical quantities and calories per serving. |
| T016 `set_annotation_filter` | X008 element/archive filters | T207 spatial camera filter | Regular expressions for annotation names. X008 describes element/archive lists with unspecified pattern semantics. |

The three candidate descriptions in `swaps.jsonl` use the same catalog style as existing tools.
They describe the visible source fields and do not assert a callable production endpoint. The
candidate raw schemas come from the pinned collection. The review ZIP is exported locally,
with the schemas visible to the reviewer. The original source groups, including overlaps, are
recorded in the private planning metadata.

All three target golds and three candidate examples validate under their respective schemas.
For the retention and calorie cases, only the target schema accepts its exact gold arguments
among all five tools. In the annotation case, T016, X008 and T263 (API-diff report configuration)
all accept the exact same gold arguments. X008 has `minProperties: 1` and an open root, which
allows undeclared keys to satisfy the count without an `elements` or `archives` field. T016
also accepts the X008 example as an object containing an undeclared key. These checks expose
why schema validity alone cannot choose the right tool. The reviewer should test whether the
visible descriptions and request establish a unique answer.

X003 shares the T131 Glaive function family and X008 shares the T016 Revapi project. Treat the
pairs as same-source development examples. X004 was left for a distinct dated-meal scenario
rather than adding a second calorie candidate to this one-swap comparison. X002 and X005 were
rated only related. X006 needs a model-visible representation, and X007 could supply a second
defensible answer to the current country request. Booking and scoreboard still have no new
candidate. Source licence clearance and independent review remain open.

## Reproduce

From `schema-native/` using the existing environment:

```bash
.venv/bin/python -m sn.v2_catalog_review audit --check
.venv/bin/python -m pytest -q tests/test_v2_catalog_review.py
.venv/bin/python -m sn.v2_catalog_review export-review --out /tmp/catalog-blind.zip
```

The audit and the three parent artifacts (v0.3 tasks, source candidates and keyword seeds)
reproduce. All 231 tests passed, including 211 package tests, 12 original evaluator tests and
eight power-planning tests. The exported ZIP has SHA-256
`a4d2009b7ac6576daad862f0df62e63c47a97505140ca63560402b389463d314`.

Give the ZIP alone to a fresh reviewer and collect the first `answers.jsonl` and
`REVIEW_NOTES.md` before exposing gold. The existing strict comparator can check the answers:

```bash
.venv/bin/python -m sn.v2_catalog_review check-review \
  --responses /tmp/answers.jsonl --reviewer reviewer-id --out /tmp/catalog-comparison.json
```

Only three candidates enter these development catalogs. Zero near misses have been independently
verified, and zero test intents have been approved. The benchmark runner does not consume these
catalogs. E1 and E2 remain gated.
