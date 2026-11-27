from copy import deepcopy
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from sn import v2_holdout_batch as batch


PAIR = {
    "intent_id": "fixture", "family_id": "fixture",
    "kind": "validity_separable", "tool": "record_fixture",
    "tool_description": "Record one fixture.", "request": "Record the allowed label.",
    "schema": {"$schema": batch.DIALECT, "type": "object", "required": ["label"],
               "properties": {"label": {"const": "before"}}, "additionalProperties": False},
    "edit_path": "/properties/label/const", "replacement": "after",
    "arguments": [{"label": "before"}, {"label": "after"}],
    "negatives": [{"label": 1}, {"label": 1}],
}


def test_pair_cross_validation_and_distinct_visible_ids():
    tasks, answers, matrix = batch.pair_rows(PAIR)
    assert matrix == [True, False, False, True]
    assert len({row["task_id"] for row in tasks}) == 2
    assert [row["task_id"] for row in tasks] == [row["task_id"] for row in answers]
    assert tasks[0]["request"] == tasks[1]["request"]
    assert all(set(row) == {"task_id", "request", "system_policy", "tools"} for row in tasks)
    wrong = {**PAIR, "negatives": [{"label": "before"}, {"label": 1}]}
    with pytest.raises(ValueError, match="negative witness validates"):
        batch.pair_rows(wrong)
    with pytest.raises(ValueError, match="Unexpected cross-validity"):
        batch.pair_rows({**PAIR, "kind": "asymmetric_edit"})


def test_grounding_requires_a_single_annotation_edit():
    pair = deepcopy(PAIR)
    pair["kind"] = "description_grounding"
    with pytest.raises(ValueError, match="exclusively"):
        batch.pair_rows(pair)
    pair["schema"]["properties"]["label"] = {"type": "string", "description": "Before."}
    pair["edit_path"] = "/properties/label/description"
    pair["replacement"] = "After."
    pair["negatives"] = [{"label": 1}, {"label": 1}]
    tasks, _, matrix = batch.pair_rows(pair)
    assert matrix == [True, True, True, True]
    schemas = [row["tools"][0]["parameters"] for row in tasks]
    for schema in schemas:
        del schema["properties"]["label"]["description"]
    assert schemas[0] == schemas[1]


def test_export_is_repeatable_and_keeps_gold_and_smaller_catalog_private(tmp_path):
    tasks, answers, _ = batch.pair_rows(PAIR)
    data = {"summary": {"approved_test_intents": 0}, "sources": []}
    first, second = tmp_path / "first", tmp_path / "second"
    assert batch.emit(first, tasks, tasks, answers, {"LICENSE": b"licence"}, data) == batch.emit(
        second, tasks, tasks, answers, {"LICENSE": b"licence"}, data
    )
    path = Path("review", f"{batch.RUN}-blind-review.zip")
    assert (first / path).read_bytes() == (second / path).read_bytes()
    with ZipFile(first / path) as archive:
        assert set(archive.namelist()) == {"tasks.jsonl", "REVIEW_INSTRUCTIONS.md", "LICENSE"}
        rows = [json.loads(line) for line in archive.read("tasks.jsonl").splitlines()]
        assert all("arguments" not in row for row in rows)
    assert (first / "sealed/gold.jsonl").exists()
    assert (first / "sealed/tasks.c5.jsonl").exists()
    with pytest.raises(FileExistsError):
        batch.emit(first, tasks, tasks, answers, {}, data)


def test_writing_revision_requires_both_variants_to_keep_the_same_request():
    from sn import v2_holdout_batch_revision as revision

    tasks, answers, matrix = batch.pair_rows(PAIR)
    rows = {row["task_id"]: row for row in tasks}
    gold = {row["task_id"]: row for row in answers}
    group = {"task_ids": list(rows), "cross_validity": matrix}
    edits = [{"parent_task_id": key, "request": "Record the label that this schema permits.",
              "arguments": answer["arguments"], "reason": "Clarify the request."}
             for key, answer in gold.items()]
    with pytest.raises(ValueError, match="must share one request"):
        revision.replace(rows, rows, gold, edits[:1], [group])
    changed, small, expected, _ = revision.replace(rows, rows, gold, edits, [group])
    assert changed == small
    assert [row["tools"] for row in changed] == [row["tools"] for row in tasks]
    assert [row["arguments"] for row in expected] == [row["arguments"] for row in answers]
    assert {row["task_id"] for row in changed}.isdisjoint(rows)


def test_budget_reads_legacy_five_tool_packet_without_a_second_view(tmp_path):
    from hashlib import sha256
    from sn import v2_holdout_budget as budget

    review = tmp_path / "review"
    sealed = tmp_path / "sealed"
    review.mkdir()
    sealed.mkdir()
    record = {"task_id": "fixture", "tools": [{"name": str(i)} for i in range(5)]}
    packet = review / "legacy.zip"
    with ZipFile(packet, "w") as archive:
        archive.writestr("tasks.jsonl", json.dumps(record) + "\n")
    manifest = {"review_zip_sha256": sha256(packet.read_bytes()).hexdigest()}
    (sealed / "manifest.json").write_text(json.dumps(manifest))
    rows, metadata = budget.payloads(tmp_path)
    assert rows == {5: {"fixture": record}, 20: {}}
    assert metadata == manifest


def test_review_comparison_accepts_disjoint_parts_and_rejects_repeat_answers(tmp_path):
    from sn import v2_holdout_review as reviewer

    tasks, expected, _ = batch.pair_rows(PAIR)
    bundle = tmp_path / "bundle"
    batch.emit(bundle, tasks, tasks, expected, {}, {"summary": {"approved_test_intents": 0}})
    first, second, notes = (tmp_path / name for name in ("first.jsonl", "second.jsonl", "notes.md"))
    first.write_text(json.dumps(expected[0]) + "\n")
    second.write_text(json.dumps({**expected[1], "arguments": {"label": "wrong"}}) + "\n")
    notes.write_text("Blind review notes.\n")
    report = reviewer.compare(bundle, [first, second], [notes])
    assert report["rows"] == report["tool_matches"] == 2
    assert report["valid_arguments"] == report["exact_calls"] == 1
    assert report["approved_test_intents"] == 0
    with pytest.raises(ValueError, match="repeated task IDs"):
        reviewer.compare(bundle, [first, first], [notes])
