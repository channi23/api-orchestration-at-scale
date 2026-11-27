# Keyword stress seeds v0.1

2026-11-25. Sixteen assistant-authored **development-only** synthetic pairs, 32 schema units,
ten proposed family groups and **zero approved test intents**. These are examples for semantic
review, not a frozen dataset, an independent holdout, a power calculation or model results.

The request stays fixed within a pair. The schema changes and the intended answer may change.
There are seven validity-separable pairs, seven asymmetric edits and two equivalent rewrites.
`validation.json` stores every four-way verdict in order
`[valid(S,g), valid(S2,g), valid(S,g2), valid(S2,g2)]`. An asymmetric edit deliberately has one
cross-valid answer: validity alone does not establish that it follows the user's preference.

Coverage includes required contacts, overlapping oneOf/anyOf branches, conditionals, dependencies,
tuple positions, a local reference chain with four object levels, open-object allOf, not,
numeric/array bounds, additional properties, contains and patterns. Each of the 32 variants has
a raw-valid but wrong example. These are authored witness claims awaiting an independent semantic
review; the automated check verifies validity and inequality to gold, not natural-language truth.
Several requests explicitly ask the solver to reason about the schema. This isolates argument
semantics and is not evidence of representative API traffic or hard tool selection.

## Rewrites and exposure

K09 substitutes an exact, reference-free address leaf through a two-link local reference chain.
K10 merges two exact open-object branches with disjoint properties. The proof checks accept only
these fixed templates; they are not general reference resolvers or allOf flatteners. Scope-changing
identifiers, reference-bearing leaves and closed-object variants fail the template checks.
Their simple substitution/intersection arguments are stronger than witness agreement, but apply
only to these templates. The concepts overlap with the previously exposed stress-fixtures 0.4
examples. There is no novelty or unseen-family claim for these examples.

Family names are conservative author labels, not demonstrated independence. All seeds share one
author/source group and stay in development. There is no renamed family split or source holdout.

## Model-free engine finding

`native-engine-verified.json` uses the existing hash-verified native helper and the pinned bundled
llguidance 1.0.1 source at `d795912fedc7d393de740177ea9ea761e7905774`. It starts no server and
uses a **byte tokenizer, not Qwen's tokenizer**.

- 19/32 schemas compile; all 19 compiled schemas accept their gold serialization.
- 204 validator-rejected values are checked on compiled schemas; zero are accepted.
- 383 negative values were offered in total; 179 belong to refused schemas and were not checked.
- Nine complete pairs compile; K04 has only its S member compiled.
- Thirteen refusals: K03 S/S2 (oneOf), K04 S2 (not), K05 S/S2 (if/then/else),
  K06 S/S2 (dependentRequired), K07 S/S2 (dependentSchemas), K11 S/S2 (not),
  K15 S/S2 (contains/minContains).

These are finite probes. Rejection can also arise from formatting or key order; zero false
acceptances is not a universal enforcement proof. No schema was relaxed and the suggested
oneOf-to-anyOf approximation was not enabled. Unsupported examples remain visible. The engine
coverage contract needs review before any future constrained campaign; this work chooses no
replacement backend and authorizes no inference.

## Reproduce and review

From schema-native/, using the existing environment (`jsonschema==4.26.0`):

```bash
.venv/bin/python -m sn.keyword_seed audit --check
.venv/bin/python -m pytest -q tests/test_keyword_seed.py
.venv/bin/python -m sn.keyword_seed native --out /tmp/keyword-native-new.json
.venv/bin/python -m sn.keyword_seed export-review --out /tmp/keyword-blind-new.zip
```

The native command requires the existing pinned helper/static library and refuses an existing
output path. It does not build or install anything. `audit` without `--check` regenerates only
this seed's three generated artifacts. The native evidence pins the pair file, schemas, golds,
helper, library and engine source.

The exported ZIP contains only 32 visible one-tool tasks and fresh-review instructions, without
gold, expected matrices, family metadata, valid-wrong examples or engine results. Give it alone
to a fresh reviewer context and preserve the first solve before showing gold. It tests argument
interpretation, not selection among competing tools. No inference, training or promotion follows
automatically from a passing authoring audit. **E1/E2 remain gated.**
