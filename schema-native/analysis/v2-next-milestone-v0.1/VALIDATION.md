# Model-free catalog and keyword milestone

**2026-11-25. Author verification on docs/v2-benchmark-design, draft PR #7.**
Previous head: `ed72f21362a1c19cff2e2c2959360275fd302213`.
This is candidate authoring and finite engine validation. No model was loaded, no model endpoint
was called, and no training, dataset freeze or E0/E0b rerun was performed. E1/E2 remain gated.

## What changed

1. [Keyword seeds](../../data/v2-keyword-seed-v0.1/README.md): 16 synthetic pairs / 32 schema units
   across ten proposed family groups. Seven validity-separable, seven asymmetric and two equivalent
   pairs are kept distinct. All 32 golds and all 32 authored valid-wrong examples validate. All
   383 generated negative examples are rejected by jsonschema 4.26.0 under draft 2020-12.
   Fixed-template equivalence arguments are checked; general flattening/inlining is not supplied.
2. [Source candidates](../../data/v2-source-expansion-v0.1/README.md): eight pinned, source-derived
   offline adapters with purpose pointers and valid samples. Six object schemas are unchanged;
   two non-object roots use a content-addressed resource binding that preserves local references.
   No exact canonical duplicate of the frozen 300-tool pool is nominated. These are candidates
   for five peer categories; booking-resource T045 and score recorder T243 remain unrepresented.
   No actual catalog is changed, no production API is asserted, and no semantic near miss is
   certified. Every source/licence/holdout decision remains unapproved.
3. The draft V2_DESIGN pair taxonomy gains an explicitly dated, prospective asymmetric-edit label.
   Bounds and overlapping choices need not produce mutually invalid golds. This does not change
   historical scoring, locked E0/E0b analysis or any model setting.

Zero new independently reviewed pairs, zero approved test intents, zero approved source peers.
These examples do not satisfy the proposed 800-test/200-development design. The keyword packet
uses one tool per task and cannot establish tool-selection difficulty. The sources are from the
existing collection, not an outside provider holdout; the calorie family is already exposed.

## Bundled engine coverage, without a model

Evidence: [native-engine-verified.json](../../data/v2-keyword-seed-v0.1/native-engine-verified.json).
The pre-existing native audit executable and static library passed their build-hash checks.
Their source matches pinned llguidance `d795912fedc7d393de740177ea9ea761e7905774` (bundled 1.0.1).
The helper compiles `%llguidance {}\nstart: %json <schema>` and checks `json.dumps` serializations
with default comma-space/colon-space separators and a **byte tokenizer**. It is not a Qwen-tokenizer
audit or the E0b online whitespace configuration. No server, model weights or GPU is involved.

| Check | Exact result |
| --- | ---: |
| Raw schema units offered / compiled / refused | 32 / 19 / 13 |
| Complete pairs with both schemas compiled | 9 / 16 |
| Partial pairs | 1 (K04 S only) |
| Gold serializations accepted on compiled schemas | 19 / 19 |
| Negative values checked on compiled schemas | 204 |
| Invalid values accepted on compiled schemas | 0 / 204 |
| Negative values offered but unavailable after compilation refusal | 179 |
| Negative values offered across all schemas | 383 |

Every refusal, with its full engine message, remains in the evidence:

| Pair / variants | Refused feature |
| --- | --- |
| K03 S, S2 | overlapping oneOf |
| K04 S2 | not inside anyOf |
| K05 S, S2 | if / then / else |
| K06 S, S2 | dependentRequired |
| K07 S, S2 | dependentSchemas |
| K11 S, S2 | not |
| K15 S, S2 | contains / minContains |

No oneOf approximation, schema relaxation, backend substitution or unsupported-subset campaign
was introduced. Zero accepted invalid probes is bounded evidence: rejection may arise from order
or formatting rather than the intended assertion. No universal enforcement or actual inference
claim follows. The source-expansion adapters have **no native capability audit** yet.
The final evidence's pair-file, per-schema, gold, helper and library hashes were checked against
the current inputs/build. Each recorded negative list was reconstructed and compared exactly.

## Reproduction and tests

From schema-native/, use the existing .venv and pinned corpus/helper; no new packages are needed:

```bash
.venv/bin/python -m sn.keyword_seed audit --check
.venv/bin/python -m sn.source_expansion audit --check
.venv/bin/python -m sn.v2_v03 audit --check
.venv/bin/python -m sn.v2_revision audit --check
.venv/bin/python -m sn.v2_authoring audit --check
.venv/bin/python analysis/v2-design/power.py --check
.venv/bin/python -m unittest discover -s analysis/v2-design -p test_power.py -v
.venv/bin/python -m pytest -q ../experiment/tests/test_evaluate.py
.venv/bin/python -m sn.keyword_seed native --out /tmp/keyword-native-new.json
```

The full package suite uses tracked filenames to exclude pre-existing untracked duplicate files;
the two new modules' tests were added explicitly before their first commit:

```python
import subprocess
files = subprocess.check_output(["git", "ls-files", "tests/test_*.py"], text=True).splitlines()
files = sorted(set(files + ["tests/test_keyword_seed.py", "tests/test_source_expansion.py"]))
raise SystemExit(subprocess.call([".venv/bin/python", "-m", "pytest", "-q", *files]))
```

**229 tests passed:** 209 package tests (194 previous + 15 new), 12 original evaluator tests,
eight standalone planning tests. New tests cover matrices, overlap/exclusivity, conditional and
dependency requirements, tuple positions, valid-wrong examples, negative witness validity,
rewrite scope rejection, hidden-field exclusion, malformed helper evidence, unchanged reference
roots, unknown-binding rejection and absence of automatic approval. All five old/new authoring
audits and the historical power artifacts reproduce. `git diff --check` passes.

All tracked files from the previous head are preserved except the prospective V2_DESIGN addition.
In particular experiment/, E0/E0b outputs/ledgers, model and run configs, old authoring versions,
review receipts, existing runtime and training code are unchanged. Pre-existing untracked duplicate
files were not staged or removed. The two preliminary local native audit files are not publication
evidence; only native-engine-verified.json is included in this milestone.

## Review artifacts and next gate

Local exports were checked against their source rows. Each ZIP contains one JSONL payload and
review instructions. No ZIP or full source-schema copy is added to Git.

| Export | SHA-256 |
| --- | --- |
| v2-keyword-seed-v0.1-blind-review.zip | `6cc63f0cd39f2afb437333a63eafb9c372260890cb4ef1cf509187df4724b074` |
| v2-source-expansion-v0.1-review.zip | `fad2d83d8e21621b3aa2cf0c0078a6ff41c0bc0da196488a27f212a37bc2d8ba` |

Give **only the keyword ZIP** to a fresh context for a first solve, saved before gold access.
It contains no gold, expected matrices, private family labels, valid-wrong examples or engine
results. Give the separate source ZIP to an existing reviewer for a nonblind purpose/binding audit;
it does not certify a near miss without the full task/catalog. Do not combine these two roles into
a claim of blind source or task approval.

Next review must resolve semantic ambiguity, genuine catalog competition, source/family/licence
clearance and the engine capability contract. Larger task authoring, renamed variants, description
grounding, source holdouts, freeze and the future run protocol remain open. Stop here for review;
this delivery does not authorize inference or training.
