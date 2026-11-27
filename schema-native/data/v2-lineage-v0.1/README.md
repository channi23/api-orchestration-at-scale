# v2 source and lineage audit

**2026-11-25. Development split review.** The audit covers 32 API drafts, eight source candidates
and 16 synthetic keyword pairs. It compares them with the frozen 300-tool pool, the 50 v1 targets
and their 100 paraphrases, 1,983 historical training-pool assignments and the inventory of 21
external stress examples. All 56 audited records stay in development. **Zero test intents are approved.**

## Findings

| Check | Result |
| --- | --- |
| API draft source resolution | 23 reach an indexed upstream GitHub repository. Nine reach a collection only. |
| API drafts with an indexed project also assigned to legacy train | 16 of the 23 with a repository mapping |
| API drafts with an indexed project shared by a v1 target | 8 of those 23 |
| API drafts with a direct v1 family relation | T033 (schedule meeting) shares the recorded calendar family with T001 |
| API drafts with a legacy normalized-schema match or a normalized v1 request match | 0 |
| Source candidate schemas with an exact historical assignment | X001 and X008 are assigned to `train`. X005 is assigned to `valid`. |
| Legacy `train` and `holdout_family` with the same indexed project | 4 projects |

The legacy split's subset labels miss project overlap. For example, the [Washington Post ANS
repository](https://github.com/washingtonpost/ans-schema) accounts for 12 historical `train`, three
`valid` and two `holdout_family` assignments that the source index maps from the GitHub subsets.
The other three crossings are Camshaft/Shenu, MDStudio/MDStudio and
xchen101/analysis-preservation.cern.ch. The audit lists exact schema IDs for each. These are
**assignments in a data file**. They do not establish that a model was fine-tuned on those rows.

Both X001 and X008 were used as distractors in the three adjudicated development catalogs.
Their exact stored `train` assignments now give another reason to keep those versions in
development. X005 shares the GoPro ForgeJS project with T122. X008 shares Revapi with T016.
X003 and X004 share a Glaive function family with T131 and remain together.

## How the audit separates the evidence

- **Lineage graph.** One node keeps all versions of an API intent on the same side. A keyword pair
  is also one node, so both schemas travel together. Exact canonical schema matches and recorded
  pool families, Glaive function names and authored seed families connect nodes transitively.
  `audit.json` records components that touch the v2 material, their edge reasons and overall size
  statistics. The comparison graph has 2,261 components with minimum, median and p95 size 1 and
  maximum size 16. The 56 audited records touch 48 components. Component counts describe the
  current graph and do not establish statistical independence or completeness.
- **Project overlap.** The source overlay maps `Github_*/oN` to `js_N.json` in the
  [pinned corpus source index](https://github.com/sdbs-uni-p/json-schema-corpus/blob/79f808b10c9e3269ea57f5c7c64fd663eadf2703/repos_fullpath.csv).
  It groups the indexed repository owner/name across benchmark subsets and compares distinct
  records across old assignments, v1 targets and current catalog roles, including distractors.
  Collection-only records keep a separate evidence type. The audit does not infer relationships
  between forks or providers from a repository spelling. A project overlap affects a
  source-held-out claim independently of an exact schema or family match.
- **Review signals.** Stored legacy normalized schema hashes and NFC/case-folded,
  whitespace-collapsed requests are recorded as review signals. They never create an edge by
  themselves. This pass does not cover renamed or paraphrased near-duplicates broadly.
  Historical prompt exposure remains separate from lineage and legacy split assignments.
- **Source and licence.** The source index gives an origin path, typically on a branch.
  The [pinned benchmark collection](https://github.com/guidance-ai/jsonschemabench/tree/9a94995b9279ae3af3aed4b2629172790b968d14)
  determines the bytes used here. Direct source version and licence clearance are still
  pending for imported cases. The [Glaive collection](https://huggingface.co/datasets/glaiveai/glaive-function-calling-v2)
  declares Apache 2.0 at collection level; original row linkage remains incomplete.
  No source clearance is awarded from an index mapping or a collection label alone.

## Consequence for the next tranche

Use the current packets as development examples and controls. For a source-held-out tranche,
identify and pin new source groups before authoring. Screen each group against the prior training,
development and distractor inventories. Keep its whole lineage together, record rights and version
evidence, then obtain a gold-blind semantic review for the new requests. Seeded split assignment
starts only after there is an eligible frame. The legacy split files remain historical evidence.
E1 and E2 stay gated.

## Reproduce

From `schema-native/`, fetch the index at the stated commit and run the read-only check:

```bash
index_file="$(mktemp)"
curl --fail --silent --show-error --location \
  https://raw.githubusercontent.com/sdbs-uni-p/json-schema-corpus/79f808b10c9e3269ea57f5c7c64fd663eadf2703/repos_fullpath.csv \
  --output "$index_file"
.venv/bin/python -m sn.v2_lineage --source-index "$index_file" --check
.venv/bin/python -m pytest -q tests/test_v2_lineage.py
rm "$index_file"
```

The module checks the index SHA-256 before parsing and records the hashes of its other inputs.
It only reads existing experiment artifacts and performs local data comparisons.
The full upstream index and original schemas are not copied into the PR.

The pinned-index audit, catalog/source/keyword and v0.3 artifact checks, and historical power
artifacts reproduced. The test suites passed all 234 cases (214 package, 12 evaluator,
eight power-planning).
