# Blind review of three development catalogs

Use only this ZIP. Follow the visible `system_policy` in each row of `tasks.jsonl`. Solve all
three requests using their supplied five-tool catalogs. Do not open the repository, prior chats,
other packets, task memories or gold answers. Disclose prior task or answer exposure. Do not call
the supplied tools. A local schema validity check may use only schemas in this packet.

Before asking to see the gold, save `answers.jsonl` with one row per task and exactly the keys
`task_id`, `tool` and `arguments`. Also save `REVIEW_NOTES.md`. For each task, list the most
plausible competing tools and describe what each can do with the information in the request.
If another tool could fulfill the request without guessing, give a concrete alternative call.
If the alternative only validates, explain which part of the request it fails to fulfill.
Flag ambiguity or invented conventions and give the reason for your chosen answer.
