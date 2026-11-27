# v2 exploratory Qwen baseline

On 2026-11-27, the untuned Qwen3-1.7B Q8_0 model completed all 177
free-decoding requests locally on a 16 GB M4 MacBook Pro. The frozen roster covers
93 intents. The exact-call score was **101/177 (57.1%)**, and the intended-tool
score was **169/177 (95.5%)**. Scores are descriptive for this run.

| Catalog | Requests | Intended tool | Intended tool and valid arguments | Exact call |
| --- | ---: | ---: | ---: | ---: |
| One tool, stress pairs | 48 | 48 | 32 | 27 |
| Five tools, API requests | 69 | 64 | 60 | 40 |
| Twenty tools, API requests | 60 | 57 | 53 | 34 |
| Total | 177 | 169 | 145 | 101 |

The largest failure class was a call to the intended tool with schema-valid wrong
arguments (44). Of those, 22 omitted at least one expected key. In one of the 22,
an omitted key's expected value matched its schema default annotation. There were
also 24 calls with invalid arguments and eight selections of the wrong tool.

On the same 60 API intents, 35 were exact with five tools and 34 with twenty.
Within the stress tracks, both variants were exact for 4/17 assertion pairs and
3/7 description-grounding pairs. Intent-weighted exact accuracy was 57.2% on API
intents, 52.9% on assertion pairs and 64.3% on grounding pairs.

## Execution and validation

- The first admission stopped at 4.81 GiB available with normal memory pressure.
  It spent zero requests. The next admission passed at 7.07 GiB.
- The runtime matched the 9,216-token smoke, offloaded all 29 layers to Metal and
  reached three consecutive normal pressure readings. All 177 prompt lengths matched
  the frozen range of 202 to 7,792 tokens. Every completion also reported its exact
  expected prompt length.
- The ledger records 355 of 360 allowed metadata requests and 177 of 177 allowed
  generation requests. The charged generation keys and completed responses each
  match the frozen order without duplicates. All replies finished with `stop`.
- The active segment took 21 minutes 53 seconds, including the settle window,
  preflight and cooldowns. The median request took 3.51 seconds. Total usage was
  527,593 prompt tokens and 10,496 completion tokens.
- Across 816 recorded resource samples, pressure was normal, thermal state was
  nominal and system swapout growth was zero. The server exited and its listening port
  closed before scoring. The post-unload check found normal pressure, nominal thermal
  state and 6.72 GiB available. Temperature and CPU/GPU utilization were not tracked
  continuously.

The frozen scorer ran offline against the private response ledger. The
[public aggregate](aggregate.public.json) gives counts and SHA-256 receipts.
Prompts, raw replies, gold answers and per-task scores stay local.
The [offline argument audit](ARGUMENT_AUDIT.md) breaks down wrong calls by added
fields, omitted fields and changed values.

```bash
umask 077
freeze=../../../outputs/v2-exploratory-freeze-v0.1
run_dir=runs/v2-exploratory-free-v0.1
.venv/bin/python -m sn.v2_holdout_score \
  --freeze "$freeze" \
  --manifest-sha256 837044af132bd981996749cef38509fa7056566be472b14ccaec1946d70ac7f6 \
  --responses "$run_dir/results.jsonl" --out "$run_dir/reproduced-score.private.json"
shasum -a 256 "$run_dir/reproduced-score.private.json"
```

The expected score file hash is
`ba9ede9b503384fe19d9f6a3c9b1ff95bcf7c96163b54d320484e302a77c9048`.
The offline score reproduced byte for byte. All 272 tracked tests passed
(252 package, 12 original evaluator and eight power-planning).

This run establishes a baseline for one model, one runtime and the frozen exploratory
set. A trained comparison, a confirmatory evaluation and a cost comparison remain open.
E1 and E2 stay gated.
