# v0.3 model-free verification

**2026-11-25. Provisional authoring; freeze_ready=false.**

Verified:

- Ten requests change and 22 remain as in v0.2; all 32 gold answers remain equal to v0.2 and validate
  against unchanged raw schemas. Descriptions are unchanged. The serving string is quoted with its
  original value, and the light request explicitly sets the friendly name without inventing a selector.
- Exact string/case policy with no aliases is visible in each review record; semantic enum mappings
  remain allowed. New V2C task IDs are disjoint from v0.2. Parent inputs and derived artifacts reproduce.
- Catalog tool sets and presentation order are identical to v0.2. Maximum distractor appearances
  remains three. Catalog quality is not newly verified; the prior nine clear passes remain a v0.2
  reviewer judgement, not a new v0.3 result. No task is approved.
- The seven recorded source-pool probes cover all 300 existing tools and publish matching paths,
  metadata snippets and hashes. Counts are 9/1/6/27/0/1/15 for retention, meals, booking, country,
  subtitles, scores and filters respectively. Text hits do not become near misses or new APIs.
- **214 tests passed:** 194 package tests, 12 original evaluator tests and eight standalone power
  tests. The ten new tests cover invariant gold, new IDs, unchanged catalogs, grounded ambiguity
  repairs, forbidden gold overrides, visible policy/blind serialization, rejected case aliases,
  schema-aware scans that ignore instance data, honest probes and closed approval gates.
- v0.1/v0.2/v0.3 audit artifacts and the existing power report reproduce with --check. The original
  review receipts still match every archived artifact hash. New document links and git whitespace
  checks pass. Existing untracked duplicate files were not collected as tests or modified.
- The local blind ZIP has exactly tasks.jsonl, SYSTEM_POLICY.txt and REVIEW_INSTRUCTIONS.md, with
  no gold, parent IDs or nominations. SHA-256:
  `1e3596c512b7f639ec8125c0ad5987a479170a61e9dbb1386984894dbb10fd8e`.
- experiment/, older dataset versions and review artifacts, E0/E0b publications, runtime profiles and
  request ledgers are unchanged. The new received adjudication is preserved separately. No local
  model was loaded, queried, edited or trained; no dependency installation or native engine probe ran.

Reproduce from schema-native/:

```bash
.venv/bin/python -m sn.v2_v03 audit --check
.venv/bin/python -m sn.v2_revision audit --check
.venv/bin/python -m sn.v2_authoring audit --check
.venv/bin/python -m pytest -q tests/test_v2_v03.py
.venv/bin/python -m pytest -q ../experiment/tests/test_evaluate.py
python3 -m unittest discover -s analysis/v2-design -p test_power.py -q
```

The package suite used git-tracked test paths plus the then-untracked new test explicitly; the new
test is now committed. Generated files are checked without rewriting parent versions.

Not verified: a fresh v0.3 semantic solve, unique interpretations after rewriting, actual API name
selector behavior (not asserted), genuine missing peer tools, complete upstream search, new catalog
quality, keyword stress coverage, source/family/licence clearance, dataset power, inference accuracy
or cost. Word changes do not make an independent task or prove a pure scaffolding effect. The
800/200 intent target remains unmet. E1/E2 remain gated.
