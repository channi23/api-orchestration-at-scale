# Private source-held-out candidate tranche A

**2026-11-25.** Ten new API intent drafts across two source projects. Each request has a
five-tool catalog drawn from its own source, with deterministic presentation order. The ten
operations yield nine distinct argument schemas. Five gold argument objects validate under
multiple tools in their catalogs, so those cases exercise tool selection.

The pinned sources, authoring rows, requests and gold are kept in local review storage. The
repo records the builder, its checks and the aggregate receipt. The reviewer ZIP contains
only visible task rows, instructions and upstream licence notices. Its manifest and gold are
stored separately under an owner-only directory. This is the first candidate tranche.
The first semantic review and adjudication are recorded below. Zero tasks are approved for
locked test.

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

## First solve

The reviewer selected the authored tool on all ten tasks. All ten argument objects validate
against their selected tool. Nine calls match the complete authored gold. The single strict
mismatch omitted an optional filter whose effect may already be covered by another filter.
The same task also raised a phrase-matching ambiguity in the draft request and gold. The
review additionally flagged date-boundary and scheduling interpretations for adjudication.

The first answers and notes matched the supplied copies byte for byte. The reviewer reported
no prior packet or gold exposure and disclosed that personal context was loaded. The
comparison, per-case author notes and gold handoff remain in local storage.

## Adjudication and private follow-up

Adjudication confirmed the original 9/10 exact-call matches, 10/10 tool matches and 10/10
schema-valid arguments. The saved first answers and notes match the preserved bytes. The
adjudication SHA-256 is
`99228113123a60a98b728530f3d3049ccc755e97052db058d9c7e30e0b7da08b`.

The review identified one search case where the syntax in both calls is broader than the
intended result. It also identified date-boundary and scheduling wording that can change the
meaning of a request. The follow-up revises three requests and two gold argument sets:

- The search requests phrase matching and explicitly asks for both filters. The revised
  expected query uses the documented phrase syntax. The existing exact comparator retains
  the original score, and the revised contract requires the narrower search.
- The date-range case uses explicit UTC instants at both ends, with an inclusive start and
  an exclusive end. This expresses the intended full days without relying on date-only bounds.
- The scheduling case spells out the source meaning across past and future records. Its gold
  stays the same.

The follow-up retains the original tools, schema bytes in the catalog, order and policy.
It gives the changed requests new task IDs within the same three intent lineages. The
other seven requests remain in the original packet. All revised golds validate, and the
follow-up ZIP and private files reproduced byte for byte. The review ZIP SHA-256 is
`2fdb50b79568138861d25f5d10412eea348eaac0240d5327e9ba93d31c532ec7`.
The revised private manifest SHA-256 is
`d986722abc8b02b8bd8d92eed78442def839df1c5f0c828183b57d25285b42f1`.
The follow-up adds no new independent intents.

The follow-up reviewer reported no prior packet or gold exposure and matched all three
expected tools and argument objects. All three answers validate. The saved first answers
and notes matched the supplied copies byte for byte. Local probes show that the schema
accepts both case variants of one filter string and accepts unknown string-valued range
operators. Exact argument comparison distinguishes those alternatives.

Final adjudication confirmed 3/3 matches and the checksums of the saved first answers and
notes. Its SHA-256 is `871cd159d9a03d737284202bd0aca124ae2b827db043f2975b30ca562f5eedfe`.
The freeze wording proposal explicitly gives the lowercase extension literal and leaves
phrase syntax for the model to derive from the tool description. It keeps the same gold
and is stored as a separate private edit. Its SHA-256 is
`e4a9279ccf6b88517c967d6c98ccccf94cc2706eaf8b7de13a12ebb74653e856`.
The first and follow-up review scores use their respective original packet bytes.
The tranche still has zero locked-test approvals.

Reproduce it from the pinned first bundle and private revision rows:

```bash
.venv/bin/python -m sn.v2_holdout_revision --parent /private/first-candidate \
  --revisions /private/revisions.jsonl --out /private/follow-up
```

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
