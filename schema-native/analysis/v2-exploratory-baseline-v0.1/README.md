# Exploratory baseline host handoff

2026-11-27. The [frozen exploratory dataset](../v2-exploratory-freeze-v0.1/README.md) has
a private inference export with 177 ordered requests. Its manifest SHA-256 is
`c8b0e552f59a44db90fd274f6d6a4d78afa8332b3cb525df32b3fe8ba2befe03`.
The export contains only request payloads and a runtime handoff manifest. The expected answers,
lineage records and scorer stay on the Mac. The export can be checked byte for byte and
has never been sent to a remote host.

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

## Preserve the experiment

The prepared protocol uses the verified 9,216-token context, 512-token reserve, fixed seed
and free decoding. The exported request payloads disable prompt-cache reuse consistently.
Before generation, use the pinned host identity and verify the model, template, context and all
177 prompt token lengths. The first preflight has 355 nominal non-generating requests.
The generation cap is 177. Each dispatch needs a durable ledger entry before send. A future
launcher must preserve completed keys on resume and count any failed or uncertain dispatch.

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
