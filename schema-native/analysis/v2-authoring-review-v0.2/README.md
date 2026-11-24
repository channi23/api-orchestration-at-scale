# Fresh-context v0.2 review evidence

The uploaded answers_1.jsonl and REVIEW_NOTES_1.md are archived here without byte changes. The
reviewer reports saving them before seeing gold; receipt.json preserves that disclosure and hashes.

- `answers.jsonl`, `REVIEW_NOTES.md`: received first solve and notes.
- `comparison.json`: existing checker output; 32/32 correct under the declared draft comparison.
- `gold.jsonl`: author answers, ready for disclosure after preserving the first solve.
- `task-comparison.jsonl`: side-by-side values and eight reviewer-assumption flags. No approval.
- `receipt.json`: input hashes, context disclosure, reviewer-rated catalog categories and unresolved gate.
- [RESPONSE.md](RESPONSE.md): author response, schema clarifications and remaining adjudication.

Reproduce from schema-native/ into a new output path:

```bash
.venv/bin/python -m sn.v2_revision check-review \
  --responses analysis/v2-authoring-review-v0.2/answers.jsonl \
  --reviewer claude-fresh-session-self-reported-blind-v0.2 \
  --out /tmp/v0.2-fresh-review-reproduced.json
cmp /tmp/v0.2-fresh-review-reproduced.json analysis/v2-authoring-review-v0.2/comparison.json
.venv/bin/python -m sn.v2_revision audit --check
.venv/bin/python -m sn.v2_authoring audit --check
.venv/bin/python -m pytest -q tests/test_v2_revision.py tests/test_v2_authoring.py
```

Do not call the author/reviewer agreement a Qwen benchmark result, a hardness test, or proof of
unique answers. The reviewer has seen only the supplied packet so far according to its disclosure;
after receiving gold it is no longer blind to this batch. Dataset approval and E1/E2 remain gated.
