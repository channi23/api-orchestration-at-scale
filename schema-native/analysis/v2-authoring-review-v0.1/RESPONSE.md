# Response to the first blind task review

**2026-11-25. Answer comparison complete; joint adjudication and dataset approval are not complete.**

## What was received and checked

Claude reports solving all 32 tasks before seeing the draft gold, PR or authoring source. The
uploaded answers and notes match the copies in outputs/claude-blind-review byte-for-byte. They
are preserved unchanged here as [answers.jsonl](answers.jsonl) and [REVIEW_NOTES.md](REVIEW_NOTES.md).
[receipt.json](receipt.json) records their hashes, the original blind ZIP hash, draft/source identity
and the reviewer's self-reported independence. File contents cannot independently prove what the
reviewer previously saw or what schemas appeared in its pretraining.

**All 32 reviewer tool choices and argument objects agree with the author gold**, using the existing
number-aware/object-order-insensitive comparison; all 32 reviewer calls validate against their
selected tool's raw schema. There are no answer disagreements. The email body includes its final
period in both answers, the chart is one call with two series in both, and NetworkSpeed is omitted
in both. Regex strings contain one actual backslash before the literal period.

See [gold.jsonl](gold.jsonl), [task-comparison.jsonl](task-comparison.jsonl) and the unchanged-helper
output [comparison.json](comparison.json). `requires_adjudication: false` in that helper means no
**answer mismatch**; it does not resolve the reviewer's wording/coverage objections or approve a task.

This is author/reviewer agreement on drafts, **not a Qwen accuracy result**, a hardness result or
evidence of schema-understanding generalization. No task, gold, schema or earlier result was edited.
The initial authoring manifest is an unchanged historical snapshot; review receipt is recorded here.

## Findings accepted as design problems

| Finding | Evidence / disposition |
| --- | --- |
| Weak and repeated distractors | Independently counted: submit_ballot, set_video_subtitles and start_charging_transaction each appear eight times as distractors; search_recipes_by_ingredients appears five times. The reviewer's seven-near-competitor count is a judgement, not an independently measured ambiguity rate. Redesign future catalogs with reviewed domain/role near misses. |
| Requests sometimes scaffold field mapping | Explicit values are necessary, but title echoes, wrapper hints and default-related wording can make mapping easier. Remove unnecessary hints in a versioned revision; retain exposed originals for documentation or paired development controls. "About half need no schema" remains a reviewer assessment until a separately approved ablation measures it. |
| Little hard-keyword coverage | Confirmed for target schemas: two contain $ref (T018 and T093), one allOf (T232); none contain oneOf, anyOf, conditionals/dependencies or patternProperties. This is an API authoring tranche, not the planned assertion-keyword stress track. Do not add assertions to source schemas just to increase coverage counts. |
| Weak validators | Confirmed: T079 accepts an empty object; T093 accepts a subtitle entry without a URL. Such responses fail our task-specific exact argument contract despite validating. Preserve raw schemas and report validity separately from task correctness. |
| No established hardness or transfer | Agreement is compatible with easy tasks. Known family overlap T033 remains development-only; source, structural lineage, pretraining exposure and remaining eligibility work are unresolved. No task is promoted to locked test. |

## Task-specific triage, before any revision

| Tool / original task | Agreed gold and issue | Proposed next revision or clarification |
| --- | --- | --- |
| send_email / V2A_4bd142d8e022 | Both include `Please review the agenda.` with its period, but the wording can be read two ways. | Quote the body literally. Preserve the original and any revision separately. |
| push_chart_update / V2A_62eb97df6add | Both produce one call containing two ordered series. | Say "one update containing two series" rather than "two updates". |
| search_restaurants / V2A_f05a7174f06a | Both use the same price bounds, but per-person and inclusive semantics are undocumented. | Rewrite the request to remove unsupported qualifications, or quarantine it. Do not silently discard details while keeping the same request. |
| create_poll / V2A_5b498dab538c | Both supply empty votes arrays and retain the question mark. Voter-identity semantics are undocumented. | Quote the question; describe only the representation the tool documents, or omit an unrequested vote state. Do not invent a voter-ID convention. |
| create_multiple_choice_question / V2A_b06aeda7ba28 | Counts agree, but answer-list counts and a learner's selection limits are different concepts. | Rewrite to match the documented list-count semantics; do not reinterpret the API fields. |
| set_smart_light / V2A_f3b351c8ad4c | Both map brightness to power inside the referenced wrapper. The request echoes the legacy schema title and wrapper. | Remove unnecessary title/wrapper hints. Keep the supplied brightness value without inventing a scale. |
| start_charging_transaction / V2A_32c030b44539 | Both preserve meterStart=18420. | Say "meter reading" and remove the redundant instruction to keep the number unchanged. |
| submit_badge_list / V2A_26fd074e837a | Both preserve the listed URI order. | Replace "priority-list order" with an unambiguous list-order instruction; do not imply automatic sorting. |
| configure_camera_network / V2A_72095f1392d7 | Both omit NetworkSpeed and the read-only MACAddress. | The authoring contract already omits unrequested defaults. Make that policy explicit in future review packets; schema validity alone must not decide whether a default-valued extra field is acceptable. |
| configure_sprite_animation, record_temperature_event, generate_invoice | Integer-looking and fractional JSON numbers already compare by mathematical value; booleans remain distinct. | No scoring-rule change needed. Array order and exact string/key spelling remain significant. |

These are proposed edits, not silently applied corrections. Any revised request needs its own
version and another semantic check, even where the numeric gold is unchanged. Review agreement
does not resolve alternative valid interpretations of the original wording.

## Two schema clarifications

- **T016:** a boolean field with `default: "false"` has a misleading default value that does not
  itself satisfy the boolean schema, but the schema passes its draft-4 metaschema. Default is an annotation and does not
  fill missing values during validation. JSON Schema says defaults should match their schema but
  does not require that for schema validity. [Official annotation documentation](https://json-schema.org/understanding-json-schema/reference/annotations)
- **T100:** including null in an enum alongside string values while also requiring `type: "string"`
  is legal. Both constraints apply, so null is rejected and the matching strings remain allowed.
  The null entry is ineffective, not evidence of an invalid schema. The pinned draft-4 validator
  confirmed both metaschema acceptance and rejection of null as a Role value.

Do not modify either source schema to "fix" these quirks in an unchanged-source comparison.
For the same reason, ignored keywords at inapplicable instance types and weak required lists are
capability/contract observations, not permission to rewrite the original tool schema.

## Verification and next gate

The existing blind-review checker was run on the received files, including exact 32-task coverage,
strict JSON parsing, raw-schema validation and semantic comparison. The 15 targeted authoring tests
pass, the original authoring audit still reproduces with --check, and review-file hashes were checked.
No runtime implementation or scoring rule changed, so the previously passing 193-test suite was not
rerun in full just to copy review evidence. No local model load, model-endpoint inference or training ran.

Next: provide these gold answers and this response to Claude for the requested unblinded comparison;
jointly resolve the remaining wording/contract issues before authoring a versioned revision and
harder catalogs. Full lineage/source checks and the separate keyword stress track remain future
work. **Accepted test intents remain zero. E1/E2 remain gated.**
