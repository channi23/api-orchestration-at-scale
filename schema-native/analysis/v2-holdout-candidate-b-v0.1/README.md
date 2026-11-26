# Private v2 holdout candidate tranche B

2026-11-26. This adds **32 candidate intents**. Combined with the ten in
[tranche A](../v2-holdout-candidate-a-v0.1/README.md), the private candidate pool has
**42 intents across both tranches**, including real API tasks from four upstream source
groups. There are zero approved locked-test intents. Review packet bytes and first
solves are preserved under separate hashes.

| New coverage | Units |
| --- | ---: |
| API intents | 20 |
| API source groups | 2 |
| API catalog sizes | 5 and 20 |
| Distinct input argument schemas among 40 API operations | 27 |
| Assertion pairs with disjoint gold validity | 4 |
| Assertion pairs with one cross-valid gold | 4 |
| Description-grounding pairs | 4 |
| Schema-valid expected calls / rejected negative witnesses | 44 / 44 |

Each API request has a five-tool catalog nested in the same 20-tool catalog, with stable
relative presentation order. Eleven expected argument objects validate under more than one
tool at both sizes. These are schema-validity ties. Semantic competition is judged separately
from the request and tool descriptions. The semantic review used the 20-tool views.

Each of the 12 schema pairs holds the request fixed and edits one schema location.
Paired variants count as one intent. The assertion track includes position-specific objects
in a tuple, duplicate array items, property-name patterns and numeric multiples.
The grounding track changes one description and checks that both different golds
validate against both schemas. Candidate family labels need lineage review before they
can underpin independent-sample counts.

## Source and privacy checks

Both API sources are pinned OpenAPI 3.0 documents with upstream license files. The local
projection uses read-only operations, resolves local references and preserves supported
input assertions. It uses JSON argument objects for the benchmark and treats formats as
annotations. The checks did not exercise live service semantics or wire encoding.

The owner screen found zero matches against 2,002 repository-indexed legacy IDs.
Another 286 IDs have collection-level provenance. There were zero exact known schema or
normalized request overlaps in the builder's prior screen. A separate screen found no exact
matches against 13 recent development requests and 51 development and external example
schema hashes. Corpus coverage, fork relationships, semantic duplication and base-model
pretraining remain uncertain.

Source identities, exact requests, schemas, gold and per-item review receipts remain local.
The reviewer ZIP contains visible task rows, review instructions and license notices.
Gold, the five-tool view and the detailed manifest are stored in a separate owner-only location. Both first
and revised packets, golds, smaller views and private manifests reproduced byte for byte.

## Gold-blind review and revisions

Two Codex reviewer contexts opened only their supplied review packet. Each saved first
answers and notes before the author compared them with gold. This establishes isolated
first solves. Reviewer-model diversity and human adjudication remain unverified.

| Packet | Tool matches | Valid arguments | Exact calls |
| --- | ---: | ---: | ---: |
| B v0.1 | 44/44 | 44/44 | 44/44 |
| B v0.2 follow-up | 8/8 | 8/8 | 8/8 |

The first reviewer flagged equivalent default-based calls, metric-limit wording, the
distinction between a collection and its parent resource, an unspecified host identity and a
pagination ceiling. The follow-up clarifies eight rows across seven intent lineages. Two golds
now include an explicitly requested filter mode that happens to equal its documented default.
The role-grounding pair keeps an identical request on both sides. The follow-up reviewer
reported no remaining ambiguity on the revised rows. The original first scores remain attached
to their original bytes. Revisions add zero independent intents. An annotation about a
one-based index permits zero under the shared assertion schema, but the requested value is
unambiguous in both variants, so those two original rows remain unchanged.

- B v0.1 blind ZIP SHA-256 `9a921f540944747566c049c0fbbf6e274c2a096cda601c6d235b85e928cb06de`
- B v0.2 blind ZIP SHA-256 `dcc29abdeffa84504e7365db86533cdcd790140f12c6b919b99603fcd8718b50`

## Baseline readiness

An offline tokenizer audit on the original packet with the eight revised rows substituted
reproduced all 87 saved online prompt lengths from the two development runs. It uses the
recorded chat template and [pinned upstream tokenizer asset](https://huggingface.co/Qwen/Qwen3-1.7B/blob/70d244cc86ccca08cf5af4e1e306ecf908b1ad5e/tokenizer.json)
without loading weights. The profile provides 8,192 context tokens with 512 reserved
for output, leaving a 7,680-token prompt budget.

| Catalog | Prompts | Readable prompt-token range | Over budget |
| --- | ---: | ---: | ---: |
| 1 tool | 24 | 248–393 | 0 |
| 5 tools | 20 | 1,280–5,891 | 0 |
| 20 tools | 20 | 5,766–10,754 | 10 |

Compact JSON reduces the largest 20-tool prompt to 7,792 tokens. The same ten still exceed
the budget, with a maximum excess of 112 tokens. No prompt truncation, source-specific
subset, context increase or change to the baseline representation was applied. Before launch,
choose and lock a representation and runtime budget that cover the included catalogs, and
verify those exact prompts on the pinned server.

The 42 candidates are an expansion toward the provisional confirmatory scale in
[the v2 design](../../V2_DESIGN.md). They do not meet its planned source/family breadth
or support a confirmatory claim. The freeze still needs further source and family review,
independent adjudication of the chosen dataset, and a feasible context budget. No candidate
was sent to Qwen. No baseline, held-out result or training result is reported.

## Reproduce privately

Use the existing Python environment and the retained owner-only sources, drafts and prior
packets. The structural and review steps are model-free. `v2_holdout_budget` also needs the
pinned tokenizer plus the saved online calibration manifests and preflight logs.

```bash
.venv/bin/python -m sn.v2_holdout_batch --inputs /private/tranche-b-authoring \
  --source-index /private/repos_fullpath.csv --prior /private/tranche-a-v0.1 \
  --prior /private/tranche-a-v0.2 --out /private/tranche-b-v0.1
.venv/bin/python -m sn.v2_holdout_batch_revision --parent /private/tranche-b-v0.1 \
  --parent-sha256 a69ab7f84cd8265d42fbe8e0be05ebe11a991b15af1de4eb8165d23ec8b62c57 \
  --revisions /private/tranche-b-authoring/revisions-v0.2.jsonl --out /private/tranche-b-v0.2
.venv/bin/python -m sn.v2_holdout_budget --bundle /private/tranche-b-v0.1 \
  --follow-up /private/tranche-b-v0.2 --tokenizer /private/qwen-tokenizer.json
```

Add `--compact` to repeat the diagnostic with compact catalog JSON. All 255 tests
passed (235 package tests, 12 original evaluator tests and eight power-planning tests).
