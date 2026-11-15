# E0b Amendment 3: resumable stop before model load

**STOPPED — resource admission failed; resumable under e0b-amendment3-v1. No Qwen model was loaded.**

Source commit: `30d04b1a82eb0cf631b01ad6e8dca6881b95cd12`. Amendment 3 review and the exact
pending-prefix clarification were accepted. The user delegated the readiness decision; actual
resource checks, rather than elapsed time or assumed app closures, determined this stop.

## What ran

- Current native capability evidence was validated against the frozen plan and source fingerprints.
- The bundled prefix helper self-test passed, with one invocation and three fixed probes.
- The exact campaign identity and plan were saved, an empty actual benchmark response stream was
  created, and the eleven historical readiness charges were imported once.
- The live pre-load check reported memory-pressure warning level **2** and
  free + inactive + purgeable **2,456,961,024 bytes (2.29 GiB)**,
  below the locked **5 GiB** floor. STOPPED.json records a resource-type resumable stop.
- Model load, swap-baseline initialization, settling, online HTTP preflight, smoke and determinism
  were not attempted. No owned model session was created; there was no model process to unload.
- No other app was closed, no weight or model setting changed, and no inference or training ran.

## Resource observations

| Observation | Admission check | Later post-stop sample |
| --- | ---: | ---: |
| Memory pressure | Warning (2) | Warning (2) |
| Free + inactive + purgeable estimate | 2.29 GiB | 3.43 GiB |
| Required available-memory floor | 5 GiB | 5 GiB |

Foundation thermal state was nominal (0) in the preliminary and post-stop checks. Two-second
system-counter samples before and after the stop observed **zero additional swapout bytes**.
These are short global samples, not proof of sustained zero swap activity or process attribution.
The available-memory sum can overlap purgeable accounting categories; it is the specified admission
estimate, not guaranteed allocatable memory. The increase between samples is not attributed to
Qwen: no Qwen model was loaded. AC power was attached in the preliminary power-status check.
CPU/GPU utilization, swap allocation in use, and thermal-throttling sensors were not measured.
The cumulative boot-lifetime swapout counter in after-stop.public.json is **not Swap Used**.
No campaign swap-growth baseline exists because loading was rejected.

The ten-process resident-memory inventory was reported locally and is **not published**. Public
resource-events.public.jsonl retains timestamps, helper proof and resource observations, with the
private inventory removed. No pause-recovery loop or resume has yet occurred; this was a pre-load
admission stop, not a warning during inference.

## Budget and report

| Category | Historical charges | New requests | Cap | Remaining |
| --- | ---: | ---: | ---: | ---: |
| Readiness/smoke | 11 | 0 | 60 | 49 |
| Benchmark, including determinism | 0 | 0 | 700 | 700 |

No baseline was re-run or imported as a benchmark output. The durable ledger contains only the
same eleven namespaced historical charges. sn.e0b_report produced a status-only partial report:
**0 final rows, 1,500 missing, complete=false**. No comparisons, accuracy read, hypothesis test,
threshold decision or research interpretation was performed.

New C1/C2/V outputs: **0**. New look-alike flags and their matched declared keys: **none**, because
no outputs exist. C2 output-side oracle_not_applied and oracle_incomplete are **unmeasured**;
oracle-counts.json distinguishes these from the frozen planned counts **32 / 0** over 300 units.
There are no pending prefix checks or offline resolutions. prefix-resolutions.jsonl is published
as an explicitly empty stream, not as evidence of any model-output prefix test.

## Verification and limits

Verified: unchanged frozen model/config/input identity; current native C1/C2/V gate; real bundled
helper self-test; actual admission failure before load; resource STOPPED.json marked resumable;
zero new request charges; private-inventory redaction; exact copies of manifest, stop and ledger.
Pre-execution regression validation remains **154 package + 12 evaluator tests = 166 passed**;
no code was changed for this publication. Original E0, experiment/ and both earlier stopped
campaigns remain unchanged.

Not reached: model load/settling, live runtime/weight checksum or GPU checks, online smoke,
30-request byte-identical determinism, C1/C2/V inference, actual output-side flags, model accuracy
or latency, and locked decision-rule outcomes. Hardware safety is not inferred beyond the sampled
observations. E1/E2 stay gated. No training.

## Later resumption

Do not delete or reset the run, results, stop record or request ledger. Once memory pressure is
normal and the specified available-memory estimate is at least 5 GiB, resume the same
**e0b-amendment3-v1** with the existing commands in [VALIDATION.md](../e0b-readiness/VALIDATION.md). The launcher
rechecks the helper and pending prefixes offline, then requires fresh admission and settling.
Only after these checks does the online runner archive this resource STOPPED.json unchanged
and continue preflight/determinism/benchmark work. No request completed
in this campaign needs repeating: none was sent. Budgets, selection and order remain frozen.

**Final state: model not loaded; no automatic retry; waiting for sufficient Mac headroom.**
