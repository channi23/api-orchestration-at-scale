# E0 implementation validation

2026-11-13. These are code and model-free checks, not inference measurements.

- Reviewed uploaded Word research assessment, especially Phases 5–7, main `9d7b84f`, and
  Claude's stage-0 commit `ea0a759`.
- Stage 0 PR #2 merged as `807b7db`, after the request-failure fix `f2d98bc`.
- Existing experiment tree is unchanged: `4fc5823a83abd5f498c3c01dc6032bd485ffa13e`.
- Original evaluator: 12 tests pass. E0 package: 40 tests pass, including real localhost fake-server
  tests, changed-config resume refusal, partial-report gating, duplicate rejection, online constraint
  negative controls and context-overflow rejection.
- Frozen offline plan: 1,200 unique paired requests and 70 unique envelopes. Both 5- and 20-tool
  catalogs and the fixed-tool family are present; raw and minified/free and constrained arms pair.
- Shell syntax and Python compilation checks pass.
- Test environment: Apple arm64, Python 3.14, jsonschema 4.26.0, NumPy 2.5.3, SciPy 1.18.1,
  pytest 9.1.1. Setup recommends Python 3.13; its full fresh-install path has not been executed.

## Standalone engine check

`envelope-byte-audit.json` records a model-free llguidance **1.9.1 byte-tokenizer** check of the
actual E0 envelopes. 67/70 compile; all 270 gold task/catalog pairs in those envelopes are reachable.
Reproduce with `python -m pip install -r requirements.txt` then
`python -m sn.audit_e0 --output runs/e0-envelope-byte-audit.json`.
`test-environment.txt` records the exact installed test environment (including optional audits;
it is not the recommended lightweight E0 install). Three 20-tool envelopes refuse compilation:

- `C020_R05`: unsupported `dependencies`;
- `C020_R06`: unknown format `cidr`;
- `C020_R09`: unknown format `path`.

This is not the pinned llama.cpp binary or its real model tokenizer, so it does not establish the
runtime refusal rate. The mandatory online preflight repeats envelope probes through the actual
server and saves any explicit refusals. If reproduced, these affect both constrained representations;
do not treat them as model misunderstandings or silently delete these tasks. Investigate a documented,
semantics-preserving preparation policy or a second engine before model-quality or E1 conclusions.

## Source and runtime checks

At llama.cpp `11fe02151f79c41d0d4af7da708755d73b9c0da6`,
`common/json-schema-to-grammar.cpp` selects `%llguidance` when built with `LLAMA_USE_LLGUIDANCE`,
and `common/sampling.cpp` routes it to the llguidance sampler.
The `--jinja` autoparser instead builds GBNF for `response_format`; a real probe reproduced this.
E0 explicitly sends `%llguidance` in the native `grammar` field to avoid that route.
`tools/server/server-context.cpp` exposes the `/props` model path/build/context fields and the
`/apply-template` and `/tokenize` response shapes used by preflight.

## Real Mac runtime (incomplete checkpoint)

The Metal device probe succeeds with the required system access. The pinned llama.cpp server and
quantizer build; server `--version` reports `11fe021`. The official Q8_0 GGUF downloads and matches
the pinned SHA-256. Actual hardware: Apple M4, 10 CPU cores, 17,179,869,184 bytes RAM (16 GiB).
Server diagnostics at verbosity 4 confirm all 29 layers offloaded to the GPU.

The real 12-request path smoke completes, with four engine-failure rows recorded separately.
Full online preflight checks all 600 distinct prompts: maximum input length 6,185 tokens, with
512 output tokens reserved inside 16,384 context. It finds **11/70** envelope refusals in the bundled
llguidance **1.0.1**, commit `d795912fedc7d393de740177ea9ea761e7905774`. This is distinct from the
standalone Python 1.9.1 check above. `format: uri` is an additional refusal. The pinned server can
return HTTP 200 after llguidance failure; fresh log monitoring detects this and prevents false
constrained success. Completed constrained outputs are independently envelope-validated as well.

The original E0 stopped at **588/1,200** saved requests for host-resource constraints, with 120
engine failures kept separate. The partial report contains no paired inference. An interrupted
in-flight request was never written, preserving all saved latencies. The original configuration
remains unchanged. All other user apps were left open. No model weights were modified or trained.

A separate sustainable profile was added: context 8,192, batch 512, microbatch 128, 2-second pacing,
normal-pressure admission and an active-swap guard. Its measured KV allocation is 896 MiB rather
than 1,792 MiB; model RSS was roughly 2.6 GiB rather than 3.5 GiB. It still produced warning pressure
with the current host workload, and was unloaded before benchmark requests. It is **not** a completed
accuracy or multi-hour stability validation. It must use a new run ID.

Final validation: 40 package tests and 12 original evaluator tests pass. The complete setup script
was rerun successfully (39 tests at that point; the final guard regression adds the 40th) with the existing Python 3.14 environment and cached weights/build. Fresh
Python 3.13 installation remains untested. Exact rendered input files, raw schema byte order, runtime
binary and CMake cache identity are included in the tightened checks. E1 and E2 remain gated.
