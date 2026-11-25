import json
from zipfile import ZipFile

from sn import v2_catalog_review as review


def test_export_keeps_parent_request_and_replaces_one_distractor(tmp_path):
    loaded = review.load()
    drafts, pool, schemas, catalogs, policy, _ = loaded
    _, parents, parent_pool, parent_schemas, parent_cats, _, parent_policy = review.v2_v03.load()
    parent_by_tool = {draft["tool_id"]: draft for draft in parents}
    out = tmp_path / "blind.zip"
    review.export_review(out, loaded)

    with ZipFile(out) as archive:
        assert set(archive.namelist()) == {"tasks.jsonl", "REVIEW_INSTRUCTIONS.md"}
        visible = {
            row["task_id"]: row
            for row in map(json.loads, archive.read("tasks.jsonl").splitlines())
        }
    assert len(visible) == 3
    for draft in drafts:
        target = draft["tool_id"]
        parent = parent_by_tool[target]
        catalog = catalogs[target]
        row = visible[draft["task_id"]]
        assert set(row) == {"task_id", "request", "system_policy", "tools"}
        assert row["task_id"] != parent["task_id"]
        assert row["request"] == parent["request"]
        assert row["system_policy"] == policy == parent_policy
        assert draft["gold_args"] == parent["gold_args"]
        assert len(row["tools"]) == 5
        old_ids = parent_cats[target]["tool_ids"]
        new_ids = catalog["tool_ids"]
        changed = [(a, b) for a, b in zip(old_ids, new_ids) if a != b]
        assert changed == [(catalog["replaced_tool_id"], catalog["candidate_card_id"])]
        for old, new, tool in zip(old_ids, new_ids, row["tools"]):
            assert set(tool) == {"name", "description", "parameters"}
            if old == new:
                assert tool == {
                    "name": parent_pool[old]["tool_name"],
                    "description": parent_pool[old]["description"],
                    "parameters": parent_schemas[old],
                }
            else:
                assert tool["parameters"] == schemas[new]
                assert tool["name"] == pool[new]["tool_name"]


def test_filter_acceptance_does_not_turn_the_competing_tool_into_gold():
    drafts, pool, schemas, catalogs, _, evidence = review.load()
    filters = next(row for row in evidence if row["target_tool_id"] == "T016")
    assert set(filters["catalog_tool_ids_accepting_target_arguments"]) == {"X008", "T016", "T263"}
    assert filters["candidate_witness_also_valid_for_target"]

    responses = [
        {
            "task_id": draft["task_id"],
            "tool": pool["X008" if draft["tool_id"] == "T016" else draft["tool_id"]]["tool_name"],
            "arguments": draft["gold_args"],
        }
        for draft in drafts
    ]
    result = review.v2_v03.previous.compare_review(
        drafts, pool, schemas, catalogs, responses, "independent-reviewer"
    )
    by_id = {row["task_id"]: row for row in result["comparisons"]}
    row = by_id[filters["task_id"]]
    assert row["raw_valid"]
    assert row["review_error_kind"] == "wrong_tool"
    assert not result["approved_for_test"]
