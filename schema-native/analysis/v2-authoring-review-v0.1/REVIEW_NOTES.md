# Blind review notes: v2-authoring-v0.1 (32 tasks)

Reviewer: Claude (Opus 5.5). Solved on 2026-11-25 using only `tasks.jsonl` and `REVIEW_INSTRUCTIONS.md`.

## Independence statement

- I have not seen the author gold, the draft source or the PR diff. This first solve was saved before any of them were shown to me.
- I don't recognize these 32 tasks or their gold. Many of the schemas come from public sources: OCPP 1.6 messages, Washington Post ANS, O3D3xx camera configs, PayPal item, GTM server-side events, Glaive-style function-calling tools. I may have seen those schemas during training and can't rule that out.
- All 32 answers validate against the selected tool's schema (checked with Python `jsonschema`, Draft 4 and default validators). That only shows they are well-formed, not that they are correct.

## Summary

1. **Tool choice was clear in all 32 tasks.** None had two equally good tools. Only 7 tasks had a nearby competitor that is plausible on the surface. By 0-based line number in `tasks.jsonl`, these are tasks 3 and 5 (start vs. reserve charging), 11 (invoice vs. order item), 15 (temperature event vs. observed property), 23 (calendar event vs. meeting), 26 (search vs. book hotel) and 30 (smart light vs. LEDs). In each case the schema settled it, mostly through a required field the request does not give (location, room_type, currency) or a missing field (participants).
2. **Distractors repeat and are mostly unrelated.** `submit_ballot`, `set_video_subtitles` and `start_charging_transaction` each appear as distractors in 8 of the 32 tasks, and `search_recipes_by_ingredients` in 5. With most five-tool catalogs, the description alone picks the tool.
3. **Many requests leak schema structure.** The wording often echoes field names or roles, so the schema matters less. Examples: "include an empty voter list for each option" (poll), "set both the minimum and maximum correct-choice counts" (quiz), "Include only those three settings inside the device's settings object" (light), "the two full unit names" (temperature), "Use the supplied seconds value directly" (retention), "the contact-channel label" (transactions), "Do not use the default country". Since extracting values from the request is expected, the key question is whether the *mapping* needs the schema. For about half the tasks it barely does.
4. **Tasks where the schema is genuinely needed** (best for your research question):
   - `V2A_80b2125e94bc`: "before and after images" must map to enum `NEW_AND_OLD_IMAGES`.
   - `V2A_f3b351c8ad4c`: brightness goes in a field called `power`, nested under the dotted key `core.brightlight` through a `$ref`.
   - `V2A_de6e78397ddf`: "one daily data point" maps to `period: "day"`; field names use a leading underscore.
   - `V2A_72095f1392d7`: exact field names like `StaticIPv4SubNetMask`; read-only fields have to be left out.
   - `V2A_d026f2a3c41f` and `V2A_e27215c42b11`: choosing the tool depends on which tool's required fields can be satisfied.
   - `V2A_02d9ad89eef7`: "combine 7 images" maps to `NumberOfImages`.
5. **Few hard schema features.** One `$ref` in use (30), one `oneOf` (only in a distractor, task 15), `allOf` once (18), and enums in a few tasks. There are no conditionals (`if/then/else`), no `anyOf` in a target, no `patternProperties`, and no deep nesting beyond two levels.

## Per-task notes (only tasks with something to flag)

| Task | Issue | Type |
|---|---|---|
| `V2A_4bd142d8e022` (email) | "the exact body Please review the agenda. Attach…": it's unclear whether the final period belongs to the body or ends the sentence. I kept the period. A gold without it is equally defensible. Quoting the body would fix this. | Ambiguity |
| `V2A_62eb97df6add` (chart) | "Push two updates" could mean two separate tool calls of one series each, or one call with two series. The answer format allows one call, so I sent one call with two series. Recommend rewording to "one update with two series". | Ambiguity |
| `V2A_5b498dab538c` (poll) | "voters" is mapped onto `votes` (array of strings). The schema doesn't say the strings are voter IDs; that's an undocumented convention. The schema also puts `additionalProperties: false` on an array, which has no effect. I assumed the question mark is part of the question. | Undocumented convention, schema quirk |
| `V2A_600d4fd25755` (annotation filter) | The `regex` default is the string `"false"` on a boolean field, which is a schema bug. The backslash in `^public\.` needs JSON escaping (`"^public\\."`). Check that the gold stores one literal backslash. | Schema bug, string fidelity |
| `V2A_32c030b44539` (start charging) | "Keep the supplied meter number unchanged" is unnatural, and "meter number" could be read as a meter ID rather than the reading. | Unnatural wording |
| `V2A_b06aeda7ba28` (quiz) | The request says min/max are counts "that must be selected". The schema says they are the number of correct answers "in the list of possible answers". Both give 2 here, so the values agree, but the field-role explanation in the request doesn't match the schema. The request also states every value directly. | Unsupported interpretation, leakage |
| `V2A_bf407e74af45` (team user) | The `Role` enum includes `null` while `type` is `string`, a schema inconsistency (harmless here). | Schema bug |
| `V2A_72095f1392d7` (camera network) | "Do not change … network speed" means leaving `NetworkSpeed` out. A gold that fills in the default `0` would also validate, so the scorer has to treat omitted and default values consistently. | Scoring convention |
| `V2A_d026f2a3c41f` (meeting) | Time zone is intentionally absent, and the format `YYYY-MM-DD HH:mm` matches the request. No issue beyond confirming the gold uses `schedule_meeting`, since `create_calendar_event` needs a location that isn't given. | Check |
| `V2A_f05a7174f06a` (restaurants) | "per-person" and "inclusive" have no counterpart in the schema. The schema doesn't say whether `min`/`max` are inclusive or what unit they use. The task can't fully preserve the request. | Can't preserve all details |
| `V2A_f3b351c8ad4c` (light) | "legacy brightness-controlled lamp" echoes the schema title "Legacy Brightlight", which is a leak. The brightness scale (0–100? 0–255?) isn't documented, so 42 is passed as given. | Leakage, undocumented scale |
| `V2A_239ffd38aded` (sprite) | The schema description contains a stray `</a>`. Numbers are typed `number`, so 3 and 3.0 are equal. The scorer should compare numbers by value. | Schema quirk, scoring |
| `V2A_9274a53ec79e` (temperature event) | `68` vs `68.0`: same point about numeric comparison. | Scoring |
| `V2A_26fd074e837a` (badges) | "in priority-list order" is odd wording: the order is the given order, not sorted by priority. It happens to be descending either way, so it's harmless here but confusing. | Unnatural wording |
| `V2A_7e394274b213` (invoice) | `add_order_item` is a reasonable near-miss, but it takes one item and requires `currency`, which isn't given. `generate_invoice` is correct. Price 12 is sent as a number; the scorer should accept 12 and 12.0. | Check |
| `V2A_e945a0d037a6` (subtitles) | `subtitle_url` has no `required` and no `type`, so a call missing `url` would still validate. Validator success is weak evidence here. | Weak schema |
| `V2A_e983302baf08` (geo path) | The top-level object has no `required`, so an empty `{}` validates. Same weak-validator issue. | Weak schema |

## Recommendations before freezing

1. Swap the repeated unrelated distractors for near-miss tools from the same domain (for example, two charging tools in every charging task, or two scheduling tools).
2. Remove the wording that echoes schemas (the phrases listed in Summary point 3) from at least half the tasks. Keep a few leaked versions as a paired control so you can measure the effect.
3. Add tasks whose target schemas use `if/then/else`, `anyOf`/`oneOf` branch selection, `$ref` chains and nesting at three or more levels. The current tranche mostly tests flat field mapping.
4. Fix the email-body period and the chart "two updates" ambiguity before scoring.
5. Write the scoring rules down: numbers compared by value, how omitted vs. default values are treated, exact string match, array order matters.
