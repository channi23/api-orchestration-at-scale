# Private source-held-out candidate tranche A

**2026-11-25.** Ten new API intent drafts across two source projects. Each request has a
five-tool catalog drawn from its own source, with deterministic presentation order. The ten
operations yield nine distinct argument schemas. Five gold argument objects validate under
multiple tools in their catalogs, so those cases exercise tool selection.

The pinned sources, authoring rows, requests and gold are kept in local review storage. The
repo records the builder, its checks and the aggregate receipt. The reviewer ZIP contains
only visible task rows, instructions and upstream licence notices. Its manifest and gold are
stored separately under an owner-only directory. This is the first candidate tranche.
Independent semantic review is pending and zero tasks are approved for locked test.

## Verified

| Check | Result |
| --- | ---: |
| Source projects compared against current development owners | 2 |
| Prior schema IDs screened for indexed sources and exact schema matches | 2,288 |
| Prior indexed repository IDs / collection-only IDs | 2,002 / 286 |
| Source owner matches in the indexed history | 0 |
| Exact matches to prior schemas or 83 additional development/stress hashes | 0 |
| Exact normalized matches to 161 previous requests | 0 |
| Raw-schema-valid golds | 10/10 |
| Schema-negative witnesses rejected | 10/10 |
| Review-ready intents / locked-test approvals | 10 / 0 |

The two source projects are reserved for this candidate set. Keep them out of future training,
development and distractor pools. The origin screen is bounded by the indexes above. Forks,
undocumented collection provenance, semantic duplicates and base-model pretraining remain
unresolved. The raw hash and normalized wording screens are exact comparisons.

The projection starts from pinned OpenAPI 3.0 inputs for read-only operations. It resolves
local references, preserves declared parameter names and supported assertions, and adapts
OpenAPI nullable types explicitly. It keeps grouped query inputs as JSON argument objects and
closes the outer argument object. Format names are annotations in this audit. Wire encoding,
service-side behavior and constrained engine capability remain separate checks. No API,
model or training run took place.

## Reproduce privately

Use the pinned inputs retained with the private candidate authoring files, the original
source-index snapshot and the same Python environment:

```bash
.venv/bin/python -m sn.v2_holdout --inputs /private/authoring \
  --source-index /private/repos_fullpath.csv --out /private/new-candidate
.venv/bin/python -m pytest -q tests/test_v2_holdout.py
```

The emitted review ZIP, gold and private manifest reproduced byte for byte. All 243 tests
passed (223 package, 12 evaluator and eight power-planning). The ZIP's SHA-256 is
`74b5fdfb4b49ef7d96e79f1c96fa16a91da3b109af378d50416eb7bbf7590c0a`.
The private manifest's SHA-256 is
`638622cfb4461c92bda7641b5f57b0855efc32b0d78aec56c6cd87e7d14e882d`.

Reviewers receive the ZIP alone. Preserve their first answers before adjudication. Next gates
include independent semantic review, expansion to additional source groups and 20-tool catalogs,
and a model-free capability audit before any constrained campaign. The candidate tranche does
not satisfy the size or track mix in the [v2 design](../../V2_DESIGN.md). E1 and E2 stay gated.
