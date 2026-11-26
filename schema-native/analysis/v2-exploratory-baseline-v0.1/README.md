# Exploratory baseline execution

2026-11-27. The [frozen exploratory dataset](../v2-exploratory-freeze-v0.1/README.md) has
a private inference export with 177 ordered requests. Its manifest SHA-256 is
`c8b0e552f59a44db90fd274f6d6a4d78afa8332b3cb525df32b3fe8ba2befe03`.
The export contains only request payloads and a runtime handoff manifest. The expected answers,
lineage records and scorer stay on the Mac. The export can be checked byte for byte and
has never been sent to a remote host.

## Selected local baseline

Run the staged export with the pinned Qwen3-1.7B Q8_0 and llama.cpp Metal build
from the measured 9,216-token smoke. The launcher reads only the inference export.
It reserves at most 177 generation requests and 360 separate non-generating requests.
The 360 covers 355 first-pass preflight requests plus five extra requests across segments.
Every segment checks the live server identity. A completed prompt-length check is reused
only with the same sealed export and runtime.

The existing Mac guards require at least 5 GiB by the free + inactive + purgeable estimate,
normal memory pressure before loading, three normal pressure readings five seconds
apart after loading and nominal thermal state. The launcher unloads its own model on a
guard stop. It checks pressure, thermal state and swap activity between requests and
during a long request. The hard limit is 1 GiB of cumulative system swapout growth across
active segments. The request cooldown is two seconds.

```bash
export_dir=../../../outputs/v2-exploratory-free-inference-v0.1
.venv/bin/python -m sn.v2_exploratory_run check --export "$export_dir"
.venv/bin/python -m sn.v2_exploratory_run run --export "$export_dir"
```

The second command is also the resume command after a resumable stop. The run
directory is `runs/v2-exploratory-free-v0.1`. Resumption verifies that saved replies
and charged generation keys match the same prefix of the frozen order. An unanswered
generation charge, invalid server telemetry or runtime fault requires inspection and
blocks an automatic resume. The launcher records a completed run only after unloading.
Use the frozen scorer offline on the complete response ledger. Keep prompts, answers and
per-request results out of the published aggregate report.

## Host options

- Use a separate Apple Silicon machine if the comparison calls for the same macOS and Metal
  backend. Verify the pinned build, GGUF and template and record the host separately.
- A Linux NVIDIA GPU host can run the same GGUF with CUDA. Record a separate runtime identity,
  including exact build and backend. Identical prompt and weights improve comparability. A
  different backend can still affect tokens, timings or memory behavior.
  [llama.cpp build documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md)
- Docker bundles the runtime on the selected host. Running it on the Mac still consumes the
  Mac's resources. A job launched and recorded entirely on a remote host can keep running
  after the Mac disconnects. [llama.cpp Docker documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md)

## Free SSH-controlled host

Oracle Cloud Always Free is the selected option to check first. Its current Ampere A1 allowance
is 2 OCPUs and 12 GB total per free tenancy. In the console, use an Always Free-eligible
`VM.Standard.A1.Flex` in the tenancy's home region, an Arm64 Ubuntu image and a boot volume
within the free allotment. Use your own SSH public key. Capacity can be unavailable and
idle VMs can be reclaimed. Oracle's sign-up process can require card verification.
[Always Free terms](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
and [SSH setup](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/connect-to-linux-instance.htm).

A1 is CPU-only. Verify speed on the staged **three-request synthetic smoke** before estimating
the cost in time of the 177-request workload. The synthetic export is separate from the
benchmark export, contains no benchmark prompts or answers, and has a manifest SHA-256 of
`a96613b3accee1a5c2efcceab2183b26fb56a96339e10da3a62d3682dbe9bee5`.

Use the manifest's exact llama.cpp commit and GGUF revision, and verify the model hash on the
host. The CPU smoke changes GPU layers from 99 to 0 and sets generation and prefill threads
to two, retaining the 9,216 context and 512-token reserve. Record the Arm CPU build as a
separate runtime. Check model identity, template and all three exact prompt counts offline
and against the local server before the three completions. Measure long-prompt wall time and
memory use on the VM. Keep the model server on loopback. Linux CPU speed and free-tier
availability remain unverified because no approved host is connected.

From the Mac checkout, the synthetic export can be verified without running Qwen:

```bash
.venv/bin/python -m sn.v2_free_host_smoke check \
  --smoke-plan ../../../outputs/v2-context-smoke-v0.1/context-9216.json \
  --out ../../../outputs/v2-free-cpu-host-smoke-v0.1
```

## Preserve the experiment

The prepared protocol uses the verified 9,216-token context, 512-token reserve, fixed seed
and free decoding. The exported request payloads disable prompt-cache reuse consistently.
Before generation, use the pinned host identity and verify the model, template, context and all
177 prompt token lengths. The first preflight has 355 nominal non-generating requests.
The generation cap is 177. Each dispatch needs a durable ledger entry before send.
Preserve completed keys on resume and count any failed or uncertain dispatch.

For a remote launch, first review the host resource policy and runtime build. Test locally
to the server with a synthetic development prompt. Keep the server bound to loopback and
use an authenticated connection to the host. Transfer only the inference export to an
authorized host. Preserve raw responses and runtime evidence for local scoring after the full
ledger is available. Host provisioning, transfer and measured inference remain pending.

## Reproduce the export

```bash
umask 077
freeze=../../../outputs/v2-exploratory-freeze-v0.1
export_dir=../../../outputs/v2-exploratory-free-inference-v0.1
.venv/bin/python -m sn.v2_exploratory_export check \
  --freeze-manifest "$freeze/manifest.json" \
  --manifest-sha256 837044af132bd981996749cef38509fa7056566be472b14ccaec1946d70ac7f6 \
  --inference-requests "$freeze/inference/requests.jsonl" --out "$export_dir"
```

Use `prepare` with an unused destination to regenerate the export. The original freeze checked
byte for byte. All 177 exported messages and parameters matched the frozen rendering.

All 267 tests passed (247 package, 12 original evaluator and eight power-planning).
