# Fresh semantic review

Solve these 32 provisional API tasks using only tasks.jsonl and the supplied SYSTEM_POLICY.txt.
Do not execute the tools, run model experiments or train anything. Each record supplies five
candidate tools and the shared policy the eventual model would receive. Read that policy before
answering, including the omission of unrequested optional/default fields.

Return answers.jsonl with exactly one strict JSON object per task and only task_id, tool and arguments.
Return separate review notes for ambiguous requests, missing details, multiple equally good tools,
undocumented mappings, weak schema guarantees, unrealistic wording and weak distractors. An answer
that merely validates need not satisfy the request. Do not invent missing values to force an answer.

Assess whether each catalog offers at least two plausible near-miss tools. Domain-adjacent tools
need not be near misses. There are known unresolved catalog gaps; you are not asked to endorse them.

Save your first solve and notes before opening author gold, revision source, parent tasks, the PR
or any earlier review/adjudication. Disclose prior access. The original reviewer who has seen the
gold cannot call another review in the same context blind. A fresh reviewer or isolated context
must receive only this packet, without gold-bearing history or retrieved memories. A fresh context
does not prove absence from pretraining or guarantee independence by itself.

These are draft API tasks, not a complete hard-keyword stress set or an approved test dataset.
No task becomes approved automatically through agreement, validation or a review script.
