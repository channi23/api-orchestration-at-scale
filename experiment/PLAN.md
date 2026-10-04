# Representation Experiment v1 — Inspection Findings & Implementation Plan

Status: **awaiting approval. No experiment code has been written yet.**
Scope: Stage 5 / RQ5 of the proposal, cut down to a single controlled variable, **schema representation**.
Out of scope: training, retrieval, progressive discovery, MCP, planning, multi-agent setups, Blaze.

---

## 1. Inspection findings

### 1.1 Repository
- At inspection time the repo held only an empty `README.md` and the draft proposal `.docx`. Nothing had been implemented.
- The proposal names Qwen3 1.7B as the first compact model (§8.5). It requires end-to-end success as the primary metric (Step 5) and token-matched controls (§8.7, Step 20).

### 1.2 JSONSchemaBench
- Source: https://github.com/guidance-ai/jsonschemabench, commit `9a94995b9279ae3af3aed4b2629172790b968d14` (2026-09-28). The HF mirror `epfl-dlab/JSONSchemaBench` is blocked by the egress proxy, so the GitHub copy is the version we use.
- **9,558 schemas.** This matches the figure in the task brief: Glaive 1707, GH-trivial 444, GH-easy 1943, Snowplow 403, GH-medium 1976, Kubernetes 1064, WaPo 125, GH-hard 1240, JSONSchemaStore 492, GH-ultra 164.
- The upstream README flags 13 Glaive schemas as unsatisfiable (issue #16). They will be excluded.
- The preliminary keyword audit (`experiment/dataset/audit_preliminary.py`) produced the table below. These are keyword-presence counts. "Nested" means properties at depth 2 or more.

| subset | n | top-level object w/ props | title/desc | $ref | nested | array | enum | oneOf | anyOf | allOf | if | pattern | format |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Glaiveai2K | 1707 | 1707 | **0** | 0 | 1257 | 496 | 206 | 51 | 3 | 0 | 0 | 0 | 149 |
| Snowplow | 403 | 386 | 365 | 3 | 166 | 136 | 105 | 24 | 18 | 0 | 0 | 54 | 403 |
| WashingtonPost | 125 | 75 | 124 | 77 | 35 | 61 | 69 | 24 | 26 | 29 | 0 | 31 | 0 |
| Github_easy | 1943 | 1713 | 1155 | 281 | 476 | 648 | 467 | 98 | 79 | 35 | 1 | 236 | 180 |
| Github_medium | 1976 | 1798 | 1144 | 515 | 1132 | 1141 | 888 | 230 | 101 | 55 | 4 | 573 | 397 |
| Github_hard | 1240 | 1153 | 590 | 604 | 1014 | 980 | 883 | 364 | 377 | 73 | 8 | 602 | 467 |
| **TOTAL (all 10)** | 9558 | 8622 | 5171 | 2771 | 4547 | 4793 | 3497 | 1398 | 874 | 346 | 53 | 1802 | 2018 |

- Median pretty-printed size: Glaive about 790 chars, GH-easy about 680, Snowplow about 1,300, GH-medium about 2,100, GH-hard about 7,800, Kubernetes about 3,300 (heavy tail). Kubernetes, GH-hard, GH-ultra and JSONSchemaStore schemas are mostly whole config documents. They do not plausibly work as tool inputs and they blow up the context at 50–100 tools.
- **Glaive schemas have no tool name or description.** Upstream stripped them and kept only `parameters`. Many GitHub schemas also lack a usable title. Every tool therefore needs a generated name and description (see §3, decision D3).

### 1.3 TSCG (official)
- Repo: https://github.com/skzl-ai/tscg, HEAD `51378d6c` (2026-07-03), tag `v1.4.3`. The npm package `@tscg/core@1.4.3` installs fine (the npm registry is reachable) and runs under Node 22. Invocation: `compress(tools, {model, profile, principles})`. The output is one text block for the whole catalog.
- What TSCG actually does was checked against the source and confirmed empirically:
  - `normalizeToInternal` keeps **only top-level `properties`** with `name`, `type`, `description`, `required` and `enum`.
  - It **drops** nested `properties`, array `items`, `$ref` targets (a `$ref` param becomes `type: string`), `oneOf/anyOf/allOf`, `minimum/maximum`, `pattern`, `format`, `default` and `additionalProperties`. Example: a Glaive schema `data: array<{measurement, timestamp, value}>` becomes `data (array) (required):` and the item structure is gone.
  - SDM rewrites descriptions by removing filler patterns, so the descriptions change too.
  - `balanced` applies CAS, which **reorders tools** (U-shape), and CCP, which appends a `[CLOSURE:…]` line.
  - `profile:'auto'` picks **different principles by catalog size** (≤20 conservative, 21–40 balanced without CFL/CFO, >40 conservative). Even `balanced` silently turns off CFL/CFO at ≥30 tools.
  - `metrics.tokens` is a chars/token **estimate**, not a real tokenizer.
- Conclusion: TSCG changes **information**, not only format, for any schema with structure below the top level. Attributing an effect to "compression" requires a control that holds information constant (§2.4).

### 1.4 Model and compute (**blocker**)
- Hardware: 4 vCPU Xeon (AVX-512, AMX), 15 GB RAM, no GPU. cmake and gcc are present, so llama.cpp can be built from GitHub source.
- The egress proxy **blocks huggingface.co, cdn-lfs.huggingface.co, hf-mirror, modelscope, ollama registry, and download.pytorch.org.** There is no way to obtain open model weights or the Qwen tokenizer.
- `api.anthropic.com` is reachable, but **no API key is configured.**
- So right now no model can be run, local or external. The experiment cannot proceed past dataset, catalog and representation construction until one of the options in D1 is enabled.

---

## 2. Experimental design (proposed)

### 2.1 Schema pool (deterministic)
- Subsets: Glaive, Snowplow, WashingtonPost, GH-trivial, GH-easy and GH-medium. Kubernetes, GH-hard, GH-ultra and JSONSchemaStore are excluded as configuration documents rather than inputs, and as context-infeasible. The exclusion is documented and counted.
- Inclusion requires all of:
  - the root is an object with 1–15 top-level properties;
  - the schema is satisfiable (it is not one of the 13 known-bad schemas, and a hand- or generator-produced instance validates);
  - there are no remote `$ref`s and no cyclic `$ref`s;
  - the pretty JSON is at most 2,500 chars, so that 100 raw tools fit the 32k context;
  - the schema is not a near-duplicate (canonical-JSON hash plus a property-set Jaccard threshold).
- Strata, recorded per schema:
  - **flat**: TSCG is lossless apart from description rewriting and dropped constraints;
  - **structured**: nested objects, arrays of objects, `$ref`, or unions, so TSCG is lossy.
- Every schema gets a feature vector: depth, #props, #required, enum, $ref, unions, constraints, size.

### 2.2 Catalogs: nested within each replicate, so tasks are paired across sizes
- R = 10 replicates.
- For replicate r, a seeded draw produces an ordered list of 100 tools, stratified about 50/50 flat/structured and across subsets.
- Catalog_k_r is the first k tools, for k ∈ {5, 10, 20, 50, 100}. The presentation order is shuffled per catalog with a recorded seed and is identical across representations.
- Task targets are tools #1–5 of each replicate. **The same tasks are therefore evaluated at every catalog size**, and only the number of distractors changes. This gives paired comparisons across sizes as well as across representations.
- Near-duplicate distractors of a target are rejected so the correct tool stays unambiguous.

### 2.3 Tasks
- 50 target tools, each with 2 paraphrased intents, giving **100 tasks**.
- Each task record has: `task_id`, `schema_id`, `catalog_ids`, `gold_tool`, `prompt`, `gold_args`, `acceptable_variants`, `task_relevant_fields`, `gen_seed` and `gen_config`.
- `gold_args` must validate against the raw schema. Structured targets require nested or array arguments.
- An automated leakage audit checks every prompt against: the tool name and its tokens, the schema ID or filename, subset names, representation names, and verbatim tool-description n-grams.

### 2.4 Representation conditions (same tool order, names and descriptions wherever the format allows)
| cond | content |
|---|---|
| **RAW** | original schema, `json.dumps(indent=2, sort_keys=False)` |
| **NORM** | local `$ref` fully inlined, `definitions/$defs` removed, `$schema/$id/$comment` removed, same serialization as RAW. This is practical with a small deterministic dereferencer, since cyclic refs are excluded upstream. |
| **TSCG** | official `@tscg/core@1.4.3`, one pinned profile (D2), output used verbatim |
| **JSON-TSCGINFO** (information-matched control) | JSON Schema rebuilt from **exactly** the fields TSCG retains: top-level name, type, required, enum and the original description. It has the same information as TSCG in JSON format. |

How the conditions split the effect:
- RAW vs JSON-TSCGINFO estimates the effect of **information removal**.
- JSON-TSCGINFO vs TSCG estimates the effect of **format/compression** at fixed information.
- Token count is reported as a covariate in every comparison.
- This control does not delete information arbitrarily; it deletes exactly what TSCG deletes. I recommend it over plain RAW-minified, which is still far above TSCG's token budget. RAW-minified can be added cheaply as a fifth arm if you want it.

### 2.5 Prompting and output
- Every representation goes into the **system prompt as text** under an identical wrapper. No native tool-calling API is used, because it would require JSON schemas and would make the conditions differ.
- The model must answer `{"tool": "<name>", "arguments": {...}}`.
- There is one parser, and malformed output is classified, not repaired. This mirrors how TSCG is intended to be used and is the same for every arm.
- Two task families:
  1. **Selection + arguments → E2E**: full catalog; parse, validate, run the mock, evaluate.
  2. **Argument generation (tool fixed)**: only the gold tool, in that condition's representation, with an instruction naming the tool. Run once per task per condition, since it does not depend on catalog size.

### 2.6 Mock execution and metrics
- The mock validates arguments against the **raw** schema (jsonschema, using the schema's declared draft). It returns a deterministic result: a hash of the canonicalized task-relevant arguments.
- E2E success means the result equals the expected result.
- Honest caveat: with single-call mocks, E2E reduces to "JSON valid ∧ schema-valid ∧ correct tool ∧ semantically correct args". It is not an independent semantic oracle, and the report will say so.
- Metrics:
  - JSON validity, schema validity, tool-selection accuracy;
  - argument exact match, field-level accuracy over task-relevant fields, semantic correctness under documented normalization (numeric equality, enum exact match, whitespace and case-insensitive free text, acceptable variants);
  - E2E success;
  - input, output and total tokens, using the **model's own tokenizer** via llama.cpp `/tokenize`, or Anthropic `count_tokens` under the Claude option;
  - latency and transformation time.
- Failure taxonomy as specified in brief §16, with primary and secondary labels assigned by deterministic rules.

### 2.7 Statistics
- Pre-registered primary comparison: **RAW vs TSCG, E2E, pooled over sizes.**
- Paired tests: exact McNemar per comparison and size. 95% CIs on the paired difference come from a **catalog-cluster bootstrap**, because tasks within a replicate are correlated.
- Holm correction across the secondary pairwise comparisons. Effect sizes: odds ratio of discordant pairs and the absolute pp difference.
- Size trend: a logistic model with E2E ~ representation × log(size) + task random effect, if it converges, otherwise stratified McNemar.
- Power, stated up front: n = 100 paired tasks per size detects about 15pp differences. Pooled over 5 sizes (n = 500 paired, correlated) it detects about 7–8pp. Smaller effects will be reported as "not distinguishable".

### 2.8 Model (frozen before the main run)
- Recommended: **Qwen3-1.7B, GGUF Q8_0, llama.cpp `llama-server`** built from a pinned commit, CPU only.
  - Greedy decoding (temperature 0, top-k 1), seed 0, max output 512, 32k context.
  - Thinking disabled via `/no_think`, applied identically in every arm.
  - Record: model SHA, quantization, llama.cpp commit, threads and hardware.
- Prompt-prefix caching shares the catalog across the tasks in a cell, which keeps CPU runtime feasible.
  - The latency metric is taken from a **separate uncached sub-run**: 1 replicate × all sizes × all conditions.
  - The pilot checks that cached and uncached greedy outputs are identical, and the result is reported.
- Fallback (D1-b): Claude Haiku 4.5, temperature 0, labelled **"external/frontier-model representation reproduction"**, not the compact-model experiment.

### 2.9 Budget (main run, before the pilot calibrates throughput)
- Selection/E2E calls: 100 tasks × 5 sizes × 4 conditions = 2,000. Argument-generation calls: 100 × 4 = 400. Uncached latency sub-run: about 200. **Total about 2,600 calls.**
- Prefix tokens:
  - Raw at about 230 tokens per tool gives roughly 23k tokens per 100-tool catalog.
  - Summed over 10 replicates × (5+10+20+50+100) tools × 4 conditions (TSCG and INFO at about 25–40% of raw), that is roughly 1.2M prefill tokens. The total with tasks and the uncached run is about 2M input tokens.
  - Output is about 0.2M tokens.
- Local CPU, assuming roughly 150–300 tok/s prefill and 20–30 tok/s decode (to be measured in the pilot): **about 3–5 h** wall-clock, $0.
- Claude Haiku 4.5: about 2M input and 0.2M output tokens. At list prices that is on the order of a few dollars. I will confirm with the claude-api reference before running.
- **Pilot:** 2 replicates × sizes {5, 20} × 4 conditions × 10 tasks is about 160 calls. It exercises every part of the pipeline listed in brief §19.

### 2.10 Layout
```
experiment/
  README.md  PLAN.md  config/
  dataset/      (audit + selection scripts, selected_schemas.jsonl; the upstream repo is cloned at a pinned commit and not committed)
  catalogs/  tasks/
  representations/{raw,normalized,tscg,tscg_info}/
  runs/<run_id>/  (prompts, raw outputs, parsed, validation, failures, timings: immutable)
  results/  analysis/  (stats + plots + report)
```

---

## 3. Confounders to state explicitly
1. **TSCG loses information** for structured schemas (§1.3). This is handled with the JSON-TSCGINFO arm and the flat/structured stratification.
2. **TSCG rewrites descriptions** (SDM). Recorded as a per-tool diff.
3. **Tool order**: `balanced` (CAS) reorders tools and `conservative` does not. The gold tool's position is logged as a covariate.
4. **TSCG config varies with catalog size** under `auto` and `balanced`. Resolved by pinning (D2).
5. **Generated names, descriptions and tasks.** These are identical across conditions, so they cannot bias the RAW vs TSCG contrast, but they affect absolute accuracy and external validity. This benchmark has **real schemas with generated tasks and mocks**, not a real API workload.
6. **Context length**: raw at 100 tools approaches 32k. Overflow is classified as `context-length failure` and is not hidden.
7. **Prefix caching vs uncached** numerics. Checked in the pilot.
8. **Output format**: one JSON answer format for every arm. TSCG's own output is not JSON Schema, so models may handle nested argument construction differently. This is an inherent part of the manipulation.
9. Single model and a single tokenizer, so there are no cross-model claims.

---

## 4. Decisions needed before implementation
- **D1 — Model access (blocking).** Either (a) allow `huggingface.co`, `cdn-lfs.huggingface.co` and `*.hf.co` in the environment's network policy to run Qwen3-1.7B locally (recommended, matches the proposal), or (b) add `ANTHROPIC_API_KEY` as an environment variable for the Claude Haiku 4.5 "external/frontier reproduction".
- **D2 — TSCG profile.** Recommended: pin `profile:'conservative'` (SDM only, no reordering) at every size. It is what `auto` itself picks at ≤20 and >40 tools, and it keeps the configuration constant. The alternative is `balanced` with explicit principles, which reorders tools and keeps CFL/CFO on at 50–100 tools against the authors' small-model guidance.
- **D3 — Names, descriptions and tasks.** Recommended: I author them once in-session, freeze them as versioned artifacts, and they then pass the automated leakage and schema-validity audits. Reproducibility comes from the saved artifacts, not from regeneration. The alternative is a deterministic template generator: fully regenerable, but the prompts are unnatural and leak field names.
- **D4 — Approve** the scope: 4 arms (optionally 5 with RAW-minified), sizes 5–100, 10 replicates, 100 tasks, and the pilot first.
