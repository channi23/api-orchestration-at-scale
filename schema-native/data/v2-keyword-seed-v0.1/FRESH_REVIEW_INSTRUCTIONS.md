# Fresh blind review: synthetic schema contracts

Use only this ZIP. Do not open the repository, PR, prior chats/reviews, gold, saved memories or
other design material. Disclose any prior exposure; a fresh context cannot guarantee that public
JSON Schema conventions were absent from pretraining. Do not execute tools, load a model or train.

Solve all 32 tasks in tasks.jsonl using each task's request, system_policy and supplied tool.
Each catalog deliberately contains one tool: this is a review of argument interpretation and
schema-conditioned synthetic requests, not a realistic tool-selection test. Repeated names or
requests are intentional. Solve each task from its own supplied schema without assuming another
task has the same answer. Do not repair the schemas.

Before requesting gold or other context, save:

1. answers.jsonl: exactly one row per task, with task_id, tool and arguments. Choose one answer
   even where uncertain; explain competing readings in notes rather than adding answer variants.
2. REVIEW_NOTES.md: ambiguity or impossibility, assumptions, plausible alternative valid answers,
   schema issues and the distinction between merely validating and fulfilling the request.

You may validate your own answers locally without retrieving remote references. Report any
unavailable validator feature rather than altering the schema. Validator success does not show
semantic correctness. Give a short disclosure of what you accessed and any prior exposure.
Do not approve or freeze test tasks. Stop after preserving your first answers and notes.
