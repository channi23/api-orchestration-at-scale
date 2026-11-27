# First v2 blind-review evidence

This directory preserves the first external review of the 32 provisional v0.1 API tasks. It does
not change the original drafts, their gold or the frozen E0/E0b experiments.

- `answers.jsonl`, `REVIEW_NOTES.md`: received files, byte-identical to the uploads.
- `receipt.json`: hashes and provenance; blind independence is self-reported, not proven by a file.
- `comparison.json`: output of the existing sn.v2_authoring checker, with 32/32 agreement.
- `gold.jsonl`: author answers in the reviewer's task_id/tool/arguments format, now ready for disclosure.
- `task-comparison.jsonl`: each author/reviewer answer side by side, with unresolved review status.
- [RESPONSE.md](RESPONSE.md): accepted findings, schema clarifications and proposed edits. No task is approved.

Reproduce the answer comparison from schema-native/ into a **new** output path:

```bash
.venv/bin/python -m sn.v2_authoring check-review \
  --responses analysis/v2-authoring-review-v0.1/answers.jsonl \
  --reviewer claude-opus-5.5-self-reported-blind \
  --out /tmp/v2-review-comparison-reproduced.json
cmp /tmp/v2-review-comparison-reproduced.json analysis/v2-authoring-review-v0.1/comparison.json
.venv/bin/python -m sn.v2_authoring audit --check
.venv/bin/python -m pytest -q tests/test_v2_authoring.py
```

The comparison command refuses an existing output path. Agreement is not a Qwen benchmark score,
proof of hard-schema coverage or approval of an ambiguous request. The reviewer should now
compare against gold, but any revised tasks require a new version and another semantic check.
