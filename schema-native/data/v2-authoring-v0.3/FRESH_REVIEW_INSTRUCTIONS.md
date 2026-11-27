# Fresh v0.3 wording review

Use only this ZIP: tasks.jsonl, SYSTEM_POLICY.txt and these instructions. Read the policy, then solve
all 32 tasks without opening the PR, source, parent packets, gold, earlier reviews or task memories.
Do not execute tools, load or query a model, or train anything. Save a strict answers.jsonl with
only task_id, tool and arguments for every task, plus REVIEW_NOTES.md, before requesting gold.

Disclose earlier task/gold exposure. A fresh session without task history is not proof of different
model weights or absence from pretraining; an already exposed reviewer must call its review non-blind.

Check whether the request determines values, name boundaries, literal strings and documented field
roles without invented conventions. Flag alternative readings rather than silently repair requests.
Judge each catalog's competing tools independently. A missing enum does not make every string a
correct answer; follow the visible exact-string policy. Raw-schema validity alone is not correctness.

The catalogs are deliberately held fixed from the preceding version while wording is revised.
Some catalog and source-documentation gaps remain. This is a provisional review packet, not a hard
keyword benchmark or an approved dataset. Agreement cannot automatically approve a task.
