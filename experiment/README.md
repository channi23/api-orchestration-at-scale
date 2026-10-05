# Representation experiment v1 — does tool-schema representation change tool use?

Single controlled variable: **how the tool catalog's schemas are represented** in the prompt.
Model, decoding, system prompt wording, tool catalog, tool names, tasks, evaluator and mock
execution are identical across conditions. No retrieval, discovery, MCP, planning, extra agents or
training. Scope and decisions: [`PLAN.md`](PLAN.md), [`DECISIONS.md`](DECISIONS.md).

**Status: complete.**
- Main run `runs/full-v2`: 3,000 requests, all HTTP 200, 0 context failures.
- Latency run `runs/latency-v2`: 50 requests, secondary/exploratory.
- Pilot: `runs/pilot-v1` and `runs/pilot-uncached-v1`. Determinism was 48/50 byte-identical with 50/50 identical E2E outcomes.
- Run incidents (an OOM-aborted first attempt and a container restart) are documented in `DECISIONS.md`.

### Results (authoritative)
| file | content |
|---|---|
| [`analysis/full-v2/RESULTS.md`](analysis/full-v2/RESULTS.md) / `results.json` | all tables, paired statistics, failure taxonomy, latency |
| [`analysis/full-v2/REPORT.md`](analysis/full-v2/REPORT.md) | final report: answers to the 10 research questions, limitations, recommendation |
| [`analysis/full-v2/SUMMARY_STE.md`](analysis/full-v2/SUMMARY_STE.md) | controlled-language summary (~80% ASD-STE100) |
| [`analysis/full-v2/figures/`](analysis/full-v2/figures/) | required plots 1–5 and `experiment_diagram.svg` |
| [`analysis/full-v2/explainer.html`](analysis/full-v2/explainer.html) | offline interactive explainer (open locally in a browser) |

- Every number in REPORT, SUMMARY, diagram and explainer is resolved by provenance key from `results.json` or the frozen artifacts (`src/provenance.py`); an unknown key is an error.
- The explanatory views are not separate sources of truth.
- Rebuild all outputs from the run artifacts with `scripts/make_outputs.sh` (no model calls).

**Headline (observed; Qwen3-1.7B only):**
- E2E success pooled over sizes: Raw 82.4%, TSCG 56.6% (−25.8 pp, 95% CI [−32.8, −18.2], exact McNemar p = 3.3e-30).
- Tool selection was unchanged.
- Raw-minified and Normalized did not differ detectably from Raw.
- Details and caveats are in REPORT.md.

**Latency (secondary/exploratory):** measured in a separate uncached sub-run. It was reduced before the
run from the planned 250 requests to **50** (2 fixed tasks × every catalog-size × representation cell),
because latency is secondary and nearly deterministic for a fixed prompt length. Individual
observations and per-cell medians are reported; this sample isn't equivalent to the 250-request design.
See `DECISIONS.md`.

## Conditions (5 arms)
| arm | what the model sees for each tool |
|---|---|
| `raw` | original JSONSchemaBench schema verbatim as `parameters`, JSON indent=2 |
| `minified` | identical content, compact JSON (token-reduced, information-identical control) |
| `normalized` | local `$ref` inlined, `definitions`/`$defs`/`$schema`/`$id`/`$comment` removed |
| `tscg` | official `@tscg/core@1.4.3`, `compress([tool], {model:'qwen-3', profile:'conservative'})` |
| `tscg_info` | JSON Schema holding **exactly the information TSCG keeps** (information-matched control) |

How the arms decompose the effect:
- `raw` → `tscg_info` measures the effect of the information TSCG removes.
- `tscg_info` → `tscg` measures the effect of TSCG's text format at fixed information.
- `raw` → `minified` measures the effect of token count at fixed information.

## Design
- **Data:** JSONSchemaBench @ `9a94995` (9,558 schemas) feeds an audit (`dataset/AUDIT.md`) and eligibility filter (4,219 eligible).
- **Pool:** a seeded ranking and a rank-ordered manual plausibility review (`dataset/review_log.v1.txt`) yield 300 tools (`dataset/tool_pool.v1.jsonl`; 174 flat, 126 structured). Each tool has a frozen name, description and function family.
- **Catalogs:** 10 replicates × sizes 5/10/20/50/100, **nested** (Catalog_k = first k tools). Each catalog is balanced 50/50 flat/structured, holds at most one tool per function family, and is presented in a seeded order that is identical across arms (`catalogs/catalogs.v1.json`).
- **Tasks:** 100 frozen tasks (`tasks/tasks.v1.jsonl`).
  - 50 target tools × 2 paraphrases. Each replicate's 5 targets appear in all of its catalog sizes, so **each task is paired across arms and across sizes**.
  - Gold arguments validate against the raw schema. An automated leakage audit is clean.
- **Two task families:**
  - `select`: full catalog shown. Measures tool selection, arguments, schema validity, mock execution and E2E success.
  - `arggen`: only the gold tool is shown and named. Measures argument generation with the tool fixed.
- **Evaluation** (`src/evaluate.py`):
  - JSON validity, then tool correctness.
  - Schema validity against the **raw** schema.
  - Argument exact match, field accuracy and semantic correctness.
  - Deterministic mock execution (receipt hash). E2E success.
  - Primary and secondary failure category.
- **Model:** Qwen3-1.7B Q8_0 (official GGUF) on llama.cpp `11fe021` (`config/model.json`). Greedy decoding (T=0, top-k 1, seed 0), thinking disabled, 512 max new tokens, 32k context.
- **Statistics** (`src/analyze.py`):
  - Exact McNemar on paired outcomes, with Holm correction for secondary comparisons.
  - 95% CIs from a cluster bootstrap over replicates.
  - Discordant-pair odds ratio, and a GLM with a log-token covariate.
  - Degradation point: the first catalog size significantly below size 5 on the same tasks.

## Reproduce
```bash
cd experiment
scripts/setup.sh                       # dataset@pin, TSCG@pin, llama.cpp@pin, model (pins revision+sha256)
python3 src/audit.py && python3 src/select_pool.py && python3 src/compile_pool.py
python3 src/build_catalogs.py && python3 src/build_tasks.py && python3 src/build_representations.py
python3 tests/test_evaluate.py         # evaluator self-tests (gold passes, perturbations classified)
scripts/start_server.sh                # llama-server with frozen args
python3 src/count_tokens.py            # model-tokenizer token counts for every tool/catalog/arm
python3 src/run.py --config config/runs/pilot.json            # PILOT (300 requests)
python3 src/run.py --config config/runs/pilot_uncached.json   # determinism + uncached latency check
# after pilot review:
python3 src/run.py --config config/runs/full.json --run-id full-v2   # 3,000 requests (~19 h on 4 CPUs)
python3 src/run.py --config config/runs/latency.json          # 50 uncached requests (secondary)
python3 src/run.py --config config/runs/latency.json --run-id latency-v2
scripts/make_outputs.sh                # analysis, report, summary, diagram, explainer
```
- The pipeline steps are deterministic. The frozen human-authored inputs are `dataset/review_log.v1.txt` and `tasks/tasks_source.v1.json`.
- Runs are append-only and resumable, keyed by run ID. They store the system prompts, raw outputs, usage, server timings and evaluations.

## Layout
`config/` frozen configs · `dataset/` audit, ranking, review log, pool · `catalogs/` · `tasks/` ·
`representations/<arm>/` per-tool renderings (+ TSCG runner, information audit, manifest) · `src/` pipeline ·
`tests/` evaluator tests and **smoke-test-only** fake server · `runs/` run artifacts · `analysis/` results, plots.
