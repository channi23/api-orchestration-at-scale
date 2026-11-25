# v2 development schema-visibility results

Completed on 2026-11-25 under the [locked protocol](README.md). Untuned Qwen3-1.7B
ran locally with free decoding, the existing E0 profile and one tool per request.
Each hidden answer was scored against both original schemas and golds in its pair.

| Measure | Schema visible | Schema hidden |
| --- | ---: | ---: |
| Generation requests | 32 | 16 |
| Exact item matches | 18/32 (56.25%) | 5/32 (15.625%) |
| Both members exactly correct | 5/16 | 1/16 |
| Both correct among the 14 changed-gold pairs | 3/14 | 0/14 |
| Schema-invalid arguments | 7/32 | 22/32 |
| Schema-valid but wrong arguments | 7/32 | 5/32 |
| Malformed, truncated or wrong tool | 0 | 0 |

| Pair type | Visible exact items | Hidden exact items | Visible pair-correct | Hidden pair-correct |
| --- | ---: | ---: | ---: | ---: |
| Validity-separable | 5/14 | 0/14 | 1/7 | 0/7 |
| Asymmetric edit | 9/14 | 3/14 | 2/7 | 0/7 |
| Equivalent rewrite | 4/4 | 2/4 | 2/2 | 1/2 |

With the same request, K12 asks for the largest retry count allowed by both the user's budget
and the schema. The hidden answer returned the budget value, `9`. With the schema visible,
the model returned `5` and `7` under the corresponding schema maxima, both correct.
K08 shows a remaining limitation. The model returned `["beta", 2]` in both visible variants
even though the second schema requires `[2, "beta"]`. Both equivalent rewrites yielded the
same correct argument objects in the visible arm. Matching an answer across variants can
also preserve an error, as K08 shows.

The measured gap is 13 exact items, or **40.625 percentage points**, on this intentionally
schema-dependent development set. The schema-visible arm answered both variants correctly on
three changed-gold pairs. Fourteen items still failed with the schema present. This evidence
covers one model, one prompt format and 16 synthetic pairs from ten proposed families. The
shared hidden answer creates dependence within each pair. Held-out transfer, a tuned-model
effect, constrained-decoding performance and cheaper tool calling require separate evidence.

## Execution and verification

Preflight verified all 48 prompts, ranging from 268 to 541 tokens with a 512-token output
reserve. The ledger contains 48 charges and 48 saved responses in the locked order.
No retry or generation smoke request occurred. Across all 241 resource samples, memory
pressure was normal, thermal state was nominal and system swapout growth was zero.
The run logged server unload and its dedicated port 8094 was verified closed.

Median request latency was 0.91 s. The campaign processed 18,212 prompt tokens and
1,890 completion tokens across both arms. These are runtime observations from one local run.

The [machine-readable report](report.json) is verbatim. It reproduced offline from the
prepared manifest and every stored response. Raw responses, manifests, ledgers and host
logs are retained locally.

| Local artifact | SHA-256 |
| --- | --- |
| manifest.json | `c65bd8ccc492e16e3548c13d1dde9d41473974051b9b2f3a4171db8f3dc119e4` |
| results.jsonl | `4ff1fa948e72f82b6cb93fa3ac14e5ac6a535d07e27754774f85591354ef4b43` |
| request-budget.jsonl | `38f5de419c9b79867dab6801f85681b9952a22e60f7901767684f1ff407236ed` |
| preflight.json | `ce337d088d4c062db8dafdf669c569eab2ece2e3cc7f7c9e33b749db55587646` |
| report.json | `84aa1eab491d21d92a70e17e654445451072c04e266a47ec32690370bbb85796` |

## Next dataset gate

For a larger benchmark, carry forward both the matched schema-visibility control and
the distinction between schema-invalid and schema-valid wrong calls. Use source-disjoint,
independently adjudicated families and lock the scoring contract before test inference.
Preserve the 16 examined pairs as development examples. The API source holdout has
zero approved locked-test intents. E1/E2 remain gated.
