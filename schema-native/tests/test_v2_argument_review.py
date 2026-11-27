import json

import pytest

from sn import v2_argument_review as review


def example():
    selected = {
        "name": "selected",
        "description": "Return the records.",
        "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}},
                       "additionalProperties": False},
    }
    visible = {"request": "Return at most five records.",
               "tools": [selected, {"name": "other", "description": "OTHER_TOOL_MARKER",
                                    "parameters": {"type": "object"}}],
               "gold": "GOLD_MARKER"}
    first = {"content": '{"tool":"selected","arguments":{}}', "finish_reason": "stop",
             "evaluation": "EVAL_MARKER"}
    return visible, first


def test_prompt_uses_only_first_arguments_and_selected_tool():
    visible, first = example()
    result = review.review_task(visible, first)
    assert result["tools"] == visible["tools"][:1]
    assert visible["request"] in result["request"]
    assert result["request"].endswith("{}")
    assert not any(marker in json.dumps(result) for marker in ("OTHER_TOOL_MARKER", "GOLD_MARKER", "EVAL_MARKER"))


def test_review_can_fix_missing_arguments_but_cannot_switch_tool():
    visible, first = example()
    unit = {"visible": visible, "gold": {"tool": "selected", "arguments": {"limit": 5}}}
    assert review.score_review(unit, first, {"content": '{"limit":5}', "finish_reason": "stop"})["outcome"] == "correct"
    switched = '{"tool":"other","arguments":{"limit":5}}'
    assert review.score_review(unit, first, {"content": switched, "finish_reason": "stop"})["outcome"] == "schema_invalid_arguments"
    unit["gold"]["tool"] = "other"
    assert review.score_review(unit, first, {"content": '{"limit":5}', "finish_reason": "stop"})["outcome"] == "wrong_tool"


@pytest.mark.parametrize(("content", "finish", "outcome"), [
    ('{"limit":5,"limit":5}', "stop", "malformed"),
    ('[5]', "stop", "malformed"),
    ('{"limit":5}', "length", "truncated"),
])
def test_rejects_non_contract_review_output(content, finish, outcome):
    _, first = example()
    assert review.score_review({}, first, {"content": content, "finish_reason": finish})["outcome"] == outcome
