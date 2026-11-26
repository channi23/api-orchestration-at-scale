# Private v2 holdout candidate tranche C

2026-11-26. This adds **56 candidate intents** from travel and weather input contracts
and newly authored schema pairs. The combined private inventory has **98 candidates**,
including 70 API intents across six upstream source groups. Catalog variants and revisions
preserve their original intent lineage.

| New coverage | Count |
| --- | ---: |
| Real API intents | 40 |
| New API source groups | 2 |
| Distinct API argument schemas among 40 selected operations | 37 |
| Validity-separable assertion pairs | 5 |
| Asymmetric assertion pairs | 5 |
| Description-grounding pairs | 6 |
| Golds that validate / rejected negative witnesses | 72 / 72 |
| Expected arguments valid under multiple tools at both API catalog sizes | 10 |

The API tasks include hotel discovery, property lookup and dated offer search in one source,
and station, grid and product lookups in the other. Every API task has a five-tool catalog
nested in its 20-tool view with fixed relative presentation order. The input projection uses
read-only source operations, a commit-pinned travel specification and a byte-hashed weather
specification snapshot. The private source manifest retains the native dialects, source URLs,
versions and upstream notices. The normalized benchmark arguments use Draft 2020-12.

The projector supports Swagger 2 path and query primitives and arrays, preserves supported
assertions including numeric step size and array uniqueness, and refuses header or body
parameters. For OpenAPI 3.1 it accepts the supported subset shared with the existing
OpenAPI 3.0 projector and rejects dialect-sensitive parameter keywords. Wire serialization,
date format enforcement and actual service availability were outside the local checks.
The grounding track annotates arithmetic and unit/rate conversion in the authoring rows.

## Blind review and revisions

Two isolated Codex reviewer contexts each solved half of the original packet. Their immutable
first answers matched **72/72** expected tools and arguments, and all 72 validated.
The original review identified a syntactically valid travel date outside the tool's described
search horizon and potential alternate readings involving resource identity, filter defaults,
departure dates and prefix matching. Eight cases were clarified in v0.2. Two expected dates
changed. A fresh reviewer context matched **8/8** revised tools and arguments and all eight
validated. Catalogs, schemas and intent lineages remained unchanged. All comparisons were
made after the independent first solves were saved. Model diversity and human adjudication
remain pending review requirements.

- Original review ZIP SHA-256 `be5a2fa354a27afbd14c5ed2891891dbf9feb9fe84ff688def961cbb6f8ec2b7`.
- Follow-up review ZIP SHA-256 `e0d9a0eb4c82d74d2ff28d456c133a111b49baa8931d61cc8a9f09d765bce268`.
- Original private manifest SHA-256 `60986aa4a007ca781db5579615ea110f3352bb943f42be42d3ef85deb7546a0b`.

The original and revised packets, smaller catalog views, expected answers and manifests
reproduced byte for byte. The releases contain 72 unique reviewed rows before catalog
replication. Private bytes and per-item receipts stay local.

## Cross-tranche freeze readiness

Both new source owners cleared the screen of 2,002 repository-indexed historical schemas.
A further 286 prior schemas have collection-level provenance. The canonical schema and
normalized-request screens found zero exact overlaps with earlier tranches and cataloged
development material. A separate check covered 13 recent development requests and 51
development or published example schema hashes. These finite screens leave semantic
near-duplicates, forks and base-model pretraining exposure open.

The combined local inventory flags four schema pairs for lineage review. Their rule templates
closely resemble published or development examples in unit rescaling, percentage conversion
and the optional-field choice under overlapping `oneOf` branches. The original rows and blind
evidence remain preserved. The inventory leaves **94 candidates for further freeze review** and
**zero approved locked-test intents**. The four holds were determined before any Qwen generation
on the candidate pool. The private readiness manifest SHA-256 is
`d4886721ee0e8ad21f0d18a44fc11df4d4c4b5d908136a2f76358602a5cc069b`.

| Current candidate roster before holds | Intents |
| --- | ---: |
| API tool calling | 70 |
| Assertion-keyword pairs | 18 |
| Description-grounding pairs | 10 |
| Total across A, B and C | 98 |

The offline tokenizer audit used compact catalogs, the [9,216-token candidate profile](../v2-context-smoke-v0.1/RESULTS.md)
and the existing 512-token output reserve. It reproduced 87 saved live calibration counts.
The table includes current reviewed revisions and the held lineage candidates.

| Tool catalog size | Prompts | Largest prompt | Over the 8,704-token prompt allowance |
| --- | ---: | ---: | ---: |
| 1 | 56 | 277 | 0 |
| 5 | 70 | 4,886 | 0 |
| 20 | 60 | 7,792 | 0 |
| Total | 186 | 7,792 | 0 |

The current roster is a candidate for separately reviewed exploratory use. It is below the
provisional confirmatory scale and still needs final source/family adjudication, catalog policy
and a signed freeze. Tranche A has five-tool views only. Online context checks and the untuned
baseline require a later reviewed campaign on the exact frozen bytes. E1/E2 remain gated.
The candidate pool has zero Qwen requests.

## Reproduce privately

Run from `schema-native/` with the retained sources, pinned source index and earlier packets.

```bash
.venv/bin/python -m sn.v2_holdout_batch --stem v2-holdout-candidate-c-v0.1 \
  --inputs /private/tranche-c-authoring --source-index /private/repos_fullpath.csv \
  --prior /private/tranche-a-v0.1 --prior /private/tranche-a-v0.2 \
  --prior /private/tranche-b-v0.1 --prior /private/tranche-b-v0.2 --out /private/tranche-c-v0.1
.venv/bin/python -m sn.v2_holdout_batch_revision --stem v2-holdout-candidate-c-v0.2 \
  --parent /private/tranche-c-v0.1 \
  --parent-sha256 60986aa4a007ca781db5579615ea110f3352bb943f42be42d3ef85deb7546a0b \
  --revisions /private/tranche-c-authoring/revisions-v0.2.jsonl --out /private/tranche-c-v0.2
.venv/bin/python -m sn.v2_holdout_budget --bundle /private/tranche-c-v0.1 \
  --follow-up /private/tranche-c-v0.2 --tokenizer /private/qwen-tokenizer.json --compact \
  --profile configs/model.qwen3-1.7b.v2-context-9216.json
```

Use `sn.v2_holdout_review` with the frozen first answer and note paths to reproduce individual
review comparisons. It rejects duplicate task IDs and requires full packet coverage.
Tranche B reproduced byte for byte with the extended builder. The projected A inputs and
golds are unchanged. Rebuild its exact historical manifest at its original builder revision
to preserve the recorded builder hash. All 262 tests passed (242 package, 12 original
evaluator and eight power-planning).
