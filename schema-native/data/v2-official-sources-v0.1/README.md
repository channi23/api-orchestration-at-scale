# Official API source pilot

**2026-11-25. Development review.** This packet contains six assistant-authored requests, three
per project, and ten tools derived from official OpenAPI operations. Each request has a five-tool
catalog from its own project. The drafts cover tool choice, pagination, typed filters and boundary
conditions. They are ready for a first semantic review, with zero approved test intents.

| Source | Pinned material | What it exercises |
| --- | --- | --- |
| PokéAPI | [OpenAPI 3.1](https://github.com/PokeAPI/pokeapi/blob/de6760be38b60a3024f1d9054330ff265f0dc619/openapi.yml), [BSD-3-Clause notice](https://github.com/PokeAPI/pokeapi/blob/de6760be38b60a3024f1d9054330ff265f0dc619/LICENSE.md) | Shared identifier shapes across species, form, entry and Pokédex lookups, plus offset pagination |
| Stripe | [OpenAPI 3.0](https://github.com/stripe/openapi/blob/5237fa08d785bc435df80fe40c2416e2848e49b7/openapi/spec3.json), [MIT notice](https://github.com/stripe/openapi/blob/5237fa08d785bc435df80fe40c2416e2848e49b7/LICENSE) | Overlapping product, price, tax and promotion filters, including a nested creation interval |

The manifest records exact spec and licence byte hashes. The local review ZIP includes the notices
verbatim. PokéAPI's notice also identifies third-party trademarks. The pilot stores operation
selectors, authored descriptions and task drafts in Git. The full specs and rendered schemas
stay outside the repo.

## Source screening

The audit compared 2,288 distinct schema IDs from the frozen tool pool, historical split and
reviewed adapter inventory. The pinned [source index](../v2-lineage-v0.1/README.md) supplies
indexed GitHub repositories for 2,002 of those IDs. There are zero known owner or project matches
for Stripe or PokéAPI in those mapped rows. The other 286 rows have collection-level provenance
only. GitHub's REST description was considered but skipped under the conservative owner screen,
which found six previously indexed files from another GitHub project, Git LFS. This does not
establish that those files describe the REST API.

The ten projected schemas have no exact canonical matches to prior argument schemas and no
identical top-level property-name sets in this inventory. These are limited signals. The
projection adds an argument wrapper policy, and the matching procedure can miss renamed and
equivalent forms. Exact repository screening also cannot resolve forks, undocumented provider
origins or pretraining. Treat the two groups as newly sourced **development** groups, and keep
both out of a future source-held-out test once these examples are reviewed and published.

## Argument contract

Each tool comes from a documented `GET` operation. The adapter maps inline path and query
parameters to one flat JSON argument object, retaining declared names, supported schema
constraints and required flags. It closes only the argument object's outer level. It records
parameter locations for traceability. It omits Stripe's exact empty optional form-body
placeholder and the PokéAPI list's `q` query, which the source declares local-only. The code
refuses unsupported parameter references, request bodies and schema keywords instead of guessing
their translation. Custom `format` strings remain annotations in this audit. Descriptions may
express requirements beyond the translated assertions, and wire serialization, authentication
and server responses are outside this offline check. No tools contact an endpoint.

All six authored gold calls validate on the selected tool. In three cases the exact arguments
also validate against multiple tools in the catalog. Two are PokéAPI lookups with shared
identifier shapes. The other is Stripe's product time filter, which several other resources
support as well. The correct tool must therefore agree with the user's requested resource.
This is a semantic review question, and the answer key stays separate from the packet.

## Reproduction

From `schema-native/`, use the existing project Python environment and PyYAML 6.0.3 for the
PokéAPI YAML. Download the pinned sources and notices into a scratch directory:

```bash
source_dir="$(mktemp -d)"
.venv/bin/python - "$source_dir" <<'PY'
import sys
from pathlib import Path
from urllib.request import urlretrieve
from sn import v2_official_sources as pilot

folder = Path(sys.argv[1])
for source in pilot.BASE.read_rows(pilot.DATA / "sources.jsonl"):
    for key in ("spec", "notice"):
        item = source[key]
        url = f"https://raw.githubusercontent.com/{source['project']}/{source['revision']}/{item['path']}"
        urlretrieve(url, folder / item["file"])
urlretrieve(pilot.v2_lineage.INDEX_URL, folder / "source-index.csv")
PY
.venv/bin/python -m sn.v2_official_sources --sources-dir "$source_dir" \
  --source-index "$source_dir/source-index.csv" --check
.venv/bin/python -m sn.v2_official_sources --sources-dir "$source_dir" \
  --source-index "$source_dir/source-index.csv" --export-review "$source_dir/review.zip"
```

The local review ZIP has SHA-256
`a134e1569f4f3199ab06f4b6ef8df158db0065db0dbb620d3a4cf2434ef335fa`.
The pinned inputs and six-row packet were checked locally. All 237 tests passed (217 package,
12 evaluator and eight power-planning). Send only that ZIP to the fresh reviewer. E1 and E2
stay gated.
