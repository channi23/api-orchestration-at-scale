> Current status, 2026-11-15: Amendment 3 review passed at `1df130c`. The narrow pending-prefix
> clarification below is model-free and complete; **166 tests pass**. No further review round is
> required by the user. Await explicit confirmation that the Mac is freed up before loading.
> The earlier 141-test record below is the historical reviewed validation; final clarification
> evidence and current totals appear at the end of this file.

# E0b Amendment 3 — model-free review validation

**LOCKED 2026-11-15 IST. Steps 1–2 complete; STOP for review and confirmation that the Mac is freed up.**

No model was loaded, no generation or training ran, and no real `e0b-amendment3-v1` run directory,
swap baseline, ledger or online receipt was created. All request activity in lifecycle tests uses
synthetic responses and temporary directories. E1/E2 remain gated.

## Scope and preservation

Amendment 3 is appended to the plan after its exact previous contents at `d26feb9`. Both configs
retain their exact previous serialized text in `amendment2_locked_text`, including all earlier
snapshots and amendment records. The only active changes are amendment/run identity, the
corresponding swap-baseline path and resource lifecycle policy. Tests compare every other config
field with `d26feb9`. Model profile, prompts, sampling, source rows, selected requests, schemas,
router, oracle and analysis rules are unchanged.

Both published stopped campaigns, `analysis/e0b-amendment1-v1` and
`analysis/e0b-amendment2-v1`, are byte-for-byte unchanged, as are `analysis/e0-clean-v1` and
`experiment/`. The preceding readiness artifacts are retained separately as
`native-amendment2.json`, `TESTS-amendment2.txt` and `VALIDATION-amendment2.md`.

## Resource lifecycle implemented

- Dedicated campaign server launch requires normal pressure and **at least 5 GiB** of the requested
  free + inactive + purgeable sum. Admission reports each component and the ten largest processes
  by resident bytes, names and sizes only. This sum is an accounting estimate: purgeable pages may
  overlap other categories. Admission inventories stay local rather than being published.
- No server process is started after failed admission. The campaign launcher enforces the frozen
  model path/profile, refuses an occupied port, imports the eleven historical readiness charges
  and records the scientific identity before starting its own server process group.
- After load, TCP readiness is followed by pressure sampling every **5 seconds**, for **90 seconds**
  maximum. **Three consecutive normal samples** are required before any inference or metadata HTTP
  request. Settle failure writes a resumable stop and unloads only the owned dedicated server.
- Before and after each fresh generation, memory, thermal and active-swap-rate checks run. A warning
  idles the model and logs a pause; checks repeat every **30 seconds**. Three consecutive checks
  clean on all guards permit continuation. Recovery timeout is **15 minutes**, followed by a
  resumable resource stop and graceful unload.
- **System swapout growth strictly greater than 1 GiB remains a final hard stop**, including during
  warning recovery, loading and settling. The original baseline is never reset on resume; changed
  boot/counter identity also fails closed. Accumulated swap allocation is not used as swap-write rate.
- Every pause, clean/warning check, continuation, stop and resume is timestamped and fsynced. Resource
  STOPPED.json files are archived unchanged before resume. A later final fault cannot leave an old
  resumable marker active. Engine/request faults, finished constraint violations, illegal-prefix
  truncations and determinism failures remain final stops. Legal-prefix truncation still records
  cd_truncated, with no protocol change.
- Fresh admission/settling and unchanged manifest/config/runtime identity are required on server
  restart. Preflight rechecks runtime and server metadata; only the pinned text-only server's unused
  random `media_marker` may differ. Original receipts are archived before refresh. Completed smoke,
  determinism, C1/C2 and V retry keys are read from durable records and never sent or charged again.
  Frozen generation order remains intact. An already charged key without a durable response fails
  closed; it is not automatically retried.

Checks are sampled at boundaries, not continuous telemetry inside a blocking HTTP call. A request
already in flight may finish and persist before the pause begins. Graceful unload verifies the
registered process identity and process group and waits for exit; it never closes other apps.

Greedy decoding, fixed seed and independent requests make resource-driven scheduling independent
of outcomes. No interim accuracy is read. These settings do **not** prove byte identity across
server restarts; the frozen 30-request determinism gate remains mandatory, and completed comparisons
are never repeated to reset it. No claim of hardware-independent determinism is made.

## Model-free tests

**129 package tests + 12 original evaluator tests = 141 passed.** 21 Amendment 3 cases cover:

- Settle pass, reset after a warning, and exact 90-second timeout.
- Warning pause, three clean checks after the last warning, and exact 15-minute timeout/unload.
- Admission at the 5-GiB boundary, below the boundary, and with abnormal pressure; inventory shape.
- Actual launcher control flow with a fake process: admission failure never calls process launch;
  settle pass permits readiness and settle failure calls unload. No model subprocess is created.
- Hard swap cap precedence even under memory warning, and final-fault non-resumability.
- Unload waits for the owned model child even if its launcher has already exited; only zombie
  or absent group members permit an unloaded event. This signaling test is entirely synthetic.
- A synthetic full benchmark transport stops after its first durable C1 response, then resumes:
  **662 unique generation keys sent exactly once**, in frozen order (30 determinism, 300 C1,
  300 C2, 32 V). Saved result bytes remain an unchanged prefix, and charges are not duplicated.
- A synthetic smoke resume skips one durable adversarial probe: 18 additional synthetic calls
  complete the planned 19, and cumulative charges are **30/60 including the historical 11**.
- Exact prior plan/config history and protected-directory preservation.

Commands (run from `schema-native/`):

```sh
.venv/bin/python -m pytest -q --ignore-glob='* 2.py'
.venv/bin/python -m pytest -q ../experiment/tests/test_evaluate.py
.venv/bin/python -m sn.e0b_readiness
```

The full package suite uses temporary localhost fake HTTP servers. Existing untracked sync copies
with names ending ` 2.py` are excluded and left untouched. `TESTS.txt` records the final passing
outputs. Native evidence is revalidated against the current plan and verification-source hashes.

## Refreshed native engine evidence — no model or tokenizer inference

| Check | Result |
| --- | --- |
| C1 envelope compilation | 70/70; zero refusals |
| C2 unit-specific compilation | 300/300; zero refusals |
| C1 schema-ordered gold reachability | 300/300 |
| Bounded invalid witnesses accepted | C1: 0/6,696; C2: 0/6,696 |
| Strict free-correct outputs accepted under their oracle constraint, both representations | 499/501 |
| Of those, formerly order-rejected subset | 250/252 |
| Raw F0 strict free-correct outputs accepted under C2 | 246/248 |
| Strict stored router replay | select 18/200; arggen 14/100 |
| V native capability gate | PASS; 32 planned retries through C1 |
| Planned oracle flags | oracle_not_applied 32; oracle_incomplete 0 |
| Tuple-array positions in the frozen envelopes | None |
| Frozen look-alike output flags | Raw CD 11; minified CD 6; both free arms 0 |
| Overall native C1/C2/V gate | PASS |

Every reachability exception remains unchanged and is **not** relaxed:
`select|A_raw_free|C005_R03|T062_p0` and `arggen|A_raw_free|single|T062_p0`.
These are the known required-but-undeclared `id` T062 cases. C3 stays excluded, with its original
failed model-free gate retained as historical engine evidence; no C3 subset or replacement is run.

## Budget and future execution — NOT authorized by this validation

New run: **e0b-amendment3-v1**. Cumulative caps remain **60 readiness (11 spent, 49 remaining)** and
**700 benchmark (zero spent)**. Projected benchmark generation count remains 662. All 30 selected
F0/C0 comparison keys are unchanged. No new readiness or benchmark request was charged here.

Only after review passes **and** the user confirms the Mac is freed up, use the following sequence.
Do not run the commands now. Start the server in a separate terminal:

```sh
.venv/bin/python -m sn.server --config configs/model.qwen3-1.7b.sustainable.json --campaign-config configs/runs/e0b.json
```

Wait for its `settled` event before proceeding. In another terminal, execute each step only if the
preceding one passed. The runner enforces determinism before C1, then C2, then V:

```sh
.venv/bin/python -m sn.e0b_preflight --run-id e0b-amendment3-v1 --output runs/e0b-amendment3-v1/online-preflight.json
.venv/bin/python -m sn.run --config configs/runs/e0b.json --run-id e0b-amendment3-v1 --preflight runs/e0b-amendment3-v1/online-preflight.json
.venv/bin/python -m sn.e0b_report --run e0b-amendment3-v1
.venv/bin/python -m sn.e0b_resources --unload
```

On an allowed resource stop, later repeat the same server/preflight/runner commands with the same
run ID and unchanged checkout. Successful requests are skipped, not repeated. Do not resume a
final fault or delete a ledger/STOPPED.json to bypass it. The report is produced after completion,
not between segments. Unload also follows any stop. Publish redacted resource observations, not
private app inventories, when future execution is authorized.

**Not verified here:** actual current Mac headroom, physical post-load settling or recovery, real
process signaling/unloading, online runtime checks, live smoke, 30 byte-identical model responses,
model/tokenizer enforcement, benchmark results, accuracy/latency or decision-rule outcomes. Fake
transport totals are software-control proofs, not measured inference results. E1/E2 stay gated.


## Amendment 3 clarification — pending prefix verification (2026-11-15)

This is the exact requested clarification, recorded after all earlier text in E0B_PLAN.md. The
reviewed locked configs and model profile are unchanged. Both stopped campaigns, frozen E0,
experiment/, selections and all budgets are unchanged. No real Amendment 3 directory, swap
baseline, online receipt or ledger was initialized. No model was loaded and no real inference,
training, process signal or resource admission ran during this clarification.

A checker failure now persists the response, usage, checker error and exact constraint
schema/grammar with **prefix_check: "pending"**. It is **not engine_refusal**, has no final failure
class, and causes an immediate resumable resource-type stop/unload rather than another request.
Missing helpers, build/library hash failures, timeouts, invalid JSON, duplicate keys, non-finite
JSON numbers and malformed/non-boolean verdict arrays all fail without claiming an illegal prefix.
HTTP/engine faults still retain their original final-stop precedence.

Before a future model load, the campaign launcher invokes one fixed helper self-test (three probes
in one helper process: complete-valid, incomplete-legal and illegal). A failure stops before model
launch. The self-test then precedes offline resolution of pending rows under the writer lock.
Only after those checks pass can admission, baseline checks, model loading and settling proceed.
A real model-free self-test against the bundled helper **passed**, recorded in
`prefix-helper-self-test.json`. It used no model weights, tokenizer inference, GPU or server.

Offline resolution appends proof-only records to **prefix-resolutions.jsonl** with the original
response fingerprint; it never rewrites the response stream, re-scores frozen data, sends a
request or adds a request-budget charge. A legal proof resolves to cd_truncated; smoke, benchmark
resume and final reporting read the same resolution overlay and skip the completed request key.
An illegal proof is preserved and makes the stop final/non-resumable before loading. Another
unavailable proof leaves the row pending. Unresolved pending checks block final analysis, so no
interim accuracy is read. Publish this resolution ledger with future campaign evidence if used.

**Final verification: 154 package tests + 12 original evaluator tests = 166 passed.** The 25 new
hermetic pending-prefix cases cover unavailable helper/hash/timeout/malformed paths, strict verdict
parsing, smoke resource-stop semantics, benchmark persistence without an engine-refusal label,
legal offline resolution for both response streams, no duplicate resolution, byte preservation,
confirmed-illegal final stops, repeated-unavailable checks staying pending, a failed pre-load
self-test preventing model startup, and resume skipping the already-paid verified response.
`test_benchmark_truncation_is_scored_not_an_engine_fault` now injects its checker and depends on
neither the installed helper nor its build state. The full suite uses temporary fake HTTP servers;
all campaign responses in tests are synthetic.

The current native evidence was refreshed and validated against current plan/source fingerprints.
C1/C2/V native capability still passes: C1 70/70 and C2 300/300 compile, C1 gold 300/300,
0/6,696 invalid witnesses accepted per arm, compatibility 499/501 (order subset 250/252), raw F0
246/248, router 18/200 and 14/100, planned oracle flags 32 not-applied and 0 incomplete. The same
two T062 exceptions remain unrelaxed. No C3 run or backend substitution occurred.

Use the existing future server/preflight/runner commands above **only after Mac-ready confirmation**.
The server automatically runs the self-test and pending offline checks before each model load.
Run ID remains e0b-amendment3-v1; readiness remains 11 spent / 49 left, benchmark 0 spent / cap 700.
Current Mac headroom, real process recovery, live smoke/determinism and all benchmark outcomes remain
unverified. E1/E2 stay gated; no training. Review was accepted; execution awaits only the user's
explicit confirmation that the Mac is freed up and the locked admission/resource checks.
