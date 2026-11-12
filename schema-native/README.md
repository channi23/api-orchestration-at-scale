# schema-native — stage 0

Follow-up to `experiment/` (representation experiment v1). Nothing in `experiment/` is changed.
This folder reuses its frozen tasks, catalogs, prompts, evaluator and statistics by import.

**Question.** Can a small local model learn JSON Schema semantics that transfer to schemas it has
never seen, and does that add anything once constrained decoding is already in place?

**Status.** Stage 0 is done and tested. Stages 1–3 are written but need an Apple Silicon Mac and
model weights, which the authoring environment did not have. The table says which is which.

| Part | File | State |
|---|---|---|
| What constrained decoding could fix (from stored outputs) | `sn/ceiling.py` → `analysis/ceiling-full-v2/` | **run, real numbers** |
| Engine audit: can each engine produce the gold call? | `sn/engine_audit.py` → `analysis/engine-audit/` | **run, real numbers** |
| BM25 shortlist floor for tool selection | `sn/shortlist.py` → `analysis/shortlist-bm25/` | **run, real numbers** |
| Leakage-safe training schema pool | `sn/trainpool.py` → `data/trainpool/` | **run, real numbers** |
| Tool-call envelope for constrained decoding | `sn/envelope.py` | tested |
| Runner with free / constrained arms | `sn/run.py` | tested against a fake server only |
| Report (tables, paired statistics) | `sn/report.py` | tested against fake data only |
| Confidence metrics (ECE, Brier, risk–coverage) | `sn/calibration.py` | tested |
| Training-data synthesis with a local teacher | `sn/synth.py` | tested against a fake teacher only |
| MLX-LM chat training files | `sn/mlxdata.py` | tested on toy rows only |
| Chat-template check before training | `sn/preflight_template.py` | **not run** |
| Mac setup, serving, LoRA training, GGUF export | `scripts/*.sh`, `configs/lora.qwen3-1.7b.yaml` | **not run** |
| Demo CLI | `sn/demo.py` | run against a fake server only |

No model was run for this stage. No accuracy number for a new arm exists yet.

## Stage 0 findings (measured)

All from the 3,000 stored outputs of `experiment/runs/full-v2` or from model-free checks.

1. **The finished experiment's headline numbers reproduce** from the raw result file
   (Raw 82.4%, TSCG 56.6%, selection 96–98%). `tests/test_ceiling.py` asserts this.
2. **Constrained decoding has a hard upper bound of about +7.6 points on Raw.**
   Of 88 Raw failures: 11 malformed, 27 schema-invalid, 8 wrong tool, 42 schema-valid with a wrong value.
   A grammar can only touch the first two groups. Best case 82.4% → 90.0%. If it only rescues outputs
   whose values were already right: 82.4% → 83.0%. See `analysis/ceiling-full-v2/CEILING.md`.
3. **About half of the remaining errors are semantic and out of reach of any grammar** (42 of 88).
   Examples: `"GERMANY"` where the request implied `"DE"`, `name` used where `title` was meant,
   `"null"` as a string, `"acme/webapp"` in a field that wanted `"webapp"`.
4. **Engines differ before any model runs.** On the 50 target tools, the gold call can be produced by
   llguidance 1.9.1 for 50/50, by xgrammar 0.2.9 for 47/50, by outlines_core 0.2.14 for 46/50.
   Across all 300 tools they compile 292, 298 and 287 schemas. See `analysis/engine-audit/ENGINE_AUDIT.md`.
   (outlines_core was checked through its generated regular expression with Python's `re`; confirm in-engine.)
5. **Tool selection on this benchmark is lexically easy.** BM25 over tool name + description puts the
   gold tool first for 93% of tasks at 100 tools and in the top 3 for 100%. The model scored 92% there.
   A learned selector cannot show an accuracy gain on these catalogs. See `analysis/shortlist-bm25/SHORTLIST.md`.
6. **The task set is small for training comparisons.** 50 target tools, intra-tool correlation 0.44,
   effective sample size about 102 of 500. Five tools hold 47% of all Raw failures.
7. **The frozen pool does not contain the hard keywords.** `if/then/else`, `not`, `unevaluated*` and
   recursion appear in 0 of 300 tools; `oneOf` in 5 (1 target, 0/10 correct). Any claim about those
   keywords needs a new stress set.
8. **1,983 schemas are safe to train on** (1,761 train / 207 validation / 15 held-out source), in 1,402
   families, after removing the 300 test tools and everything close to them.

## Run the model-free part (any machine)

```bash
cd schema-native
pip install -r requirements.txt
../experiment/dataset/fetch_jsonschemabench.sh
python -m pytest -q                 # 21 tests
python -m sn.ceiling                # analysis/ceiling-full-v2/
python -m sn.engine_audit           # analysis/engine-audit/      (about 4 minutes)
python -m sn.shortlist              # analysis/shortlist-bm25/
python -m sn.trainpool              # data/trainpool/
```

## Run on the Mac (not yet executed — report what breaks)

```bash
scripts/setup_mac.sh                        # venv, pinned llama.cpp with Metal + llguidance, base GGUF, tests, template check
scripts/serve.sh                            # base Qwen3-1.7B Q8_0 on :8080

# E0 — untuned model, free vs constrained decoding (1,200 requests)
python -m sn.run --config configs/runs/e0_decoding.json --run-id e0-v1
python -m sn.report --run e0-v1

# one request, with everything shown
python -m sn.demo --task T008_p0 --catalog C020_R00 --constrained
```

Training (only after E0 is read; see `PLAN.md` for the gate):

```bash
scripts/serve.sh /path/to/teacher.gguf 8081            # a larger local teacher, e.g. a 4-bit 8B model
python -m sn.synth --server http://127.0.0.1:8081 --split train --per-schema 2
python -m sn.synth --server http://127.0.0.1:8081 --split valid --per-schema 1
python -m sn.mlxdata --representation raw && python -m sn.mlxdata --representation minified
scripts/train_lora.sh minified && scripts/fuse_to_gguf.sh minified
scripts/train_lora.sh raw      && scripts/fuse_to_gguf.sh raw

python -m sn.run --config configs/runs/e1_lora.json --run-id e1-v1 --arms A_raw_free B_raw_cd Bm_min_cd
scripts/serve.sh models/qwen3-1.7b-lora-raw-Q8_0.gguf
python -m sn.run --config configs/runs/e1_lora.json --run-id e1-v1 --arms C_raw_lora_free
scripts/serve.sh models/qwen3-1.7b-lora-minified-Q8_0.gguf
python -m sn.run --config configs/runs/e1_lora.json --run-id e1-v1 --arms D_min_lora_free E_min_lora_cd
python -m sn.report --run e1-v1
```

## Memory on 16 GB (estimates, not measurements)

- Qwen3-1.7B weights: about 3.4 GB at 16-bit, about 1.8 GB as Q8_0 GGUF.
- Inference context: roughly 0.1 MB per token of key/value cache at 16-bit, so about 1.6 GB at 16k
  tokens and about 3.2 GB at 32k. The 100-tool Raw prompt is 27k tokens; it fits, but close other apps.
- LoRA training at batch 1, 3,072 tokens, 16 layers, gradient checkpointing: expected well under 10 GB.
  `scripts/train_lora.sh` records the real peak with `/usr/bin/time -l`. Report that number.
- The teacher for data synthesis is the largest item. A 4-bit 8B model needs about 5–6 GB. Do not run
  the teacher and training at the same time.

## Design choices that differ from the brief, and why

- **Arm D's "lossless representation" is minified JSON.** It is lossless by construction, it is the
  strongest baseline the finished experiment found (same accuracy, about 40% fewer tokens), and it adds
  no new syntax. A newly invented notation would confound "understands schemas" with "learned a new
  format"; the finished experiment already measured a format penalty of −5.8 points at equal
  information. A compact typed notation stays an optional later ablation.
- **Inference for every arm goes through one server (llama.cpp, Metal).** MLX-LM is used for training.
  `mlx_lm.server` 0.32.2 has no JSON-Schema constraint, so mixing back-ends would mix engines.
- **Arm F (decision model + LLM) is not built yet.** Finding 5 says this benchmark cannot show a
  selection gain. `sn.shortlist` is the floor any selector must beat; `sn.calibration` is ready for it.
