# Joint adjudication: v2-authoring-v0.1 (reviewer side)

Reviewer: Claude (Opus 5.5). Written 2026-11-25, after reading `gold.jsonl`, `task-comparison.jsonl`, `comparison.json`, `receipt.json` and `RESPONSE.md`.

## 1. Answer agreement: confirmed

I checked this myself, not just through your checker. The `answers.jsonl` in the bundle is byte-identical to my saved blind solve. Compared with `gold.jsonl` as parsed JSON, all 32 tasks match exactly, with tool and arguments equal. There are no disagreements to adjudicate.

I agree with your framing. Matching your gold shows the gold is reproducible by one strong reader. It does not show the tasks are hard, test schema understanding, or are ready to freeze.

## 2. Corrections to my notes (I accept your clarifications)

| My note | Correction |
|---|---|
| T016 `regex` default `"false"` called a "schema bug" | Wrong word. In draft-4, `default` is an annotation and doesn't have to match the schema. The schema is valid; the default value is just misleading. |
| T100 `Role` enum with `null` called a "schema inconsistency" | Wrong word. It's legal and simply ineffective: `type: "string"` rejects null. Not a defect. |
| "One `$ref` in use (30)" | Undercount. The targets for both T018 (smart light) and T093 (subtitles) use `$ref`. Correct count: two `$ref`, one `allOf`, no `oneOf`/`anyOf`/conditionals/`patternProperties`. |
| "About half the tasks barely need the schema" | This is my judgement, not a measurement. I agree it should be tested with an ablation (request-only vs request+schema), not stated as a finding. |

I agree that none of the source schemas should be edited.

## 3. Proposed edits: I agree with all of them, with these additions

1. **Email (V2A_4bd142d8e022):** agree. Quote the body, for example: `the body "Please review the agenda."`
2. **Chart (V2A_62eb97df6add):** agree.
3. **Restaurants (V2A_f05a7174f06a):** prefer rewriting over quarantining. Drop "per-person" and "inclusive". The rest of the task is clean.
4. **Poll (V2A_5b498dab538c):** prefer dropping the vote state entirely. `votes` is optional, so the revised gold should leave it out. This also removes the only reason the request mentions voters.
5. **Quiz (V2A_b06aeda7ba28):** prefer giving only the prompt and the correct and incorrect options. The revised gold then leaves out `numberAnswers`, `minCorrectAnswers` and `maxCorrectAnswers` under the omit-unrequested-optionals rule. Stating counts in any wording still scaffolds the mapping.
6. **Smart light (V2A_f3b351c8ad4c):** agree. Suggested wording: "Turn on the Reading nook lamp and set its brightness to 42." Drop "legacy" and "settings object".
7. **Charging (V2A_32c030b44539) and badges (V2A_26fd074e837a):** agree.
8. **Camera (V2A_72095f1392d7) and the omit-defaults policy:** agree, plus one point that matters for E1. The omit-unrequested-defaults rule is part of the scoring contract, so the model under test must be told it in its system prompt. Otherwise exact match penalizes a call that is valid and reasonable (for example, `NetworkSpeed: 0`). Report "valid but extra default fields" as its own error class so it doesn't hide real mapping errors.

## 4. Process points for the revised version

- **I'm no longer blind for this batch.** I've now seen the gold. A blind check of v0.2 should come from a different reviewer, or from a fresh session that receives only the v0.2 packet. My own v0.2 review should be labelled as non-blind.
- **Decide ambiguity handling ahead of time.** For each task, either rewrite it until only one reading is left, or list the accepted alternative answers in the gold before any model runs. Don't decide after seeing model outputs.
- **Catalog redesign:** each task should include at least two near-miss tools from the same domain, and no distractor should appear in more than about 10% of tasks.
- **Keep both versions:** keep each original wording as a paired "hinted" control next to its cleaned revision. The gap between the two is a direct measure of scaffolding.

## 5. Status

- Answer agreement: **resolved (32/32).**
- Wording, difficulty and coverage issues: **open.** They need a versioned revision (v0.2) and a new semantic check.
- Approved test intents: **0.** E1 and E2 remain gated. I agree.
