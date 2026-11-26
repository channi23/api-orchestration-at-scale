# v2 context profile smoke test

Locked on 2026-11-26. This compares two separate local Qwen3-1.7B profiles on
synthetic development prompts. The [held-out tokenizer audit](../v2-holdout-candidate-b-v0.1/README.md)
found a maximum of 7,792 compact prompt tokens, requiring 8,304 total with the existing
512-token output reserve.

| Setting | Reference | Candidate |
| --- | ---: | ---: |
| Context window | 8,192 | 9,216 |
| Estimated Metal KV allocation | 896 MiB | 1,008 MiB |
| Max generated tokens per request | 512 | 512 |
| Cold prompt caching policy | Off | Off |
| Hard generation request cap | 2 | 3 |
| Non-generating metadata requests | 5 | 7 |

The candidate configuration changes only context among model and server parameters.
Additional context is expected to add 112 MiB of Metal KV storage. For this comparison, the
benchmark request's prompt cache is off in both arms to exercise the full prompt each time.
Previous measured v2 runs used prompt caching. The historical profile is untouched.

The catalog contains 20 synthetic tools and uses lossless compact JSON. Shelf-reference
examples in the decoys calibrate its size. The first two messages are identical across both
profiles. The 9,216-token candidate also receives a longer input.

| Input | Offline prompt tokens | With output reserve | Profiles |
| --- | ---: | ---: | --- |
| Short control | 1,397 | 1,909 | Both |
| Long shared control | 7,363 | 7,875 | Both |
| Extended control | 8,389 | 8,901 | 9,216 only |

Run the reference first and unload it before the candidate. Each server must have
normal memory pressure, nominal thermal state and at least 5 GiB available before loading.
The launcher requires the standard settle window and monitors pressure, thermal state,
swap rate and the 1 GiB cumulative swapout hard limit. It records an environmental or request
fault and stops without retry. Online context and lengths must match the locked plan before
generation. The 8,389-token input is never sent to the smaller context. Successful generation
of a short exact call on the extended input, together with clean resource readings, is the
hardware smoke check. Accuracy and multi-hour resource behavior need separate evidence.
No private held-out task or training data is an input.

**Both runs completed.** See the [measured results](RESULTS.md).

## Reproduce

Run from `schema-native/` in the existing environment. Supply the pinned tokenizer JSON from
the earlier tokenizer audit. Both model-free plans pin the model, server and chat template.
Two separate local output directories retain run ledgers, reports and host resource logs.
The pre-existing reports can be reproduced at their respective originating runner commits.

```bash
umask 077
tokenizer=../../../outputs/v2-holdout-candidate-b-v0.1-authoring/qwen-tokenizer.json
plans=../../../outputs/v2-context-smoke-v0.1
.venv/bin/python -m sn.v2_context_smoke prepare --tokenizer "$tokenizer" --plan-dir "$plans"
.venv/bin/python -m sn.v2_context_smoke run --tokenizer "$tokenizer" --plan-dir "$plans" \
  --context 8192 --approved-plan-sha256 bd3c9abfcb76a3784a87d7f71948aefefb9e4ac0474fca09e1234169627b79ce
.venv/bin/python -m sn.v2_context_smoke run --tokenizer "$tokenizer" --plan-dir "$plans" \
  --context 9216 --approved-plan-sha256 c1c39caf261032567c1038357b949f3e8767abf7b60760f4d09e21f51e5eb600
```
