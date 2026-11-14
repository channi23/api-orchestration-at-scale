# E0 whitespace diagnosis (not a new accuracy benchmark)

The completed 1,200-request `e0-clean-v1` remains immutable, from inference commit
`cf2b7e613292b9c048b26ed6aa439ef923af97d3`. Its 95/600 constrained truncations
include 76 outputs ending in at least 128 consecutive whitespace characters, across 15 intents.
One of 600 free outputs was truncated. All failures remain in the published accuracy denominator.

## Mechanism and model-free evidence

The exact pinned llguidance compiler defaults to an unbounded JSON whitespace skip regex.
See bundled `parser/src/json/compiler.rs` (execute), and
[the pinned upstream documentation](https://github.com/guidance-ai/llguidance/blob/d795912fedc7d393de740177ea9ea761e7905774/docs/json_schema.md).
A native-byte-token check of `{"a":"x"}` with 100 spaces after the opening brace found:

| Options | Compact sample accepted | Sample with 100 spaces accepted |
|---|---|---|
| Default flexible | yes | yes |
| whitespace_pattern with `{1,8}` | yes | yes |
| whitespace_flexible false | yes | no |

The regex length bound is not an effective remedy in this pinned engine. Compact mode rejects
whitespace between JSON tokens while retaining spaces inside string values (e.g. `"a  b"`).
This changes the output serialization language; it does not change JSON value constraints.

## Separately saved real probes

Selection rule fixed before probing: the first saved constrained truncation for each of
5-tool, 20-tool, fixed-tool × raw/minified; plus the first successful raw constrained output
for each of those three sizes. This yields nine cases. All six selected failures happen to be
T227_p0 (the same flight-listing intent); the three controls are T106_p0. Therefore this does
not test the other 14 affected intents or estimate population accuracy.

Each case was sent to three conditions, with the original messages, Q8_0 weights, 8K context,
greedy seed-0 settings, disabled thinking and 512-token output cap unchanged:

| Condition | Change from completed E0 | Length finishes / 9 | Engine/request/raw-schema faults |
|---|---|---:|---:|
| llguidance flexible | None; replay baseline | 6 | 0 |
| llguidance compact | Top-level constraint copy x-guidance.whitespace_flexible: true (implicit) → false | 2 | 0 |
| GBNF via response_format | Explicit llguidance grammar → standard response_format under pinned --jinja autoparser | 0 | 0 |

Compact JSON removes the whitespace escape path but two cases instead repeat text inside a
string until the same token cap. GBNF completes the six selected failing cases, but their
returned arguments are still semantically wrong; all three success controls remain successful
in all three conditions. Successful completed constrained outputs are checked against the
prepared envelope and the selected tool's original raw schema; fresh llg-error log entries
are checked separately to reject silent enforcement fallback.

**Conclusion:** a serialization/sampling interaction explains reproduced token-limit failures;
compact mode is a partial workaround, not a proven accuracy fix. No general claim that
constrained decoding is inferior, and no demonstrated case for LoRA, follows from this run.
The next gate is full-envelope preflight and a prospectively specified second-engine comparison,
plus distinct-intent diagnostics. Do not overwrite or silently rerun the completed E0.
E1 and E2 remain gated. No model weights were modified and no training ran.

## Resource and reproduction notes

All 27 pre-request checks: normal memory pressure, nominal thermal state and zero observed active
swap writes (first interval has no rate). The dedicated model was gracefully unloaded after probing;
other apps remained open. No context, batch, offload, quantization, concurrency or output-cap setting
changed. Expected compact-mode effect: fewer formatting tokens, without guaranteeing termination.

Run from schema-native with the same pinned server/profile loaded:

```bash
python -m sn.diagnose_whitespace --source-run e0-clean-v1 --output runs/e0-whitespace-diagnostic-v1
```

The diagnostic freezes all payloads and skips saved requests on an identical plan. It refuses changed
source/output/server identity. Keep the original source run (including compressed prompts); public
path-redacted plan/results are compressed alongside this report. This diagnostic is outcome-selected,
not the frozen E0 protocol. Use a separate output directory for a changed plan.
