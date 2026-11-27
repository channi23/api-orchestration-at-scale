# v0.2 model-free verification

**2026-11-25. Provisional revision; readiness remains false.**

- All 32 cleaned gold answers validate against unchanged raw schemas, with the inherited explicit
  dialect/format policy and remote-reference prohibition. The existing deterministic request-leakage
  checks pass. Only poll (T039) and quiz (T213) gold change.
- Revision types: 24 wording, three ambiguity repairs, two answer-contract changes, one request-contract
  change, two unchanged controls. All are descendants of the same 32 original intent lineages.
- Every paired original/clean variant has identical new catalogs and prompt-policy hashes. None
  reuses the old blind solve as a new model result or claims an established pure-scaffolding effect.
- Five distinct tools per review catalog; maximum distractor appearances is three (9.375%). Ten tasks
  lack two author-nominated near misses; no nomination is independently verified. This gate is unmet.
- Target keyword coverage remains two $ref, one allOf, zero oneOf/anyOf/conditionals/patternProperties.
  There are zero fresh v0.2 blind reviews and zero approved test intents. No native engine checks ran.
- **204 tests passed:** 184 package tests, 12 original evaluator tests and eight standalone power tests.
  After final regex-quotation/request wording polish, all 26 authoring/revision tests passed again.
  The 11 new revision tests cover changed gold, version IDs, bounded catalog assignment and its failure,
  blind export fields, paired context, default-only versus mixed errors, boolean/number distinction,
  unsupported nested-default scope and no automatic reviewer approval.
- Both v0.1 and v0.2 audit artifacts reproduce with --check; the original power report still reproduces.
  Original review artifacts match every hash in their preserved receipt. The original authoring source,
  helper and manifest, frozen E0/E0b results/configs, and experiment/ are unchanged.
- The local blind ZIP contains only tasks.jsonl, SYSTEM_POLICY.txt and REVIEW_INSTRUCTIONS.md.
  Each task has only task_id, request, system_policy and tools, with no author gold/parent IDs or
  near-miss labels. ZIP SHA-256:
  `f6e7a5f2e7dce9bdd49d4cceb4c17a6670e2828e089b81ab9831a2358a9dd79c`.
  Prompt-policy SHA-256:
  `71cf74c503b28118f9a13ff40820a37e470843e4c8964dee1f2f5febb80cf6c7`.

Reproduce from schema-native/:

```bash
.venv/bin/python -m sn.v2_revision audit --check
.venv/bin/python -m sn.v2_authoring audit --check
.venv/bin/python -m pytest -q tests/test_v2_revision.py tests/test_v2_authoring.py
.venv/bin/python -m pytest -q ../experiment/tests/test_evaluate.py
python3 -m unittest discover -s analysis/v2-design -p test_power.py -q
```

The full package suite used the git-tracked tests plus the then-untracked new test file explicitly,
so pre-existing duplicate files named "... 2.py" were excluded. The added test is now committed.
No dependencies were installed and no model was loaded, queried, edited or trained.

**Not verified:** request uniqueness/semantics by a fresh reviewer, two genuinely close distractors
per task, the complete default taxonomy for nested/ref/combinator cases, wider source/family/licence
clearance, keyword stress coverage, power on a larger dataset, any inference accuracy or cost effect.
The 800/200 target remains unmet. E1/E2 remain gated.
