# Sustainable E0 on a 16 GiB Apple Silicon Mac

Use a separate profile and run ID. Never silently resume an existing experiment with different
context, batching, pacing, model quantization or concurrency.

| Setting | Original E0 | Sustainable profile | Reason / effect |
|---|---:|---:|---|
| Context | 16,384 | 8,192 | All 600 measured prompts fit: max 6,185 + 512 output tokens. KV cache measured at 1,792 → 896 MiB. |
| Batch | 2,048 | 512 | Lower prompt-processing burst size; throughput and numerical paths may change. |
| Microbatch | 512 | 128 | Lower workspace demand; timing/numerical paths may change. |
| Request spacing | 0 s | 2 s | Idle interval outside measured request latency; reduces average duty cycle, not model allocation. |
| Resource admission | none | normal memory pressure required | Refuses new requests at warning/critical pressure or after three consecutive intervals with ≥1 MiB/s swap writes. |
| Quantization / weights | Q8_0, pinned SHA | unchanged | No weight modification or fine-tuning. |
| GPU offload | all 29 layers | unchanged | Avoid moving work to a CPU-heavy backend. |
| Concurrency | 1 | unchanged | No parallel model requests. |
| Generation | greedy, seed 0, thinking off, max 512 | unchanged | Same request parameters. |

The 8K allocation was tested on the 16 GiB M4. The model RSS fell from about 3.5 to 2.6 GiB and
KV allocation halved, but system pressure still became warning with the existing app workload.
The model was unloaded before any benchmark requests under that profile. **This is not a
multi-hour stability or accuracy validation.** Do not run a long experiment unless pressure remains
normal after loading the model. Resource guards stop the runner; they do not close other apps or
unload a separately launched server. Stop that dedicated server after a guard refusal.

When headroom is available, from `schema-native/`:

```bash
# Terminal 1
scripts/serve.sh --config configs/model.qwen3-1.7b.sustainable.json

# Terminal 2: offline / online checks, then a bounded smoke
source .venv/bin/activate
python -m sn.preflight --config configs/runs/e0_sustainable_smoke.json --output runs/e0-8k-smoke-preflight.json
python -m sn.run --config configs/runs/e0_sustainable_smoke.json --preflight runs/e0-8k-smoke-preflight.json --run-id e0-8k-smoke-v1
python -m sn.report --run e0-8k-smoke-v1

# Only after reviewing smoke and host pressure: a new, separate benchmark
python -m sn.preflight --config configs/runs/e0_sustainable.json --output runs/e0-8k-preflight.json
python -m sn.run --config configs/runs/e0_sustainable.json --preflight runs/e0-8k-preflight.json --run-id e0-8k-v1 --limit 25
```

Repeat the last command to add the next 25 requests. Allow an idle break and check pressure between
chunks. Remove `--limit` only when sustained headroom has been established; the resource checks still
run before each request. With warning pressure, finish/save other work before choosing to close
unused apps yourself. Large browser and editor workloads can exhaust the shared memory budget even
with a small model. App-family footprint totals include compressed/swapped allocations and may
include shared charges; they are not additive physical RAM.

Read-only checks (built into macOS):

```bash
sysctl kern.memorystatus_vm_pressure_level vm.swapusage
vm_stat
```

The pressure sysctl returns dispatch levels (normal 1, warning 2, critical 4), not the kernel's
internal enum values. Use differences in the `Swapouts` counter over time, multiplied by the
reported page size, to measure active writes. A large accumulated swap total alone is not current
thrashing. Never delete swap files, disable compression, disable thermal protections or purge caches
as an experiment optimization. Cache purging also changes the benchmark's execution conditions.

Keep the laptop on a firm, ventilated surface and leave macOS fan/thermal control intact.
A warm chassis alone does not establish throttling. Read `ProcessInfo.thermalState` when available;
`pmset -g therm` may provide no measurement on Apple Silicon. Numerical temperatures, power and
clock-level throttling were not measured here because `powermetrics` required administrator access.
No system utilities were installed, and no global power/security settings were changed.

Sources: [Apple memory-pressure guidance](https://support.apple.com/en-au/guide/activity-monitor/-actmntr1004/mac),
[Apple thermal-state guidance](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/power_efficiency_guidelines_osx/RespondToThermalStateChanges.html),
[Apple ventilation guidance](https://support.apple.com/en-au/102336).
