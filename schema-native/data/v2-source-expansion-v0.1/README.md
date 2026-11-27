# Source expansion candidates v0.1

2026-11-25. Eight source-backed candidate cards from the existing JSONSchemaBench checkout at
`9a94995b9279ae3af3aed4b2629172790b968d14`. These are **offline schema adapters**, not verified
production APIs, approved distractors, new task answers or source-held-out test cases.

The nomination followed an exploratory text scan of the 9,558-schema checkout beyond the frozen
300-tool pool. It is a curated candidate list, not a reproducible exhaustive semantic search.
`cards.source.jsonl` is the reviewed-input boundary: every raw schema has a pinned canonical
hash and JSON-pointer evidence for the proposed purpose. `cards.jsonl` adds raw-file hashes,
source identifiers, sample validity, exact-pool duplicate checks and existing train-pool assignments.
No complete source schema is newly committed and no existing catalog is changed.

| Card | Source-derived purpose | Proposed gap target |
| --- | --- | --- |
| X001 | Log-group retention enum | T254 retention |
| X002 | Resolver cache configuration, TTL unit unspecified | T254 retention |
| X003 | Food quantity/calories-per-serving log | T131 calorie logger |
| X004 | Dated meal log | T131 calorie logger |
| X005 | Audio track configuration | T093 captions |
| X006 | Caption transcript | T093 captions |
| X007 | Legacy country-code enum | T064 country |
| X008 | Element/archive include/exclude string lists | T016 filters |

All eight positive samples validate; no exact canonical schema duplicate of the frozen pool was
found. This does not establish semantic independence or a genuine near miss. X003/X004 share the
exposed track_calories function lineage and stay together in development. Their undeclared goal
field does not become backend-supported merely because additional properties are allowed.
X007 includes historical country codes, so no current ISO claim is made. It could make the old
country request ambiguous rather than harder. X002 states no TTL unit. X008 does not specify
regex/glob semantics, and `_uniqueItems` is not enforced as `uniqueItems`.

Six adapters preserve their object schema directly. X006 and X007 put the source value under a
required `value` property. Their original schema remains a distinct resource in an offline
registry; local references retain the original resource root. This is not a naive root transplant.
The resource binding has no existing runner/native-engine compatibility approval.

Five of the seven requested peer categories have nominations. Booking-resource T045 and score
recorder T243 still have no nomination here; this is not proof that the broader corpus lacks one.
The source review below records confirmed project overlaps. Per-file licence clearance,
production behavior, native capability and request-level competition remain open. Near misses
approved: **0**. Catalog changes: **0**. Approved test intents: **0**.

## Hash reproduction

`schema_sha256` is the SHA-256 of the parsed source schema serialized with the repository's
`experiment/src/schema_utils.py` helper. Use sorted object keys, compact separators, unescaped
Unicode encoded as UTF-8, and no trailing newline. Arrays retain their order.

```python
import hashlib
import json

def schema_sha256(source_schema):
    canonical = json.dumps(
        source_schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

Pass the parsed `source_schema` from a review row. The same convention applies to
`binding_schema_sha256` over its argument schema. `schema_raw_sha256` instead hashes the
source file's original bytes, including its formatting.

## Source review follow-up

The nonblind review rated six candidates plausible and two related (X002 and X005). Its
mechanical checks agree with the repository audit. The frozen pool confirms T254 is
`set_data_retention` and T064 is `select_country`.

The [pinned corpus source index](https://github.com/sdbs-uni-p/json-schema-corpus/blob/79f808b10c9e3269ea57f5c7c64fd663eadf2703/repos_fullpath.csv)
maps the numbered GitHub examples to original file paths. Cross-checks with upstream files
support these findings:

| Card | Origin evidence |
| --- | --- |
| X001 | [CloudWatch Logs Janitor](https://github.com/andrew-templeton/cfn-cloudwatch-logs-janitor/blob/55adf90c3dd783bc84a33199f72df2a600e8912a/schema.json), exact parsed-schema match |
| X002 | [Snowplow Iglu Central resolver-config 1-0-2](https://github.com/snowplow/iglu-central/blob/d7a4cdb511710cf52b8fbb4035fb1757fb91bdb6/schemas/com.snowplowanalytics.iglu/resolver-config/jsonschema/1-0-2). The copy in this benchmark drops the root dialect declaration and renames the URI field's `format` keyword to `_format`. The source schema leaves the TTL unit unspecified. |
| X003, X004 | [Glaive function-calling collection](https://huggingface.co/datasets/glaiveai/glaive-function-calling-v2) at the subset level. Both are in the exposed T131 `track_calories` family. Original dataset row IDs remain unresolved. |
| X005 | [GoPro ForgeJS playlist track](https://github.com/gopro/forgejs/blob/b3b33cd71beaba5db57370a8b5ebb87e2d69bb6d/reference/playlist/playlist-track.json) and [T122 sprite animation](https://github.com/gopro/forgejs/blob/b3b33cd71beaba5db57370a8b5ebb87e2d69bb6d/reference/display/sprite-animation.json) are from the same project. Both source files match the pinned benchmark copies after dropping root `$schema` and `id`. |
| X006 | The corpus index points to `notpeter/legiscrape`, path `legiscrape/granicus-captions.schema.json`. The indexed file URL returned 404, so the mapping is available but direct file verification remains open. |
| X007 | [richardjmarini/JsonSchema](https://github.com/richardjmarini/JsonSchema/blob/979807c063b55b3950b3fbbba8a744eb5697c971/schemas/country.json), exact parsed-schema match. The corpus maps T064 to a separate project, `usingjsonschema/ujs-book-materials`. |
| X008 | The index maps X008 and T016 to Revapi. [T016's annotation-filter file](https://github.com/revapi/revapi/blob/master/revapi-java/src/main/resources/META-INF/annotated-elem-filter-schema.json) matches the benchmark copy. [X008's filter file](https://github.com/revapi/revapi/blob/master/revapi-basic-features/src/main/resources/META-INF/filter-schema.json) at the indexed branch differs in its filter definitions, so keep using the pinned benchmark revision. |

Treat GoPro ForgeJS and Revapi as shared source groups in any future source holdout. The mappings
record provenance for review. Per-file licence clearance still needs the relevant historical
versions and terms.

The offline audit uses declared Draft 4 for X001, X006, X007 and X008. X002 through X005 have no
dialect declaration in the pinned copies and use the project's Draft 7 fallback. No format
checker is configured, so X004 accepts a test value of `"not-a-date"` even under Draft 7.

The current runner builds catalog text from the frozen representation files. X006 and X007 have
no entry in those files and have no model-facing representation. The reviewer packet shows both
the wrapper and the source schema. The offline validator can resolve the wrapper's URN via its
registry. A future prompt must expose the referenced structure, and any constrained run needs a
separate engine check of that representation.

The v0.3 requests already state the data-source lifespan in seconds (T254), the daily calorie
target (T131), subtitle track URLs with formats and confidence (T093), and regexes for annotation
names (T016). Those are useful distinctions to retain in a new development catalog. X007 stays
out of the Costa Rica task until the requested output is clearly a country name, since `CR`
could serve the current intent. Each proposed insertion still needs a fresh blind review with
the full catalog and request. Booking-resource T045 and scoreboard T243 remain open.

## Reproduce and source review

From schema-native/, with the existing pinned upstream checkout and Python environment:

```bash
.venv/bin/python -m sn.source_expansion audit --check
.venv/bin/python -m pytest -q tests/test_source_expansion.py
.venv/bin/python -m sn.source_expansion export-review --out /tmp/source-candidates-new.zip
```

The exported ZIP supplies the eight full raw schemas, bindings, purpose evidence, samples and
review instructions for a **nonblind source audit**. It is separate from the keyword blind task
packet. A reviewer already exposed to old gold may review sources, but cannot thereby provide a
new blind solve of old tasks. No source, catalog or split is promoted automatically. No model
endpoint, weights, server, training or E0/E0b artifact is involved. **E1/E2 remain gated.**
