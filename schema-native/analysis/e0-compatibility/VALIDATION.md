# E0 constraint-policy correction (2026-11-14 IST)

The earlier 588-request checkpoint remains unchanged and separate. It exposed compatibility faults,
not a sound comparison of learned semantics. This correction is specified before the fresh full run.
It is informed by that pilot, not an independent preregistered replication.

`annotation-dependencies-v1` changes only the prepared constraint copy:

- Omit `format` assertions. The frozen evaluator uses `jsonschema` without a FormatChecker, so formats
  do not constrain its acceptance language. Raw/minified prompts retain the original format information.
- Lower legacy dependencies into absent(trigger) OR consequent, using a false property schema for
  absence, and append these guards to allOf. No dependency is discarded and no lenient mode is used.
- Preserve literal enum/const/default/example data. This policy is bounded E0 preparation, not a
  general dialect converter or a claim of complete engine support.

Evidence (model-free): the exact native C library bundled into the server compiles 59/70 original
E0 envelopes and 70/70 corrected envelopes. All 300 corrected task/catalog gold pairs are reachable
with a byte tokenizer. All 128 property-presence combinations in the frozen dependency schema agree
with the raw validator, with zero mismatches. These checks do not replace real model-tokenizer probes.
Gold reachability uses schema-ordered object keys. It establishes a witness in the grammar,
not acceptance of every valid key permutation or the order preferred by the model. The completed-run
[key-order audit](../e0-clean-v1/KEY_ORDER.md) measures this distinction directly with the bundled engine.

Real runtime evidence: the corrected 12-request paced smoke completed with zero engine/request
errors, zero truncations and zero selected-tool raw-schema violations. This is a path check, not an
accuracy estimate. Loaded pressure stayed normal; Foundation thermal state was nominal. Full
preflight also checks every envelope and all 600 unique prompts before the new run.

50 package tests and 12 original evaluator tests pass. Clean E0 stops on any engine error,
prepared/raw constraint violation, resource warning or serious/critical thermal state. Valid calls
to the wrong tool are still model errors. Old results, old configs, original experiment files and
model weights are unchanged. New clean runs use a new run ID and are never pooled with the pilot.

Reproduce after the pinned server library has been built:

```bash
scripts/build_native_audit.sh
python -m sn.native_audit --config configs/runs/e0_clean.json --output runs/native-clean.json
python -m pytest -q
```

Sources: [format semantics](https://json-schema.org/understanding-json-schema/reference/type),
[dependency/implication semantics](https://json-schema.org/understanding-json-schema/reference/conditionals).
