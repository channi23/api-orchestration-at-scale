# E0 implementation validation

2026-11-13. These are code and model-free checks, not inference measurements.

- Reviewed uploaded Word research assessment, especially Phases 5–7, main `9d7b84f`, and
  Claude's stage-0 commit `ea0a759`.
- Stage 0 PR #2 merged as `807b7db`, after the request-failure fix `f2d98bc`.
- Existing experiment tree is unchanged: `4fc5823a83abd5f498c3c01dc6032bd485ffa13e`.
- Original evaluator: 12 tests pass. E0 package: 29 tests pass, including real localhost fake-server
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

## Source-verified, not executed

At llama.cpp `11fe02151f79c41d0d4af7da708755d73b9c0da6`,
`common/json-schema-to-grammar.cpp` selects `%llguidance` when built with `LLAMA_USE_LLGUIDANCE`,
and `common/sampling.cpp` routes it to the llguidance sampler.
`tools/server/server-context.cpp` exposes the `/props` model path/build/context fields and the
`/apply-template` and `/tokenize` response shapes used by preflight.

## Still requires the user's Mac

No Qwen GGUF weights or llama.cpp build were present in the checked locations. No new model
inference, Metal runtime validation, latency, peak memory, training, tokenizer-template check, or
adapter export was run. Follow `schema-native/README.md` for the exact local commands. E1/E2
remain gated. Preserve the preflight receipt, raw run directory, report and dedicated server log.
