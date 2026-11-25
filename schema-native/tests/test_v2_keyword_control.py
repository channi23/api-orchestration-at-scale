import json

from sn import v2_dev_pilot as pilot, v2_keyword_control as control


def test_materialized_pairs_have_a_single_hidden_message_and_match_the_audit():
    plan = control.task_plan()
    units = {row["task_id"]: row for row in plan["units"]}
    assert len(units) == plan["config"]["generation_cap"] == 48
    assert control.audit()["hidden_max_exact_members"] == 18
    assert control.audit()["hidden_max_pair_correct"] == 2
    for pair in plan["pairs"]:
        hidden = units[pair["hidden"]]["visible"]
        assert "parameters" not in hidden["tools"][0]
        for task_id in pair["visible"]:
            visible = units[task_id]["visible"]
            schema, = [tool["parameters"] for tool in visible["tools"]]
            assert hidden["request"] == visible["request"]
            assert hidden["system_policy"] == visible["system_policy"]
            assert hidden["tools"][0]["name"] == visible["tools"][0]["name"]
            assert "gold" not in visible
            assert schema


def test_fake_run_scores_shared_hidden_response_against_both_distinct_schemas(tmp_path):
    plan = control.task_plan()
    plan["profile"] = {"request_params": {}}
    units = {row["task_id"]: row for row in plan["units"]}
    gold = {}
    for pair in plan["pairs"]:
        for task_id in pair["visible"]:
            gold[task_id] = units[task_id]["gold"]
        gold[pair["hidden"]] = gold[pair["visible"][0]]
    order = iter(plan["units"])

    def post(path, payload):
        assert path == "/v1/chat/completions"
        unit = next(order)
        assert payload["messages"] == pilot.messages(unit["visible"])
        assert set(payload) == {"cache_prompt", "messages"}
        return {"choices": [{"message": {"content": json.dumps(gold[unit["task_id"]])},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10}}

    report = pilot.generate(plan, tmp_path, post, lambda: None, cooldown=lambda _: None,
                            reporter=control.report)
    assert report["request_count"] == 48
    assert report["arms"]["visible"]["all"]["outcomes"] == {"correct": 32}
    assert report["arms"]["visible"]["all"]["pair_correct"] == 16
    assert report["arms"]["hidden"]["all"]["outcomes"]["correct"] == 18
    assert report["arms"]["hidden"]["all"]["pair_correct"] == 2
    assert sum(p["visible_same_answer"] is True for p in report["pairs"]) == 2
    assert len((tmp_path / "request-budget.jsonl").read_text().splitlines()) == 48
