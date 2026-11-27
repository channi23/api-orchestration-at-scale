# v2 context smoke results

Completed on 2026-11-26 under the [locked development protocol](README.md).
The **9,216-token candidate passed the bounded Mac smoke test**. On the pinned server
it accepted an 8,389-token prompt while reserving 512 tokens for the response, then
generated the expected JSON call. No held-out input was sent to the server.

| Observed | 8,192-token reference | 9,216-token candidate |
| --- | ---: | ---: |
| Generation requests completed / charged | 2 / 2 | 3 / 3 |
| Exact synthetic calls | 2 / 2 | 3 / 3 |
| Longest measured prompt | 7,363 tokens | 8,389 tokens |
| Measured Metal KV allocation | 896 MiB | 1,008 MiB |
| Estimated available memory at load | 6.48 GiB | 6.31 GiB |
| Resource samples | 13 | 20 |
| Peak system swapout growth | 0 bytes | 0 bytes |
| Memory pressure / thermal state | Normal / nominal | Normal / nominal |

Every online prompt length matched its locked offline count. The two prompts shared by both
profiles produced byte-identical responses. Both servers used full Metal offload and unloaded
before verification of the closed ports. The long shared call took 10.51 s at 8,192 and 10.46 s
at 9,216. The extended call took 12.23 s and produced 37 completion tokens. These timings are
single observations. Sustained throughput, the full 512-token decode workload and multi-hour
resource behavior were outside this smoke test.

The 9,216-token profile provides an 8,704-token prompt allowance after the unchanged reserve.
The largest existing compact holdout prompt counted 7,792 tokens offline, leaving 912 tokens
of margin under the candidate. All 20 current compact catalogs clear that offline calculation.
Use this candidate for future reviewed readiness checks. Online checks on the final frozen
catalogs, larger and more diverse held-out coverage, and independent freeze review remain pending.
The historical profile and run settings remain intact.

## Evidence

Reports reproduced from the exact saved manifests and five response rows. The request ledgers
match their stored response keys one for one. Host logs and run rows remain local.

| Local artifact | Reference SHA-256 | Candidate SHA-256 |
| --- | --- | --- |
| manifest.json | `bd3c9abfcb76a3784a87d7f71948aefefb9e4ac0474fca09e1234169627b79ce` | `c1c39caf261032567c1038357b949f3e8767abf7b60760f4d09e21f51e5eb600` |
| preflight.json | `3528cdc3d25687493969c381fb890207dc3951cfda780c3308e7384eb9f51731` | `71d3ec48a642ad55457aa1d0ef3a24b98711f95ef1df6cb3530fa2add0581f6e` |
| results.jsonl | `2ceb47a7a5a26dec0c0561b87a4797b8eef286920642a4e1e0e3ab1b9e3a6dca` | `c2b97c330f5a3f50d733995aa953119dff269ba05f63419859e213c9c395c827` |
| request-budget.jsonl | `f5db4958768945bddf1b5cf8cb52fdad815591c398321130cbaf4c783e476463` | `b89838339a7e19a82bd94b7192fbe4b9a24d4e6a953fb4290c2404957c12ddf2` |
| report.json | `f13553fb4cb2f4f26a7fc6714d0a697a98fe72d6fb0657d86bfb44572b3408c9` | `9c5e79936e09e3d12d4b9a3ca8d2ae1945c5a0d77d99ece22eb0e3d1eb5cd3cd` |

E1/E2 stay gated. No training occurred.
