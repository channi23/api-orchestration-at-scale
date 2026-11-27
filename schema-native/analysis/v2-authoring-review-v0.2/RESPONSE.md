# Response to the fresh-context v0.2 review

**2026-11-25. Answer comparison complete; semantic and catalog adjudication remains open.**

## Evidence and comparison

The received answers_1.jsonl and REVIEW_NOTES_1.md are preserved byte-for-byte as
[answers.jsonl](answers.jsonl) and [REVIEW_NOTES.md](REVIEW_NOTES.md). [receipt.json](receipt.json)
records hashes, the exact blind packet and authoring manifest, and the source commit. The reviewer
reports using only the packet and discloses an unrelated automatic profile snapshot. This supports
a self-reported fresh-context blind solve, not proof of independence or a different underlying
model. Prior exposure to public schemas during pretraining remains unknown.

**All 32 answers match the v0.2 gold under the existing JSON comparison and all 32 validate against
the selected raw schemas.** No default-only, wrong-tool or other answer mismatch was found. This
comparison does not resolve ambiguity merely because the reviewer chose the same interpretation.
Eight tasks are explicitly marked assumption-bearing in task-comparison.jsonl.

[gold.jsonl](gold.jsonl) now supplies the requested gold disclosure; [task-comparison.jsonl](task-comparison.jsonl)
puts the answers side by side. [comparison.json](comparison.json) is the existing checker output.
These are draft-author/reviewer comparisons, **not Qwen inference results or a benchmark accuracy claim**.
No original request, gold, schema, scoring rule or previous review has changed.

## Findings accepted for adjudication

| Finding | Author disposition |
| --- | --- |
| Regex wording | Accepted authoring error: "literal patterns" can suggest disabling regex despite the preceding instruction. A future version should say "Use these regular expressions exactly as written". Gold currently uses regex=true; do not treat agreement as resolving the wording. |
| Grader-oriented asides | Remove genuinely redundant instructions such as "fictional benchmark paths; only produce a tool call" from user speech. Shared output/string/ordering policy belongs in visible system instructions, not repeated as user requests. |
| Units, price conventions and time interpretation | Do **not** move necessary semantics into hidden author metadata. If per-unit pricing or wall-clock conventions are needed, keep them in the request or model-visible tool documentation. Remove only redundancy; if the source does not define a needed convention, rewrite or withhold the task. |
| Tool-description echoes | The six-word/name guard is only a narrow automatic check. Paraphrase naturally and add genuinely confusable tools; removing every shared domain word would not itself establish schema understanding. |
| Frame indexing and smart-light naming | The new questions about frame number versus index and identifying versus setting a lamp name require explicit contract review. Keep the supplied brightness value without inventing a scale. |
| Free-text values and aliases | A missing enum does not make every schema-valid string correct. Preserve explicitly supplied strings where required; decide/document any acceptable semantic aliases before model runs. Do not silently add alternatives after observing a model's output. |
| Weak schemas | Schema validity alone is insufficient. Keep task-specific correctness checks; do not tighten the original source schemas to manufacture stronger validation. |
| Catalog quality | The reviewer rates nine catalogs strong, seven moderate/borderline, nine with one competitor, and seven without a real near miss. "About 16" includes the seven borderline cases; it is not a verified count of 16 passing catalogs. No catalog/task is automatically approved. |
| Related tasks and splits | Shared or swapped-tool catalogs motivate a lineage review, not a rule that any reused distractor merges all tasks. Keep actual derived/sibling/paired intents together; apply source/family audits before any train/test assignment. |

The eight assumption-bearing tasks are serving-size wording (3c06), invoice item-name boundaries
(3cb8), animation indexing (3e23), lamp-name/brightness mapping (8905), share-event labels (9bda),
regex wording (c8fb), transaction-channel vocabulary (f29f), and subtitle format strings (98d2).
The matching gold is available for each; possible alternatives remain a joint adjudication issue.

## Schema terminology: legal but weak is different from invalid

The fresh reviewer did not see earlier corrections, so these are repeated for the unblinded phase:

- T016's string default on a boolean field is misleading, but its default is an annotation and does
  not make the draft-4 schema invalid or automatically fill a missing input.
- T100's null enum member is legal but excluded by its simultaneous string type requirement.
- T089/create_place.geo has an outer `type: object`. Its anyOf branch keys such as latitude and box
  are unknown keywords at those schema positions, not property declarations. The branches are legal
  but do not constrain those coordinates. The pinned validator accepts `{}` and arbitrary object
  members for geo while rejecting null, numbers, strings and arrays because the outer type remains.

Thus the new geo observation is a real weakness, but "invalid subschemas" or "constrains nothing"
without the outer-type qualification is inaccurate. The raw schema must remain unchanged.

## Current gate and verification

- Strict 32-task answer coverage, raw-schema validation and number-aware/object-order-insensitive
  argument comparison ran through the existing sn.v2_revision checker. Eight reviewer-assumption
  flags were joined to the matching task IDs; no answer was renamed or repaired.
- The 26 authoring/revision tests passed, both authoring versions still reproduce with --check,
  and review-source hashes and new document links were checked. No runtime implementation changed,
  so the previously passing 204-test suite was not rerun in full merely to archive received evidence.
- v0.1 and v0.2 source/gold, original receipts, E0/E0b publications, experiment/ and model settings
  remain unchanged. No local model loading, model-endpoint inference, tool execution or training ran.

Next: give this gold bundle to the reviewer for the requested unblinded comparison and resolve the
eight assumption cases plus catalog ratings before a consolidated revision. Necessary user-visible
semantics must not disappear into hidden metadata. A later revision needs a new version; do not
overwrite this first solve or reuse it as a fresh review of changed wording.

**Approved test tasks: 0.** Catalog quality, hard-keyword coverage, wider source/family checks and
dataset scale remain incomplete. E1/E2 stay gated; agreement is not campaign approval.
