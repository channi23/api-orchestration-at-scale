# v2 tool-call and unseen-schema benchmark specification

**DRAFT FOR DESIGN REVIEW — 2026-11-25. Not a locked dataset or an executable campaign.**

Addresses [issue #6](https://github.com/channi23/api-orchestration-at-scale/issues/6).
Based on merged main `778c1c1e11c14867b4ed3e3c1cbf8acd3353f0a6` and the accepted
[E0b interpretation](analysis/e0b-amendment3-v1/INTERPRETATION.md).

## 1. Purpose, scope and decisions proposed for review

Determine whether a small model can choose a tool and generate semantically correct arguments
for experimentally held-out schemas. Eventually test whether training improves that behavior
and whether a deployable small-model system can match a stronger reference at lower total cost.
These are separate claims. Neither was established by E0b's order diagnostic.

The initial delivery specified the dataset and supplied a model-free planning calculation. The
user's subsequent "do that" authorizes candidate authoring and checks; the first provisional
[authoring batch](data/v2-authoring-v0.1/README.md) is separate from dataset approval. This does not
authorize benchmark inference, weight edits, training infrastructure or changes to any E0/E0b
result, prompt, score, config or `experiment/` file. It does not authorize E1/E2.
Historical PLAN.md stage-2a counts and abstention suggestions are not a launch protocol for v2;
this reviewed, versioned design must precede any later implementation or campaign lock.

| Decision | Proposed default | Status |
| --- | --- | --- |
| First authoring source | One candidate intent per each of the 250 pool tools not targeted in v1 | Proposal; 250 tools is not 250 verified independent holdouts |
| Additional sources | Expand with provenance-traceable APIs and independently authored schema families; external source holdout is required for a source-transfer claim | Source/licence inventory needed before freezing |
| Authors and review | Human or model draft, followed by a separate reviewer solving the request without seeing draft gold or candidate-model outputs | No draft is accepted on validator checks alone |
| Size | Provisionally 800 locked-test intent clusters plus 200 development intent clusters | Recompute using development clusters; not a power guarantee |
| Core contract | One tool call, all required details explicit, satisfiable and unambiguous request | Refusal and missing-information behavior deferred |
| Tracks | API tasks, assertion-keyword pairs, description-grounding pairs, reported separately | Do not turn grounding gains into keyword-understanding claims |
| Training | No training until dataset and capability gates pass and a new protocol is approved | E1/E2 remain gated |

All defaults are concrete review proposals, not retroactive amendments to E0b. Candidate authoring
has been authorized; independent review, dataset freeze and campaign approval remain separate gates.

## 2. Size and the independent unit

The published file contains 1,562 records: 1,500 final rows plus controls/retry attempts. Planning
uses only the 200 final select units per contrast, excluding determinism and retry records.
Those 200 units represent **50 independent intents**, each repeated four times.
Stored historical `eval.e2e_success` values are used verbatim; the proposed stricter v2 contract
is not retroactively applied to these rows.

- C2 versus C1: 37 improved units, one regression, +18 points; observed row discordance .19.
- V versus F0: five improved units, no regressions, +2.5 points; row discordance .025.
- Neither contrast estimates a future training effect or the difficulty of new schemas.

[POWER.md](analysis/v2-design/POWER.md) and [power.json](analysis/v2-design/power.json) reproduce
these counts, intent clustering, conditional whole-intent simulations and sensitivity tables.
For a true 5-point change against zero, an independent binary-pair normal approximation at 80%
power gives 312/626/940 pairs for discordance .10/.20/.30 (two-sided alpha .05). A conservative
two-test Holm first-step alpha .025 gives 378/758/1,139. These are planning scenarios, not exact
McNemar power or family-cluster guarantees. Requiring an observed gain of at least five points is
an additional practical gate; the calculation does not promise 80% passage of that gate when the
true effect is exactly five points.

Provisional candidate allocation, **after** eligibility/leakage review:

| Track | Development intents | Locked-test intents | What one intent means |
| --- | ---: | ---: | --- |
| API tool calls | 100 | 500 | A distinct task/tool scenario, not another paraphrase |
| Assertion keywords | 50 | 150 | One base scenario and its paired schema edit |
| Description grounding | 50 | 150 | One base scenario and its paired description edit |
| Total | 200 | 800 | Pair members and controls do not increase independent n |

The 250 unused pool tools are the first authoring tranche, not this complete allocation. Source
expansion and family review may reduce their eligible count. Do not fill a shortfall with cloned
templates, extra catalogs, renamings or paraphrases. If sufficient independent sources/families
cannot be obtained, report a smaller exploratory dataset rather than claim adequate power.
The small per-track counts may be insufficient to establish a five-point gain within that track.

Before freeze, enumerate cluster-size distributions and estimate uncertainty from development
data only, once a separately approved model-free/online pilot protocol exists. Simulate the
actual hierarchical estimator at effects 0, 3, 5 and 8 points over plausible family correlations,
check false-positive rates, and enlarge or narrow the confirmatory claim before test access.
Keep development tasks separate from the test frame during this calibration. No sample-size
change based on locked-test accuracy is allowed.

## 3. Provenance, family splits and leakage

Record distinct identities rather than treating the keyword name as a family:

- `intent_id`: the underlying user goal; all paraphrases and catalog repetitions share it.
- `base_schema_id`: the original schema; all mutations, property-order variants, inlining and
  renaming descendants retain its lineage.
- `structural_family_id`: authored template or semantic operation lineage, including equivalent
  rewrites and paired edits; generic shared use of `required` does not create an edge.
- `source_id`: upstream repository/API/document and pinned version; `source_group_id`: the
  provider/project grouping used for a source-held-out evaluation. A JSONSchemaBench subset name
  alone does not prove distinct API provenance. Unknown provenance cannot support that claim.

Construct a leakage graph using shared intent, schema ancestry, authored family/template and
confirmed duplicates. Whole connected components are indivisible across train/dev/test. Source
groups assigned to an external holdout are excluded from both training and development, including
their schemas as distractors. Report component counts and min/median/p95/max sizes, edge reasons
and every giant component. Do not break a large component just to meet counts; change the sampling
frame and document it. Generic names such as `name`/`id` are not duplicate edges by themselves.

Before any v2 authoring, inventory the frozen 300-tool pool, its 50 target intents, all 100 v1
paraphrases, schema-native/trainpool, stress examples and any future authoring corpus. Mark v1
target-intent and stress-example lineages as exposed development-only material. Exclude their confirmed family
siblings from locked test. Existing trainpool assignments must be re-audited; do not assume the
old split is compatible with v2. Similarity scores are review candidates, not proof of identity.

The initial authoring audit found prior catalog exposure for 100 of the 250 untargeted tools in E0,
and 246 in the older full-v2 experiment. Prior inference exposure is recorded separately from
training/development leakage: it does not update weights, but "not previously a target" must not
be described as "never previously supplied to the model." A tool's prior distractor appearance alone
does not establish a new intent's leakage status. All candidates remain provisional and unassigned
unless a known target-family sibling requires development-only treatment.

Use versioned exact-byte, canonical-JSON, schema-structure and normalized request comparisons;
record thresholds and reviewed near-duplicate edges. Assign eligible components with seeded hashes
`SHA256("v2-split-20261125" + NUL + component_id)`, preserving declared track/source strata. Publish
the assignment algorithm, component manifest and any deterministic balancing rule before freeze.
Require at least 80 independently authored lineage components in the proposed locked test, report
their imbalance, and test whether family clustering invalidates the nominal 800-intent target.

"Unseen" means excluded from our experimental training/development, **not proven absent from the
base model's pretraining**. An API-source holdout claim waits for actual verified source groups;
pool-only results must be labelled in-pool generalization.

## 4. Request and answer contract

The output is one strict JSON object, exactly `{"tool": "tool_name", "arguments": {...}}`.
Tool names are unique in the offered catalog. No wrappers, commentary, duplicate keys, non-finite
numbers or additional envelope keys. A call is correct only if the tool is allowed by the request,
the arguments satisfy that tool's **raw** schema, and the values satisfy an independently reviewed
task-specific answer predicate. Schema validity by itself does not establish semantic correctness.

All units, dates, time zones, identifier values, rounding conventions and necessary business rules
must be explicit in the request or supplied tool documentation. Gold may be a set/predicate where
several outputs are valid; record why each is acceptable. Only declare a single gold when the
request determines it. The author and independent reviewer must agree on ambiguity before freeze.

Compare parsed object keys without order significance. Preserve array order unless the task's
reviewed contract explicitly makes a particular array a set. Do not silently case-fold identifiers,
normalize Unicode keys, coerce types, fill defaults, remove extra keys or accept near matches.

Core requests are satisfiable and do not require discarding user details. Refusals, missing values,
no-tool cases and ambiguous requests need a separate reviewed abstention contract and version;
the historical suggestion of 60 abstention tasks is not part of this core benchmark.

## 5. Tracks, transformations and gold checks

### API tasks

Include genuinely confusable tools and more than one relevant-looking distractor, selected using
descriptions/provenance without looking at candidate-model outputs. Use catalog sizes 5 and 20
with the target present; arggen-only is a diagnostic. A mock execution can check contract handling,
but a hash-returning mock is not evidence of successful interaction with a real API.

### Assertion-keyword pairs

Cover nested required/type constraints; enum/const and string/numeric bounds; discriminated
oneOf, anyOf, allOf and not; if/then/else; dependentRequired/dependentSchemas; additionalProperties;
$defs/$ref; homogeneous arrays and **per-position tuple arrays** with prefixItems/items; and bounds.
Keep recursion and unevaluatedProperties in explicitly labelled exploratory coverage until their
reference, witness and engine contracts are reviewed; never claim broad coverage from their names.

Each pair fixes the user request while making one reviewed schema change. Store the four verdicts
in order `[valid(S,g), valid(S',g), valid(S,g'), valid(S',g')]`:

| Pair label | Required evidence |
| --- | --- |
| Validity-separable | `[true,false,false,true]`, distinct gold answers, both fully answer the same request |
| Equivalent rewrite | `[true,true,true,true]`, same semantic gold; a sound transformation argument for the allowed subset |
| Non-equivalent, same answer | Same gold and four true verdicts, plus a witness distinguishing the schemas |

Do not assume every meaning-changing edit permits two mutually exclusive valid answers. If the
request is now impossible, move it out of core rather than silently drop a requested detail.
Witness agreement supplies bounded checks, not a general equivalence proof.

Allowed core invariance controls: schema property ordering, compact versus readable serialization,
and consistent bijective renaming of tool/property identifiers across schema, request, gold and
references. Renamed outputs are compared after the recorded inverse mapping. Reference inlining,
$defs extraction and allOf flattening are allowed only in a reviewed subset with preserved base-URI,
scope, reference targets and assertions. Reject unknown keywords or unsafe rewrites. Do not
assume flattening a node is safe when outside references point into it.

### Description-grounding pairs

Only annotations/documentation change: units, roles, conventions or explicit mappings. Schemas
must be byte-equivalent after **schema-aware** annotation removal, and both distinct golds must
validate against both schemas. Such pairs measure API-description reading, not assertion-keyword
understanding. Label arithmetic and date arithmetic separately, including cases where the request
already supplies the computed answer. Description ablation remains a separately designed control.

Drafts receive two independent checks: (1) schema/gold/matrix verification and (2) request meaning
and answer-predicate review. A second model, if used, gets no author gold initially and cannot
resolve disagreements by majority vote alone; a human adjudicates. Do not select examples using
the future evaluated model's failures. Accepted test gold must not reach the inference interface.

## 6. Dialects, validation and engine capability

New authored core schemas use JSON Schema draft 2020-12 with explicit `$schema`. Preserve original
dialects for imported sources and validate with the corresponding pinned validator. Dialect
migration is a separate control, not an automatic rewrite of raw schemas. Pin validator version,
reference registry, format-assertion policy and exact schema bytes before dataset freeze.

Resolve references from an immutable local registry; no network resolution during validation or
inference. Record `$id`, anchors and base URIs. Pin a finite-value policy and format checkers with
task-independent conformance tests. An unsupported or ambiguous dialect is a dataset gate failure.

For every engine/version/serialization option and complete request envelope, require model-free:

1. Schema/envelope compilation and explicit refusal reasons.
2. Schema-ordered and alternative-order gold reachability, not just canonical gold.
3. Validator-rejected negative witnesses for each assertion and branch, including missing required
   fields, wrong types, extra fields, array positions, branch overlap and conditional/dependency violations.
4. Reachability probes for renamed and property-order variants; separate accepted-invalid cases
   from rejected-valid cases. Rejection alone cannot prove enforcement.
5. Native token-level boundary and legal-prefix checks using the exact bundled helper/build hash,
   followed later by separately budgeted online smoke. Character-level PyPI checks do not establish
   the native server's behavior.

Publish a capability manifest **before any model outputs**: full coverage, unsupported schemas,
accepted-invalid witnesses, order restrictions and the frozen comparison subsets. Never relax an
assertion to pass the gate or swap engines after observing accuracy. Raw-schema validation remains
authoritative; any constraint-copy lowering needs a reviewed equivalence argument and regression tests.

The full dataset and each frozen supported subset must be reported separately. Constrained
comparisons may cover only their predeclared common supported subset, with its own sample-size
check; unsupported cases cannot disappear from coverage totals. A confirmatory campaign does not
launch if its declared subset fails enforcement or power requirements. Free-generation exploratory
results on unsupported schemas do not demonstrate constrained support.

## 7. Future baseline and measurement proposal, not run authorization

Use untuned Qwen3-1.7B with raw schemas as the first small-model baseline; require a fresh reviewed
campaign/config for all runtime settings and budgets. Preserve the E0 profile as a reference,
but do not silently assume its context/output caps are adequate for larger v2 prompts. Enumerate
token budgets and any necessary change before lock. No current server is started by this design.

Compare matched free and constrained arms. A deployable V baseline uses strict parsing and raw
validation of its free answer, retries once only on invalid output, and never reads gold, eval fields
or correctness. Charge all attempts. An oracle-order arm may be a labelled diagnostic, never the
deployable system or the basis of a cost claim. Fixed separators and schema-order variants are
recorded options, not silent fixes. Laya/Jev-style routing can be later comparators but does not by
itself establish correct argument generation.

Primary future score: intent-weighted end-to-end correctness, averaged within intent across the
predeclared catalog sizes and pair members. Keep track weights fixed (500/150/150 test mix unless
amended before freeze), publish each track and size separately. Stress outcomes also include
**pair-correct** (both members correct), invariance under sound rewrites, and order/renaming stability.
Matching two wrong answers is not correctness; keep consistency and correctness separate.

If training is later authorized, propose one primary tuned-versus-untuned deployable-system
comparison: at least +5 percentage points with a two-sided 95% interval excluding zero. Proposed
secondary tests cover keyword pair-correct, grounding pair-correct and order sensitivity, using
a separate Holm family; multiplicity and exact contrasts must be locked in that campaign. Report
whether gains survive order controls rather than merely teaching the engine's preferred sequence.
No tuned arm, training corpus or training run is created here.

Resample structural lineage components, then intents within components, keeping all paired arms,
schema variants, catalogs and paraphrases together. Use at least 10,000 seeded hierarchical bootstrap
replicates; publish equal-intent estimates, family-weighted sensitivity and an intent-only sensitivity.
Do not use row-level McNemar as independent confirmatory evidence. Few or badly imbalanced families
can invalidate this plan; calibrate the estimator on development only and amend before freeze.

A future cheaper-tool-calling claim needs its **own** non-inferiority and cost protocol, not the
five-point superiority calculation above. Proposed reliability margin: two percentage points versus
a pinned stronger reference, justified for the application and powered before use. Require the
one-sided 97.5% lower bound above −2 points plus a paired cost-ratio upper bound below 1. These
are intersection requirements; both must hold. Label this proposal rather than a proven margin.
Name the reference/model/version, hardware and price snapshot before running anything.

Measure all routing, schema compilation, validation, retries, fallbacks and failed/uncertain calls;
report cost per request and cost per successful request, success rate, tokens, uncached/cached
latency separately and resource observations. Local tokens are not dollars: state runtime,
energy/hardware assumptions or limit the claim to tokens/latency. API list prices alone do not
make local and cloud costs comparable. No cost-reduction conclusion follows from E0b's 1.11× tokens.

Strict diagnostics retain overlapping flags and primary precedence:
`engine_refusal > cd_truncated > invalid > wrong_tool > lookalike_key > valid_wrong_value > correct`.
A mechanical look-alike flag does not override a valid accepted semantic answer; retain the flag,
matched declared key and both raw-validation/correctness verdicts. Never repair keys for scoring.
Legal-prefix truncations are scored failures, not automatic engine faults. Pending prefix checks
pause reporting; confirmed illegal prefixes and fresh engine/request faults stop the campaign.
Any later run must explicitly retain durable ledgers, exact resume keys and reviewed Mac resource
guards, including admission, pauses and hard swapout-growth stops.

## 8. Artifact and freeze contract

Proposed new dataset artifacts, in a future v2 namespace outside frozen experiment/:

- `sources.jsonl`: licence, upstream revision, retrieval hash, source group and exposure status.
- `schemas.jsonl`: dialect, raw bytes/hash, constraint copy/hash, references and transformation proof IDs.
- `tasks.private.jsonl`: intent/pair/track IDs, request, allowed tool IDs, semantic gold/predicate,
  reviewer/adjudication records and full validation matrix. Labels remain inaccessible to inference.
- `tasks.public.jsonl`: only request-visible fields; schema/catalog IDs with no gold/eval leakage.
- `splits.json`: graph version, lineage components, source holdouts, seeded assignments and audit findings.
- `catalogs.json`: exact distractors/presentation order, token lengths and deterministic selection inputs.
- `capabilities.json`: engine/native build/serialization hashes and all positive/negative probe verdicts.
- `MANIFEST.json`: hashes of every input, scripts/dependencies/template/tokenizer versions, review signoffs,
  registered metrics, exclusions, proposed request counts and separate smoke/benchmark/retry caps.

All pair members, paraphrases and order/renamed variants share a split. Gold/predicate files may be
released with the scientific artifact but must be excluded from the runner's input capability; do
not call a publicly exposed test set confidential. Version and retire any test exposed during tuning.
Freeze dataset bytes and the protocol before inference; preserve every later amendment and stop.
No model-output-dependent difficulty filtering, subset switching or interim accuracy looks.

## 9. External examples and next review gates

[stress-fixtures-0.4.zip](https://github.com/user-attachments/files/34879814/stress-fixtures-0.4.zip),
SHA-256 `8bb8ab2ac1553bf7bc3ae068e615e23d776ddb0a8c2550d4cde82e206fad1132`, is a public external
example bundle, **not a dataset**. Its 20 core pairs, one future control and 25 flattening checks
are exposed design examples. Keep them and descendants out of locked test. No bundle code is
copied into this delivery. Included PyPI-engine findings are the author's external evidence,
not a reproduced native capability result. The ZIP hash was independently checked for this design.

Review sequence:

1. **Now:** review this specification and the power assumptions; no models or task authoring.
2. **Later explicit instruction:** inventory sources, author and independently review candidate
   tasks, implement validators/leakage audits, and supply a model-free dataset-readiness report.
3. **Separate approval:** lock a development-only pilot if needed for power/runtime calibration;
   no locked-test access, and no training by implication.
4. **Dataset review:** freeze sufficient held-out components and capability subsets, task contracts,
   effect/cost hypotheses and full execution budgets; document unresolved gaps.
5. **Only then consider E1/E2:** a separate training/campaign review and explicit authorization.

**Current gate: design and independent candidate review. Provisional drafts are not a frozen v2
dataset; no new model campaign, cost result or training result exists.**
