# Engine audit (model-free)

Each engine is asked to compile the constrained-decoding schema of every tool and then to accept the frozen gold call, character by character. No model is involved. A rejected gold call means the engine makes that task unsolvable.

Tools: 300. Target tools with a gold answer: 50.

| Engine | Version | Schemas compiled | Compiled with warnings | Targets compiled | Gold accepted (compact) | Gold accepted (spaced) | Gold accepted (either) |
|---|---|---:|---:|---:|---:|---:|---:|
| llguidance | 1.9.1 | 292/300 | 0 | 50/50 | 50/50 | 50/50 | 50/50 |
| xgrammar | 0.2.9 | 298/300 | 0 | 49/50 | 47/50 | 47/50 | 47/50 |
| outlines_core | 0.2.14 | 287/300 | 0 | 48/50 | 46/50 | 46/50 | 46/50 |

## Target tools where an engine cannot produce the gold call

| Engine | Tool | Stratum | Problem | Schema keywords |
|---|---|---|---|---|
| xgrammar | post_release_comment (T062) | structured | gold call rejected | maxLength, minLength, pattern |
| xgrammar | register_quantum_backend (T103) | structured | compile: RuntimeError: [09:03:27] /project/cpp/json_schema_converter.cc:5082: minItems is greater than the number of pr | enum, items, maxItems, minItems, minimum, oneOf |
| xgrammar | define_keyframe (T158) | structured | gold call rejected | items |
| outlines_core | post_release_comment (T062) | structured | gold call rejected | maxLength, minLength, pattern |
| outlines_core | create_place (T089) | structured | compile: ValueError: Unsupported JSON Schema structure {"elevation":{"type":"number"},"latitude":{"type":"number"},"lon | additionalProperties, anyOf |
| outlines_core | create_view_template (T152) | structured | compile: ValueError: Unsupported JSON Schema structure false 
Make sure it is valid to the JSON Schema specification an | additionalProperties, maxLength, minLength, pattern, patternProperties |
| outlines_core | track_client_session (T273) | flat | gold call rejected | additionalProperties, enum, maximum, minimum, pattern |
