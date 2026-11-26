# v2 development repair comparison

Protocol locked on 2026-11-26. This diagnostic uses the 32 schema-visible items from the
[development schema-visibility control](../v2-keyword-control-v0.1/RESULTS.md). The three
arms use the same original requests, schemas, golds and exact scorer.

| Arm | Treatment | New generation requests |
| --- | --- | ---: |
| Baseline | Reuse each saved schema-visible completion | 0 |
| Validator retry | Reuse the first completion and send one corrective turn on a raw schema error | 7 |
| Checklist | Append one shared checklist to the system prompt and generate once | 32 |

The retry sees the original request and schema, its own previous completion and one error
from the raw validator, chosen deterministically by JSON path, schema path and message.
Valid arguments, malformed replies and truncated replies keep their first answer in this
development protocol. Routing reads visible schemas and the first response. Gold is only
used by the exact scorer. The seven fixed retry units are K02/S2, K03/S, K04/S2, K05/S2,
K08/S2, K11/S and K16/S2. The checklist asks Qwen to include requested details the schema
allows and verify required fields, tuple positions and applicable branch or dependency rules.
There is no combined arm.

The report counts exact calls, both kinds of argument error, improvements and regressions
relative to baseline, and prompt and completion tokens per arm. The logical token total for
the retry arm includes its first attempt and every retry. New live usage is also reported
separately. Logical token totals are a work measure. Model hosting cost would need separate
measurement. The saved baseline predates the interventions and comes from a different
server session using the same pinned profile. All 32 items are public development examples
already used to design these interventions. A held-out test needs independently reviewed
tasks and a fresh prospective baseline under the same campaign.

## Runtime and request limits

The hard limit is 39 generation attempts, plus up to 79 non-generating metadata requests
for context preflight. Model, template, sampling, cache setting, context, and 512-token output cap follow the prior control.
The launcher uses a dedicated port, requests are charged before dispatch, and scoring
starts after all 39 responses are stored. An engine, HTTP or resource fault ends the run.
The standard admission check requires estimated available memory of at least 5 GiB,
normal memory pressure and nominal thermal state. The server settles before the first
request, retains the 1 GiB swapout-growth hard stop and unloads on exit. An existing
run directory prevents restarting the same campaign.

## Reproduce

From `schema-native/` with the pinned existing runtime and local source artifacts in
`runs/v2-keyword-control-v0.1/`. The manifest and row hashes are pinned in
[the run config](../../configs/runs/v2_keyword_repairs.json). The saved baseline and
prior evidence were left intact. The historical runner remains available at commit
`e2529a3` for byte-for-byte reproduction of its implementation hash.

```bash
umask 077
repair_plan=../../../outputs/v2-keyword-repairs-v0.1-plan.json
.venv/bin/python -m sn.v2_keyword_repairs prepare --bundle "$repair_plan"
.venv/bin/python -m sn.v2_keyword_repairs run --bundle "$repair_plan" \
  --approved-plan-sha256 72f68cf37bd1fd337041e3c91ea6b05606edc637185eeb7000476913f9a518b4
```

Preparation is model-free and writes to a new path. Compare the printed digest to the
locked digest before launching. The plan reproduces all 32 old prompts and selects seven
repairs with jsonschema 4.26.0. The input audit for the preceding control still reproduces.
E1/E2 remain gated pending a sufficiently large held-out dataset.
