# JSON Schema-native model research

E0 asks whether constrained decoding changes the untuned Qwen3-1.7B result on the frozen
benchmark. It uses one pinned model and server for all four conditions: raw/free, raw/constrained,
minified/free, minified/constrained. There are 1,200 requests: 100 tasks × four arms ×
(two selection catalogs, 5 and 20 tools, plus the fixed-tool argument condition).

**Current status:** Claude's stage 0 is merged. The pinned server and model run on a 16 GB Apple M4;
34 package tests and the 12-request real smoke complete. Runtime preflight finds 11/70 envelope
refusals in bundled llguidance 1.0.1. The frozen 1,200-request E0 is in progress; no complete
benchmark or training result is claimed yet. The original `experiment/` tracked files are unchanged.
`PLAN.md` contains the preregistered predictions and research gates.

## Model-free verification

Python 3.13 is the recommended Mac environment. Python 3.14 was used for the local tests.
Run from `schema-native/`:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-e0.txt
../experiment/dataset/fetch_jsonschemabench.sh
python -m pytest -q
python -m pytest -q ../experiment/tests/test_evaluate.py
python -m sn.preflight --offline --output runs/e0-offline.json
```

The offline check verifies all 1,200 unique requests, matching tasks across arms, catalog membership,
unique tool names, raw-schema gold validity and envelope gold validity. It cannot authorize inference.
The dataset is pinned at `9a94995b9279ae3af3aed4b2629172790b968d14`.

## Run E0 on a 16 GB Apple Silicon Mac

Prerequisites: Xcode command-line tools (`xcode-select --install`), Python 3.13, CMake and Rust/Cargo
(for example `brew install python@3.13 cmake rust`). Docker cannot expose Apple Metal here.
Close memory-heavy apps. Disk must hold the dataset, build, environment and about 1.8 GB GGUF.
Memory estimates in the source report remain estimates until this is run.

Get current main, preserve any local changes, then enter `schema-native/`. In terminal 1:

```bash
scripts/setup_mac.sh
scripts/serve.sh
```

Setup uses a project-local `.tools/llama.cpp` checkout, refuses tracked edits there, builds commit
`11fe02151f79c41d0d4af7da708755d73b9c0da6` with Metal and llguidance, and downloads
`Qwen/Qwen3-1.7B-GGUF`, revision `90862c4b9d2787eaed51d12237eafdfe7c5f6077`,
file `Qwen3-1.7B-Q8_0.gguf`. It verifies SHA-256
`061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`.
It installs E0 dependencies only. `SN_PYTHON` and `TOOLS_DIR` override the Python executable and tools
root; export `TOOLS_DIR` in both terminals if overriding it.

With `--jinja`, this pinned server lowers standard `response_format` through its GBNF autoparser.
E0 therefore sends the explicit `grammar` payload `%llguidance {}\nstart: %json <schema>` to select
llguidance while preserving the same chat prompts. Standard `response_format` remains supported
for compatible endpoints and synthetic tests; it is a distinct transport and is recorded in results.

The pinned llama.cpp bundles llguidance **1.0.1**, commit
`d795912fedc7d393de740177ea9ea761e7905774`; the standalone stage-0 audit used 1.9.1.
Preflight records and checks the bundled engine commit. These are distinct engine conditions.

The server stays in the foreground and logs to `runs/server.8080.log`. It never kills an existing
server. If port 8080 is occupied, stop the server you own before proceeding.
Wait until this succeeds, then in terminal 2, from `schema-native/`:

```bash
source .venv/bin/activate
curl -fsS http://127.0.0.1:8080/health
scripts/run_e0.sh e0-v1
```

The wrapper first runs online preflight and a **12-request path smoke**, then a separate online
preflight and the full E0. Smoke outputs are not accuracy evidence. Online preflight checks:

- GGUF checksum, clean pinned llama.cpp source, build flags, running build identity and model path;
- server log evidence of Metal and GPU layer offload;
- two adversarial constant/bounds probes to detect ignored constraints;
- detection of fresh `llg error` log entries, including HTTP-200 silent enforcement fallback;
- all 70 unique actual envelopes through the real server/tokenizer, with explicit engine refusals saved;
- each unique benchmark prompt through `/apply-template` and `/tokenize`, reserving all 512 output
  tokens within the actual context size. There are no silent truncation or fallback changes.

An explicit schema/grammar refusal is recorded separately from model failures. Auth, network,
context, malformed API-response and generic server failures stop a run after saving the failed
request. Correct the cause and use a **new run ID** for a clean result. Do not delete failed rows to
improve scores. If the process merely stops between requests, run the same command to resume.
Identical settings, input hashes, dependencies and server properties are required. Existing rows are
never overwritten; duplicate or unknown request keys are rejected. Concurrent writers are locked out.
A torn final JSONL line is rejected for manual inspection; never automatically discard experiment data.

Equivalent individual commands (useful when diagnosing a failure):

```bash
python -m sn.preflight --config configs/runs/e0_decoding.json --output runs/e0-preflight.json
python -m sn.run --config configs/runs/e0_decoding.json --preflight runs/e0-preflight.json --run-id e0-v1
python -m sn.report --run e0-v1
```

For a one-task demo (outside the benchmark):

```bash
python -m sn.demo --task T008_p0 --catalog C020_R00 --constrained
```

## Read the results

`runs/<id>/manifest.json` records configuration, source/input hashes, package versions, runtime
preflight evidence, expected request keys and server properties. `results.jsonl` preserves raw output,
finish reason, usage, latency, request failures and unchanged raw-schema evaluator results.
Prompts are stored compressed in the run directory.

`python -m sn.report --run <id>` writes `analysis/<id>/REPORT.md` and `report.json`:
tool accuracy, argument exact match, field accuracy, schema validity, semantic correctness, E2E,
strict E2E, tokens, p50/p95, and p99 only for cells with at least 200 returned requests. The five-way
model failure split is malformed, wrong tool, invalid only, invalid plus wrong value, valid but wrong
value. HTTP/context/engine/transport/response failures are separate, and all count as system failures.
The evaluator's semantic matching intentionally accepts specified variants and some scalar coercions;
exact match and strict E2E should be read alongside it.

Partial runs get descriptive tables and **no paired inference**. Complete runs get paired exact
McNemar and 95% catalog-replicate bootstrap intervals, pooled and by catalog size. The preregistered
primary pooled selection contrast is unadjusted; Holm correction covers secondary comparisons.
Catalog sizes/paraphrases share tools, so 1,200 requests are not 1,200 independent intents.
Cached, sequential latency is descriptive and must not be presented as an uncached speed comparison.

Stop the dedicated server with Ctrl+C after E0. `/usr/bin/time -l` then appends its lifetime maximum
RSS to the server log. Re-render with that measured value:

```bash
python -m sn.report --run e0-v1 --server-log runs/server.8080.log
```

RSS is process resident memory, not a Metal allocator peak. Without that evidence the report says
memory is unrecorded. Preserve the server log with run artifacts; separate server sessions if you
need run-specific memory measurements.

## Research gates and limits

E0 is instrumented and runtime-tested, but the benchmark readout is not yet complete. Read the real E0 before E1: ≥95% constrained accuracy
means harder tasks first; constrained below free means inspect engine faults and run a second engine.
Even a positive E0 does not establish unseen-schema learning. Test v2 (250 new intents), keyword stress
and impossible-request tasks remain to be authored and validated before a powered training claim.

The original `sn.synth`, `sn.mlxdata`, calibration, train-pool and E1 configuration are retained as
**unvalidated training scaffolding**. Training/export scripts intentionally stop with the gate message.
No new E1 work or E2 contrastive training has been performed. Revisit the Qwen3 thinking-template
mismatch check, training model/tokenizer revision pins, MLX API compatibility and fused GGUF export
when E0 and the new datasets are sound. E2 additionally needs unseen-schema invariance/sensitivity
pairs with independently checked gold answers; a validator alone cannot infer the user's intended value.

Stage 0 analyses remain in `analysis/ceiling-full-v2`, `analysis/engine-audit`, and
`analysis/shortlist-bm25`. `requirements.txt` installs the optional engine-audit dependencies;
`requirements-mac.txt` is deferred MLX training material. The earlier “90% ceiling” is a
classification-based rescue estimate, **not a mathematical bound**: token masking can also change
already-valid answers, for better or worse. The unchanged-valid-wrong count is a testable prediction.
The pool mixes dialects and engine keyword support is incomplete; raw-schema validation remains the
final authority. Gold-envelope checks do not prove full language equivalence or engine completeness.

The [E0 validation record](analysis/e0-readiness/VALIDATION.md) includes the standalone byte-tokenizer
check: 67/70 envelopes compile under llguidance 1.9.1, with three explicit refusals. This is a known
readiness limitation, not model inference; the real server may differ and must be checked online.
