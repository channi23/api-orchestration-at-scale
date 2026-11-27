# Unblinded adjudication — v2-authoring-v0.2

Reviewer: same Claude session that produced the first solve. **This step is not blind.** I have now seen the gold, the comparison and the author response. Nothing here changes the preserved first solve.

## 1. Evidence checks

- The bundle's `answers.jsonl` and `REVIEW_NOTES.md` are byte-identical to the files I sent. My local SHA-256 hashes match `receipt.json` (`fed02474…`, `9b46b55e…`). The blind ZIP hash also matches (`f6e7a5f2…`).
- I compared `gold.jsonl` with my answers on my own, with a type-aware comparison (booleans not equal to numbers, key order ignored, array order kept). Result: 32/32 match. This agrees with `comparison.json`.
- Agreement is weak evidence. The same interpretation by author and reviewer does not show that the task has only one reading. I do not know whether the author and I share an underlying model.

## 2. Corrections to my first notes

I accept these author corrections:

| My first wording | Correction |
|---|---|
| create_place `geo.anyOf` branches "constrain nothing" | Wrong as written. The outer `type: object` still applies. I tested it: `{}` and `{"latitude":"x"}` pass; `5` and `null` fail. Correct statement: the branches do not constrain the coordinate members, but `geo` must still be an object. |
| c8fb `regex` string default called a "schema defect" | Better called "misleading". In draft-4 a default is only an annotation. The schema is legal and nothing fills in a missing value. |
| d63d `Role` enum with `null` called a "schema defect" | Legal but unreachable: `type: string` rejects `null`. |
| "About 16 of 32 catalogs meet the bar" | Too generous. Only the 9 "strong" catalogs clearly meet it. The 7 borderline ones are not verified passes. |
| "Move scaffolding sentences to author metadata" | Accepted refinement. Remove only redundant sentences. Meaning that the model needs (units, per-unit price, time conventions) must stay in the request or in visible tool documentation. |
| Cross-cutting item 5 lists "submit_badge_list is fine" inside a list of weak schemas | Editing slip. submit_badge_list requires `badgelist` and `loc`, so it does not belong in that list. |

## 3. The eight assumption cases

Decision codes: **Keep** = gold stays and the task needs no change for this point. **Rewrite** = gold stays, but the request or the authored tool description must change in a new version so that only one reading is natural. **Hold** = do not use the task until it is rewritten.

| Task | Point | Decision | Reason and fix |
|---|---|---|---|
| f29f | `channel: "telephone"` | **Keep** | The request supplies the word "telephone". Turning it into "phone" would be a change, not an extraction. Score exact string; do not add aliases. |
| 98d2 | `format: "WEB_VTT"`, `"SRT"` | **Keep** | The request supplies both strings exactly. My worry was about the missing enum, not about this task's answer. Score exact strings. |
| 9bda | `method: "email"`, `content_type: "article"` | **Keep** | Both words are in the request, and the policy says to keep every requested detail the tool can represent. So a reply without `content_type` is incomplete, not an equally valid alternative. Declare before any model run that casing variants ("Email") are wrong. |
| 3c06 | `serving_size: "1 medium apple"` | **Rewrite (minor)** | "1 medium" is a fair reading because "apple" repeats the item name. Fix: quote the serving, e.g. `Apple, 95 calories, serving "1 medium"`. Then the gold becomes "1 medium". Or keep the wording and accept only the verbatim string, but say so first. I prefer the rewrite. |
| 3cb8 | item names "Desk lamp", "Cable tray" | **Rewrite** | "two Desk lamp units" leaves the name boundary unclear ("Desk lamp" vs "Desk lamp units"). Fix: "Invoice Harbor Studio for 2 × Desk lamp at 35.50 each and 3 × Cable tray at 12 each." Here "each" already gives per-unit pricing, so the "Both prices are per unit in the same currency" sentence can go. The meaning stays in the request. |
| 3e23 | frames 3 and 18 vs `start`/`end` indices | **Rewrite or Hold** | The source schema says "index" but does not say if counting starts at 0 or 1, or if `end` is included. The request says "frame 3". Nothing in the packet settles this. Fix: say "start at frame index 3 and end at frame index 18". That copies the schema wording, but the value is only clear that way. If you want to avoid the echo, hold the task. |
| 8905 | "named Reading nook" used to identify vs set; brightness → `power` | **Rewrite (tool description)** | The schema has no separate selector. `name` is part of a device-state object. The authored description ("Set the name, brightness level…") makes `name` read as a rename. Fix only the authored description, not the raw schema. For example: "Send a state update for a smart light, given its name, brightness (`power`) and on/off state." Keep 42 as given and do not invent a scale. |
| c8fb | "Treat both as literal patterns" | **Hold until rewritten** | Accepted authoring error. Use the author's wording: "Use these regular expressions exactly as written." Gold `regex: true` stays. |

Result: 3 points are settled with no change (f29f, 98d2, 9bda). 5 tasks need new wording in a later version (3c06, 3cb8, 3e23, 8905, c8fb). Two of those should be held until then (3e23, c8fb).

## 4. Other sentences written for the grader

I sort these by whether the model needs the meaning:

| Task | Sentence | Decision |
|---|---|---|
| 7cb2 | "These are fictional benchmark paths; only produce a tool call" | Remove. Not user speech, and it adds no meaning. |
| 08d0 | "Preserve the listed order of values" | Remove. The system policy already covers order, and "followed by" already gives it. |
| 5168 | "Preserve the quoted HTML" | Remove. The system policy already says to keep strings unchanged. |
| fca0 | "both in the same currency" | Remove. The tool has no currency field, and the sentence does not settle what the price range means. |
| 3cb8 | "Both prices are per unit in the same currency" | Replace with "each", as in section 3. |
| d5eb | "Both times are local wall-clock times in the same time zone" | Remove. The tool format has no time zone and the request names none, so no conversion is likely. If the author wants to block conversion, a shorter natural form is fine: "9:00 to 9:45 local time". |
| c8fb | "Treat both as literal patterns" | See section 3. |

## 5. Catalog ratings

I re-checked each catalog against what the gold selects. Seeing the gold does not change my blind ratings:

- **Strong (9 clearly meet "two or more plausible competing tools"):** 151f, 398e, 3cb8, 3e23, 88b4, d5eb, d63d, dee3, f29f.
- **Borderline (7, not verified passes):** 1e3f, 7cb2, 9bda, 9d7e, b9cd, ef56, fca0.
- **One competitor (9):** 005a, 08d0, 243e, 363b, 5168, 8905, 8c5b, 9c21, b94e.
- **No real near miss (7):** 1f98, 3c06, 5043, 776e, 98d2, a4d7, c8fb.

The kinds of competing tools that would fix the gap catalogs are listed below. They should be chosen from the existing source pool, not written for the task:

| Task | Missing kind of competing tool |
|---|---|
| 1f98 retention | another tool with a seconds/TTL field (cache expiry, session timeout, log retention by days) |
| 3c06 calories | a meal or nutrition logger without a target, or a tool that sets the calorie goal alone |
| 5043 booking resource | a room/resource tool without moderation, or one that books a slot in an existing resource |
| 776e country | another enum selector of places (state, region, other-continent country) |
| 98d2 subtitles | a caption/text-track tool or an audio-track tool with format + URL items |
| a4d7 scoreboard | a single-player score update, or a match-result recorder |
| c8fb annotation filter | another include/exclude filter (file globs, log levels, tag filters) |

## 6. Remaining gates

- Approved test tasks after this adjudication: **0**. This review cannot approve anything; it only gives decisions for the next version.
- The next version needs a new version number and a fresh blind review by a different context. That review should get only the new packet, not this one.
- Before any model run, record the scoring rules for exact strings and the aliases (none, from my side) in visible documentation. Do not add aliases after seeing model output.
- Lineage review for the paired catalogs (005a/5168, 151f/88b4, b94e/dee3, 5043/d5eb, 243e/9c21/fca0) is still open. Keep true pairs on the same side of any split.
