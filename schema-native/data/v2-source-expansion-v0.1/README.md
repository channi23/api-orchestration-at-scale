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
Licences, production behavior, source grouping, native capability and genuine request-level
competition remain unverified for every candidate. Near misses approved: **0**. Catalog changes:
**0**. Approved test intents: **0**.

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
