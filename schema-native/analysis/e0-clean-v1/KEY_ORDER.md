# Clean E0: post-hoc key-order audit

This extends the pilot concern raised in external feedback to the **completed clean run** and the
**exact bundled llguidance 1.0.1 static library**, not standalone 1.9.1. No inference was run.
Data, prompt and schema bytes are checked against the recorded inference identity; the original
inference source files are reconstructed from its recorded Git commit for that check.

The native helper receives identical JSON values in original key order and schema key order,
serialized compactly in both cases. An output is classified as rejected *only for order* when
original order is rejected but reordering the same value makes it accepted. This includes envelope
and nested argument object order, not just the outermost object. It does not prove that order
caused a particular sampled token decision.

| Free-correct output category | Requests | CD correct | CD wrong | CD truncated |
|---|---:|---:|---:|---:|
| Accepted in original order | 249 | 249 | 0 | 0 |
| Rejected solely for order | 252 | 140 | 40 | 72 |
| Rejected for another tested reason | 0 | 0 | 0 | 0 |

501 of 515 free-correct outputs are strict tool-call JSON eligible for this test; 14 have non-JSON
wrappers and are excluded from this diagnostic only. The 252 order-only cases span 35 tools.
Requests share tool intents/paraphrases/catalogs and are not independent observations. All 95
constrained truncations are legal grammar prefixes, so truncation is not evidence of engine fallback.
Byte-token reachability is not a model-tokenizer or per-token-logit trace.

This strongly supports an order-related mechanism in the clean run. It does not establish a causal
order effect without a controlled intervention. Gold reachability in the earlier audit used
schema-ordered keys and therefore did not measure acceptance of model-preferred serializations.
The original primary accuracy result remains 85.5% free vs 70.5% constrained on pooled raw selection.
A post-hoc subset where both outputs finish is 87.5% vs 83.3% over 168 pairs; it conditions on an
outcome and must not replace the all-200-pair primary comparison or establish a causal effect.

## Additional model-free separator check

The exact bundled engine accepts fixed human-readable separators via top-level x-guidance:
`whitespace_flexible: false`, `item_separator: ", "`, `key_separator: ": "`.
For a two-property schema it accepts `{"a": "a  b", "b": 1}`, rejects the compact equivalent under
that formatting policy, and still rejects swapped key order. Spaces inside strings are preserved.
This is support evidence only; there is no measured accuracy result for this setting.
The prior bounded-whitespace-regex check did not enforce the bound in this engine version.

## Research gate and next controls

E1/LoRA remains gated. Before a new full run, specify and validate:

1. A diagnostic oracle-order condition that uses only free-output key order to reorder properties
   in constraint copies. It must preserve validation semantics and be labeled an oracle diagnostic,
   never a deployment baseline. Define nested properties/arrays/alternatives/missing keys and how
   to handle invalid free outputs. Do not use gold values to choose a schema branch or retry.
2. A validate-then-constrain deployment baseline. Route using syntax, envelope and the chosen tool's
   raw-schema validity only; a schema-valid semantic error cannot be detected using gold answers.
   Report total latency/tokens of the free attempt plus any retry and score every task.
3. A second-engine condition and fixed readable separator control, with all 70 envelopes preflighted,
   gold reachability qualified by key order, raw-schema enforcement checks and prospective run IDs.

Keep the completed E0 frozen. Do not pool outcome-selected diagnostics with the benchmark or silently
replace settings. Do not modify model weights or start fine-tuning based on this artifact.

Reproduce from schema-native, with no model server needed:

```bash
scripts/build_native_audit.sh
python -m sn.order_audit --run e0-clean-v1 --output analysis/e0-clean-v1/key-order-audit.json
python -m sn.report --run e0-clean-v1 --server-log runs/e0-clean-v1/clean-server-sessions.log --order-audit analysis/e0-clean-v1/key-order-audit.json
```

See `key-order-audit.json` for row-level acceptance/prefix evidence and build hashes. The helper build
record is verified before use. Existing E0 metrics/raw responses are preserved; reporting changes
separate `cd_truncated` from ordinary malformed outputs and add descriptive truncation sensitivity.
