# v2 argument review on development tasks

Protocol locked on 2026-11-27 before generation. The
[exploratory audit](../v2-exploratory-baseline-v0.1/ARGUMENT_AUDIT.md)
motivated a single second pass for argument selection. The comparison uses all
11 saved first calls from the separate [API development pilot](../v2-dev-free-v0.1/PILOT_RESULTS.md).
These are known development examples. All 11 receive one review, including the
previously correct calls.

Each review sees the original request, the tool selected on the first call with
its description and raw schema, and the first arguments. The prompt asks it to
retain requested values even if they equal a default, remove unsupported
additions, and preserve correct arguments. It returns just an argument object.
The offline scorer attaches the original tool name and uses the same exact-call
and raw-schema rules as the first pass. There is no fallback to the original
arguments, so a failed second pass counts against this arm. No expected answer
or evaluation label enters a review prompt.

Report exact corrections and regressions, argument error categories, prompt and
completion tokens, and added wall time. A useful development signal is a net
increase in exact calls with zero regressions. Token counts measure additional
work. This small comparison measures neither deployment cost nor generalization.

Use the exact first-pass Qwen3-1.7B Q8_0 Metal runtime, 8,192-token context,
512-token output reserve, greedy sampling, disabled thinking, and enabled
prompt cache. The treatment changes the prompt and fixes the selected tool.
All 11 locked prompt lengths are between 284 and 1,104 tokens.

The cap is 11 generation attempts and 28 non-generating requests. A successful
first preflight uses 23 metadata requests. The remaining five allow fresh
server checks or unfinished preflight work on a resumed segment. The existing
runner durably charges each request before dispatch. It checks the 5 GiB memory
floor at admission, waits for three normal readings after load, monitors
memory pressure, thermal state and swapout, and unloads its own server on stop.
A non-resumable fault or an unanswered generation charge blocks automatic
retry. Saved completed generation keys carry over on any permitted resume.

## Reproduce locally

Use the existing development ledgers and pinned tokenizer from `schema-native/`.
Preparation writes a model-visible plan to a new path. Its SHA-256 is
`ea231ea481daebd3ec337b9888af28c395649ac0575a0014ff460952e36a9772`.

```bash
umask 077
bundle=../../../outputs/v2-argument-review-v0.1-sealed.json
sha=ea231ea481daebd3ec337b9888af28c395649ac0575a0014ff460952e36a9772
.venv/bin/python -m sn.v2_argument_review prepare --bundle "$bundle" \
  --tokenizer ../../../outputs/v2-holdout-candidate-b-v0.1-authoring/qwen-tokenizer.json
.venv/bin/python -m sn.v2_argument_review run --bundle "$bundle" --plan-sha256 "$sha"
.venv/bin/python -m sn.v2_argument_review report --bundle "$bundle" --plan-sha256 "$sha"
```

The frozen exploratory benchmark, its original scores, and model weights are
outside this run. E1 and E2 stay gated.
