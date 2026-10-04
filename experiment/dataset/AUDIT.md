# JSONSchemaBench audit

Source: https://github.com/guidance-ai/jsonschemabench @ `9a94995b9279ae3af3aed4b2629172790b968d14`  
Total schemas observed: **9558**

Counts are numbers of schemas containing the feature anywhere in the schema (`has_nested_object` = an object with `properties` at depth >= 1; `has_conditional` = if/then/else, dependencies, dependentSchemas/Required; `has_constraints` = any of min/max/length/pattern/format/items-count/uniqueItems/multipleOf).

| subset | n | root_object_with_properties | title_or_description | ref | ref_cyclic | nested_object | array | array_of_objects | enum | oneOf | anyOf | allOf | conditional | not | patternProperties | constraints | format | pattern | metaschema_invalid | eligible | eligible_flat | eligible_structured |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Glaiveai2K | 1707 | 1707 | 0 | 0 | 0 | 1257 | 496 | 321 | 206 | 49 | 3 | 0 | 18 | 7 | 0 | 151 | 149 | 0 | 0 | 1681 | 343 | 1338 |
| Github_trivial | 444 | 212 | 238 | 41 | 1 | 37 | 76 | 18 | 98 | 71 | 26 | 11 | 1 | 7 | 25 | 135 | 15 | 51 | 0 | 210 | 137 | 73 |
| Github_easy | 1943 | 1707 | 1146 | 281 | 14 | 577 | 649 | 284 | 457 | 96 | 78 | 35 | 14 | 8 | 49 | 809 | 169 | 230 | 1 | 1607 | 749 | 858 |
| Github_medium | 1976 | 1795 | 1133 | 508 | 48 | 1156 | 1130 | 614 | 875 | 224 | 98 | 54 | 27 | 24 | 136 | 1199 | 371 | 568 | 1 | 495 | 110 | 385 |
| Github_hard | 1240 | 1145 | 569 | 602 | 198 | 1014 | 973 | 660 | 878 | 360 | 355 | 71 | 39 | 31 | 287 | 911 | 445 | 597 | 0 | 0 | 0 | 0 |
| Github_ultra | 164 | 131 | 78 | 131 | 36 | 113 | 156 | 88 | 130 | 66 | 77 | 22 | 4 | 20 | 30 | 118 | 68 | 74 | 1 | 0 | 0 | 0 |
| JsonSchemaStore | 492 | 383 | 416 | 340 | 68 | 311 | 433 | 178 | 339 | 189 | 160 | 105 | 48 | 31 | 118 | 322 | 106 | 173 | 0 | 0 | 0 | 0 |
| Kubernetes | 1064 | 1060 | 1054 | 779 | 19 | 0 | 647 | 0 | 292 | 275 | 0 | 0 | 0 | 0 | 0 | 225 | 225 | 0 | 0 | 0 | 0 | 0 |
| Snowplow | 403 | 386 | 365 | 3 | 0 | 175 | 136 | 80 | 105 | 24 | 18 | 0 | 3 | 0 | 12 | 291 | 5 | 54 | 0 | 213 | 144 | 69 |
| WashingtonPost | 125 | 75 | 124 | 77 | 24 | 36 | 61 | 26 | 68 | 24 | 26 | 29 | 27 | 23 | 32 | 35 | 0 | 31 | 0 | 13 | 5 | 8 |
| **TOTAL** | 9558 | 8601 | 5123 | 2762 | 408 | 4676 | 4757 | 2269 | 3448 | 1378 | 841 | 327 | 181 | 151 | 689 | 4196 | 1553 | 1778 | 3 | 4219 | 1488 | 2731 |

## Eligibility criteria (tool-convertible)

- included subsets: Glaiveai2K, Github_trivial, Github_easy, Github_medium, Snowplow, WashingtonPost (Kubernetes, Github_hard, Github_ultra, JsonSchemaStore excluded: predominantly whole configuration documents, not plausible tool inputs, and too large for 100-tool catalogs)
- root is an object with 1..15 top-level properties
- metaschema-valid under its declared draft (default draft-7)
- no cyclic, non-local or unresolvable `$ref` (needed for the NORMALIZED condition)
- not matching the documented GlaiveAI unsatisfiable `oneOf` pattern (upstream issue #16)
- pretty-printed size <= 1500 chars (context budget for 100 raw tools)
- not an exact duplicate (sha256 of canonical normalized schema) of an earlier schema

## Exclusion reasons (all reasons, a schema can have several)

| reason | count |
|---|---:|
| too_large_for_100_tool_context | 4424 |
| subset_excluded_config_documents | 2960 |
| root_not_object_with_properties | 957 |
| top_level_property_count_out_of_range | 810 |
| cyclic_ref | 408 |
| known_unsatisfiable_pattern | 29 |
| exact_duplicate_of | 25 |
| nonlocal_or_unresolvable_ref | 5 |
| metaschema_invalid | 3 |

## Primary (first) exclusion reason

| reason | count |
|---|---:|
| subset_excluded_config_documents | 2960 |
| too_large_for_100_tool_context | 1377 |
| root_not_object_with_properties | 716 |
| top_level_property_count_out_of_range | 195 |
| cyclic_ref | 47 |
| exact_duplicate_of | 25 |
| known_unsatisfiable_pattern | 14 |
| nonlocal_or_unresolvable_ref | 3 |
| metaschema_invalid | 2 |

Eligible schemas: **4219** (flat 1488, structured 2731). `flat` = no top-level property is an object/array/$ref/combinator (TSCG keeps all top-level structure); `structured` = at least one is (TSCG drops sub-structure).
