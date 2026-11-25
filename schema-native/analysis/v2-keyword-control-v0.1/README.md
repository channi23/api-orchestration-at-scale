# Schema-visible versus schema-hidden development control

2026-11-25. This model-free design asks whether the model uses the supplied schema to
change its answer when the request stays the same. It uses the existing
[16 synthetic keyword pairs](../../data/v2-keyword-seed-v0.1/README.md).
Each member offers one tool, so the control measures argument interpretation.

## What the offline audit verified

| Count | Result |
| --- | ---: |
| Development pairs / proposed structural families | 16 / 10 |
| Distinct schema-visible prompts | 32 |
| Distinct schema-hidden prompts | 16 |
| Pairs whose accepted argument objects differ | 14 |
| Maximum exact members with one shared answer per hidden pair | 18 / 32 |
| Maximum both-members-correct with one shared answer per hidden pair | 2 / 16 |

The hidden prompt is byte-identical within each pair after the normal message renderer.
The 14 changed-gold pairs allow at most one exact match each from a shared answer.
The two same-gold pairs allow two each. These are ceilings for the proposed scoring
protocol. Actual model accuracy in either arm remains unmeasured.

One prior gold-blind reviewer answered all 32 items. The five local receipt hashes match.
The ZIP payload matches the regenerated review packet. Rebuilding gold from the authored
pairs and comparing each first answer reproduced 32 correct tool names, 32 valid argument
objects and 32 exact call matches. The reviewer disclosed the automatically supplied generic
profile and prior knowledge of public JSON Schema. Complete context independence could
not be verified. These are the review findings on the original prompts.

The existing argument comparator equates numeric `2` and `2.0` while keeping booleans
distinct from numbers. The postal-code schema requires a string. The memo wording can
be clarified with a quoted literal and the prefix wording can explicitly allow the full
list in a future version. This audit preserves the reviewed requests and golds. A wording
revision would need a new prompt manifest and review before it is used for evaluation.

## Prospective measurement

Use raw schemas and free decoding for both arms. The shared policy allows any supplied
schemas and the shared tool description avoids telling the model a schema is present.
The prompt audit uses the pilot's message renderer. Only the tool's `parameters` field
differs between the arms for a given member. Task IDs, gold, edit labels and pair metadata
stay outside the messages.

The dedicated run sends one schema-visible call per member and one schema-hidden call
per pair, for a hard cap of 48 generation attempts with no retries. Within each pair
the single hidden request runs first, followed by S and S2. Preflight uses at most 97
non-generating calls before any completion. Apply the same strict parser and exact scorer in both arms. Validate each answer
against that member's original schema offline. Report exact member accuracy and
both-members-correct by pair kind. Keep same-gold rewrite consistency distinct from correct
answers. Reuse the hidden answer for both members under the locked protocol.

The paired requests intentionally rely on schema information. Findings will describe these
development examples and one-tool interpretation. Held-out generalization, cost reduction,
and E1/E2 require separate evidence. The 19/32 engine coverage reported for these schemas
also prevents a full matched constrained arm on the current pinned backend.

## Reproduce the model-free input audit

From `schema-native/` using the existing environment:

```bash
.venv/bin/python -m sn.keyword_seed audit --check
.venv/bin/python -m sn.v2_keyword_control audit |
  diff -u analysis/v2-keyword-control-v0.1/audit.json -
```

The [audit](audit.json) records the paired gold relation and rendered-message hashes.
No model loads for this audit. There are zero approved locked-test intents.

Use the pinned runtime, unchanged model profile and dedicated loopback port 8094. The launcher
requires fresh admission (at least 5 GiB estimated available, normal pressure, nominal thermal
state), then a post-load settle window and a context check on every prompt. The first request,
engine or resource fault stops the run and unloads its server. Absolute swapout growth above
1 GiB is a hard stop, and there are no automatic retries. The run writes an exclusive local
directory, charges each request before sending it and scores only after all 48 results are
stored. The previous 11-request run can be reproduced offline at its original runner commit
`818d330`. Its settings and evidence remain preserved.

The prepared plan hash is
`c65bd8ccc492e16e3548c13d1dde9d41473974051b9b2f3a4171db8f3dc119e4`.
From `schema-native/`, prepare it at a new local path and compare the printed digest
before launching the authorized development run:

```bash
umask 077
control_plan=../../../outputs/v2-keyword-control-v0.1-plan.json
.venv/bin/python -m sn.v2_keyword_control prepare --bundle "$control_plan"
.venv/bin/python -m sn.v2_keyword_control run --bundle "$control_plan" \
  --approved-plan-sha256 c65bd8ccc492e16e3548c13d1dde9d41473974051b9b2f3a4171db8f3dc119e4
```
