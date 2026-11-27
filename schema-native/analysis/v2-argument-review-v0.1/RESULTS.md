# v2 argument review results

Completed locally on 2026-11-27 under the [locked protocol](README.md).
Exact accuracy stayed at **9/11**. The review produced zero corrections and zero
regressions. All 11 argument objects matched their saved first calls under the
frozen equality rules. The promotion-code call still omitted the requested limit.
The DigitalOcean call still added the incompatible name filter alongside the tag
filter. Both calls remained schema-valid.

| Measure | Saved first calls | First calls plus review |
| --- | ---: | ---: |
| Exact calls | 9/11 | 9/11 |
| Schema-valid calls with wrong arguments | 2 | 2 |
| Logical generation requests | 11 | 22 |
| Prompt tokens | 19,783 | 25,954 |
| Completion tokens | 587 | 939 |
| Total tokens | 20,370 | 26,893 |

The review added **6,523 tokens (+32.0%)** and a median **1.27 seconds** of
request wall time per call. The outcome misses the locked development criterion
of more exact calls with zero regressions. The sample contains only two first-call
errors. These figures describe the measured intervention on these development
tasks. They leave the broader accuracy and cost questions open.

## Execution and verification

- The 16 GB M4 MacBook Pro passed admission at 6.05 GiB available. The pinned
  runtime confirmed all 29 layers offloaded to Metal and passed the settle window.
- All 11 online prompt counts matched the sealed plan. The ledger contains
  11 generation charges and 23 metadata charges. There were no generation retries.
- All 45 resource samples recorded normal pressure, nominal thermal state and
  zero system swapout growth. The model unloaded and its port closed before scoring.
- The frozen first-call report reproduced byte for byte. The
  [machine-readable report](report.json) contains paired outcomes, token counts
  and ledger hashes. Its SHA-256 is
  `3a6d1e645a21c60a35204df70eef75e15e6f2a6e54f73a8779a7426659af4d0b`.
- The review report also reproduced byte for byte. All 280 tracked tests passed
  (260 package, 12 original evaluator and eight power-planning).

Raw responses, the inference plan and resource logs remain local. The exploratory
benchmark was not rerun. E1 and E2 stay gated.
