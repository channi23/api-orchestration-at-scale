import json

import pytest

from sn import v2_dev_pilot as pilot
from sn import v2_keyword_repairs as repairs


def call(value):
    return json.dumps({"tool": "save", "arguments": {"count": value}})


def fixture():
    task = {"request": "Save three.", "system_policy": "Return one call.", "tools": [
        {"name": "save", "description": "Save a number.", "parameters": {
            "type": "object", "required": ["count"], "properties": {"count": {"type": "integer"}}
        }},
    ]}
    units = [{"task_id": key, "visible": task, "gold": {"tool": "save", "arguments": {"count": 3}}}
             for key in ("invalid", "valid_wrong", "correct")]
    baseline = {u["task_id"]: {"content": call(value), "finish_reason": "stop",
                              "usage": {"prompt_tokens": 20, "completion_tokens": 10}}
                for u, value in zip(units, ("3", 4, 3), strict=True)}
    return units, baseline


def test_router_repairs_only_raw_schema_violations_and_sees_no_gold():
    units, baseline = fixture()
    task = units[0]["visible"]
    assert repairs.validation_feedback(task, call("3"), "stop") == "Arguments at $.count: '3' is not of type 'integer'"
    assert repairs.validation_feedback(task, call("3"), "length") is None
    assert repairs.validation_feedback(task, '{"tool":', "stop") is None
    assert repairs.validation_feedback(task, call(4), "stop") is None
    cases, requests = repairs.schedule(units, baseline)
    assert [c["retry"] for c in cases] == ["invalid|retry", None, None]
    assert len(requests) == 4
    repair = pilot.messages(requests[1]["visible"])
    assert repair[:2] == pilot.messages(task)
    assert [m["role"] for m in repair[2:]] == ["assistant", "user"]
    assert repair[2]["content"] == baseline["invalid"]["content"]
    assert "not of type 'integer'" in repair[3]["content"]
    checklist = requests[0]["visible"]
    assert checklist["tools"] == task["tools"] and checklist["request"] == task["request"]
    assert checklist["system_policy"] == task["system_policy"] + "\n\n" + repairs.CHECKLIST
    assert all("gold" not in r["visible"] for r in requests)
    changed_gold = [{**u, "gold": {"tool": "do_not_use", "arguments": {"count": 999}}} for u in units]
    assert repairs.schedule(changed_gold, baseline)[1] == requests


def test_report_counts_reuse_regressions_and_all_retry_tokens():
    units, baseline = fixture()
    cases, requests = repairs.schedule(units, baseline)
    plan = {"cases": cases, "units": requests}
    responses = [{"task_id": u["task_id"], "content": call(value), "finish_reason": "stop",
                  "usage": {"prompt_tokens": 30, "completion_tokens": 12}}
                 for u, value in zip(requests, (3, 3, 3, "3"), strict=True)]
    report = repairs.report(plan, responses)
    assert report["live_requests"] == 4
    assert report["live_token_usage"] == {"prompt_tokens": 120, "completion_tokens": 48}
    assert report["arms"]["baseline"]["outcomes"]["correct"] == 1
    assert report["arms"]["validator_retry"] == {
        "logical_requests": 4, "token_usage": {"prompt_tokens": 90, "completion_tokens": 42},
        "outcomes": {"correct": 2, "valid_wrong_arguments": 1}, "improved": 1, "regressed": 0,
    }
    assert report["arms"]["checklist"]["improved"] == 2
    assert report["arms"]["checklist"]["regressed"] == 1
    with pytest.raises(ValueError, match="frozen order"):
        repairs.report(plan, responses[:-1])
