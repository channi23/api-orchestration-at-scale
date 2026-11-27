# Fresh review of six draft tool calls

Use only `tasks.jsonl` and the policy included in each row. The two other files are upstream
licence notices. Solve each request with its supplied catalog. Keep external docs, earlier
chats, gold and other packets out of the review. Do not execute a tool or contact an endpoint.
Disclose any prior exposure.

Before asking for gold, save `answers.jsonl` with one row per task and exactly the keys
`task_id`, `tool` and `arguments`. Save `REVIEW_NOTES.md` with plausible alternative tools
or argument shapes and explain what in the visible request distinguishes each. If a case
depends on an unstated convention, flag it. Local schema checks may use the supplied schemas.
