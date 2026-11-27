# v2 development repair comparison results

Completed on 2026-11-26 under the [locked protocol](README.md). Each arm was scored on the
same 32 schema-visible development items. The baseline reuses earlier responses from the
same pinned model profile. The retry arm starts from those same responses.

| Outcome | Baseline | Validator retry | Checklist |
| --- | ---: | ---: | ---: |
| Exact calls | 18/32 | 19/32 | 18/32 |
| Schema-invalid arguments | 7 | 4 | 7 |
| Schema-valid but wrong arguments | 7 | 9 | 7 |
| Exact improvements / regressions | — | 1 / 0 | 0 / 0 |
| Logical generation requests | 32 | 39 | 32 |
| Prompt / completion tokens | 13,627 / 1,261 | 17,424 / 1,506 | 15,291 / 1,266 |
| Total tokens relative to baseline | 1.00× | 1.27× | 1.11× |

The checklist left every item's outcome category unchanged and used 11.21% more tokens.
One of seven validator retries recovered the exact call, moving exact accuracy from
56.25% to 59.375%, a gain of 3.125 percentage points at 27.15% more logical tokens.
Two other retries fixed the schema violation and still missed the request. Four still
violated the schema. There were zero malformed, truncated or wrong-tool final answers.

- K04/S2 was recovered. Qwen dropped the disallowed `b` and kept the requested `a` and ID.
- K08/S2 illustrates the limit of validator feedback. Qwen changed `["beta", 2]` to
  `[1, "beta"]`, fixing the positional types while replacing the requested value `2`.
- K02/S2 became valid after switching from `economy` to `express`. The request required
  the cheapest allowed option, `priority`.

The measured token counts include prompt and completion tokens. Reused first attempts
are included in the logical totals for the retry arm. The actual 39 new requests used
19,088 prompt tokens and 1,511 completion tokens. The measured results describe these
fixed development examples and interventions. Held-out effectiveness, deployment cost
and training effects require separate evidence.

## Execution and verification

The successful admission estimated 6.01 GiB available with normal memory pressure.
Preflight checked all 39 prompts, spanning 406 to 626 tokens with 512 tokens reserved for
output. The ledger contains exactly 39 charges and 39 stored responses in the locked order.
Across 196 resource samples, pressure was normal, thermal state was nominal and system
swapout growth was zero. Server unload was logged and the dedicated port was verified closed.
The earlier two pre-load stops had zero requests and were preserved in local archives.

The [machine-readable report](report.json) is copied verbatim and reproduced from the locked
plan and saved responses. Raw responses, manifest, ledger and resource logs remain local.

| Local artifact | SHA-256 |
| --- | --- |
| manifest.json | `72f68cf37bd1fd337041e3c91ea6b05606edc637185eeb7000476913f9a518b4` |
| results.jsonl | `b76b81e62f2fb74e473d87de4c73a6f32150d85ad21c6c0b0f1f885ca20518b2` |
| report.json | `75038ada444dc23e1fa518c4a4be5192dc72b8363242029c196e89f70ac5b4e6` |
| request-budget.jsonl | `cec1870d1ec0b96e3391f350cec8bb28d574d7476ca203cc10b5e979d600758c` |
| preflight.json | `a434e927a6d29d2844c5cabac2336dcd3d3016625ded742e8c45be08c847c9a1` |

E1/E2 stay gated. The experiment used free decoding throughout. No training occurred.
