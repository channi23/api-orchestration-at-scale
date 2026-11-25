# Proposed v2 development inference pilot

**2026-11-25. Ready for separate run approval.** This is a short diagnostic of the unchanged
Qwen3-1.7B on already reviewed development requests. It measures completion behavior,
token counts, latency and which errors need attention before a larger campaign.
It supplies no held-out, cost, training or comparison claim. No model was loaded while
preparing this run.

| Item | Prepared scope |
| --- | --- |
| Inputs | 11 distinct development requests with five tools each |
| Source mix | Four original Stripe/PokéAPI requests, two revised requests replacing their original versions, five DigitalOcean requests |
| Decoding | One free-decoding call per task, tools and schemas in prompt text |
| Inference budget | 11 generation attempts, including failed or uncertain sends, with zero generation smoke calls and zero automatic retries |
| Model | Existing Qwen3-1.7B Q8_0 GGUF and pinned E0 sustainable profile |
| Runtime | Local Metal server, 8,192-token context, one slot, 512 output-token cap, greedy decoding and thinking disabled |
| Order | Source groups and task IDs listed in the run config, catalog order from the review packet |

The run config pins the three reviewed ZIPs, corresponding golds and adjudication receipts.
The local plan records their 11 selected tasks, implementation hashes, the E0 chat-template
hash, verified model/build hashes and run settings. The HTTP payload carries the visible
policy, tools, request and model settings. Gold is used only for scoring after every response
has been saved. No private held-out files are inputs to the pilot.

## Live admission and stop conditions

The launcher runs its own server on loopback port 8093. Before loading, it checks normal
memory pressure, nominal thermal state, at least 5 GiB estimated available memory, and a free
port. It takes a fresh system swapout baseline. After load, it requires three consecutive
normal pressure readings five seconds apart, with a 90-second settle limit.

The initial HTTP preflight uses `/props`, then `/apply-template` and `/tokenize` for each of
the 11 prompts. These are 23 non-generating requests. It verifies the pinned model, build,
chat template, Metal offload and context margin including the full output reserve. No
completion is sent until all prompts pass.

The runner monitors pressure, thermal state and system swapout between calls and while
waiting for HTTP. A resource warning, cumulative growth above 1 GiB, HTTP failure or recognized
engine fault stops the pilot and unloads its dedicated process. It pauses two seconds between
completed requests. The ledger charges each generation before sending and the live run
directory can only be created once. It preserves partial results and stop evidence for review.

The report uses strict JSON and counts truncation, malformed output, wrong tool,
schema-invalid arguments, schema-valid wrong arguments and correct calls. The per-task
detail keeps schema validity separate from tool choice. Latency and token usage are included.

## Model-free validation and launch

Use the existing project environment from `schema-native/`. With the reviewed local files
still in the workspace's sibling `outputs` directory:

```bash
pilot_outputs=../../../outputs
pilot_plan="$pilot_outputs/v2-dev-free-v0.1-plan.json"
.venv/bin/python -m sn.v2_dev_pilot check --outputs "$pilot_outputs" --bundle "$pilot_plan"
```

The pilot plan has SHA-256
`36b6f71fd49773f5af454d2ee789b72521b0c7322eb4a0c348a882da08d89c25`.
Model-free validation verified the pinned GGUF, commits and binary, recreated the exact 11
requests, and checked that the live run directory did not exist. Fixture tests exercised the
budget, interruption behavior, scorer and context gate. All 247 tests passed (227 package,
12 original evaluator and eight power-planning). Actual tokenizer counts, throughput and
model outcomes still require the live run.

After approval of this specific plan and a fresh passing Mac admission check:

```bash
.venv/bin/python -m sn.v2_dev_pilot run --bundle "$pilot_plan" \
  --approved-plan-sha256 36b6f71fd49773f5af454d2ee789b72521b0c7322eb4a0c348a882da08d89c25
```

Local evidence goes to `runs/v2-dev-free-v0.1/`. Review aggregate results before publication.
The run leaves the held-out dataset and E1/E2 gates separate.
