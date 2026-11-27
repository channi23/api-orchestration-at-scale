# v2 development pilot results

Completed on 2026-11-25 under the [approved pilot protocol](README.md).
This was free decoding on 11 reviewed development tasks with five candidate tools each.

| Measure | Observed |
| --- | ---: |
| Generation attempts / completed responses | 11 / 11 |
| Correct tool | 11 / 11 |
| Schema-valid arguments | 11 / 11 |
| Exact tool and arguments | 9 / 11 |
| Schema-valid but wrong arguments | 2 / 11 |
| Malformed, truncated, wrong tool or schema-invalid | 0 |
| Median request latency | 2.73 s |
| Prompt and completion tokens | 19,783 and 587 |

Online preflight checked all 11 prompts before generation. The longest prompt was 3,643
tokens with a 512-token output reserve in an 8,192-token context. There were 23
non-generating preflight requests and no generation retries. All 58 live resource samples
showed normal memory pressure, nominal thermal state and zero system swapout growth.
The run logged server unload, and the dedicated port was verified closed.

The [machine-readable report](report.json) is copied verbatim from the completed run.
The original scorer reproduced it from the local manifest and stored responses. The ordered
task IDs matched the approved plan, and the ledger contained exactly 11 benchmark charges.
The public record contains scoring, timing and token counts. The raw responses, ledger,
manifest and host logs are retained locally.

| Local artifact | SHA-256 |
| --- | --- |
| manifest.json (identical to the approved plan) | `36b6f71fd49773f5af454d2ee789b72521b0c7322eb4a0c348a882da08d89c25` |
| results.jsonl | `4a6a6a813c258b48a6d5b89fd14d6d35706eb9dbe0f9f231edb0db5b4689440b` |
| request-budget.jsonl | `89bdad420ae5ed091dd397924420631d4616d27c7f20c8628ab1c378a41c260e` |
| preflight.json | `994c8d9df93efb62a492550c4a90027d06d19f3dbe58073fb329e3801fcc345b` |
| report.json | `8a28ed65189fc867f82dd10328bafeb42f35fd5b7b0ca8e5ba9e920da64fbd75` |

## Why both wrong calls passed

| Task | Output difference | What the original validator saw |
| --- | --- | --- |
| `V2OSW_1b2777a6b571` | Omitted `limit: 5` | The field is optional. The request supplies the value. |
| `V2DO_321f64c5b032` | Added `name` alongside `tag_name` | Both fields are allowed. Their mutual exclusion appears in the field descriptions only. |

Replaying the stored outputs through the strict router routed **0/11** to retry. Both misses
therefore pass a validate-then-constrain router using these raw schemas. This replay sent
no generation requests and used no gold in the routing decision.

For DigitalOcean, an isolated counterfactual added only
`"not": {"required": ["name", "tag_name"]}` to a copy of the argument schema.
The raw 2020-12 validator accepts the gold and rejects the stored call under that copy.
The hash-verified native byte-tokenizer helper compiled the original schema and accepted both
schema-ordered witnesses. It refused the copy with `Unimplemented keys: ["not"]`.
This was an argument-schema probe using the pinned bundled llguidance build, without a model
or server. The inference schema and pilot result were preserved. The Stripe miss depends on
the requested value, so a static required-field rule would still leave value selection unresolved.

The pilot is descriptive. Held-out generalization, constrained decoding accuracy, cost savings
and training effects require separate evidence.
