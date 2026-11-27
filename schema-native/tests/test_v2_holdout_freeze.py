import json

import pytest

from sn import v2_holdout_freeze as freeze, v2_holdout_score as scoring


def test_nested_catalog_order_is_part_of_the_frozen_contract():
    small = {"task_id": "fixture", "request": "Example.", "system_policy": "Return a call.",
             "tools": [{"name": str(i)} for i in range(5)]}
    large = {**small, "tools": [{"name": str(i)} for i in range(20)]}
    freeze.validate_intent([{5: small, 20: large}], "api")
    with pytest.raises(ValueError, match="nested, ordered"):
        freeze.validate_intent([{5: {**small, "tools": list(reversed(small["tools"]))}, 20: large}], "api")
    with pytest.raises(ValueError, match="identical request"):
        freeze.validate_intent([{1: small}, {1: {**small, "request": "Different."}}], "assertion")


def test_write_checks_exact_bytes_and_refuses_overwrite(tmp_path):
    out = tmp_path / "freeze"
    rows = {"inference/requests.jsonl": b"{}\n", "scoring/expected.jsonl": b"{}\n"}
    freeze.write(out, rows)
    freeze.write(out, rows, verify=True)
    with pytest.raises(FileExistsError):
        freeze.write(out, rows)
    (out / "scoring/expected.jsonl").write_bytes(b'{"changed":true}\n')
    with pytest.raises(ValueError, match="Frozen bytes changed"):
        freeze.write(out, rows, verify=True)


def test_scoring_keeps_validity_correctness_and_omissions_separate():
    schema = {"type": "object", "properties": {
        "page": {"type": "integer", "default": 1}, "limit": {"type": "integer"}
    }, "additionalProperties": False}
    tools = [{"name": name, "parameters": schema} for name in ("list_records", "find_records")]
    variants = [
        {"tool": "list_records", "arguments": {}},
        {"tool": "find_records", "arguments": {"page": 1, "limit": 5}},
        {"tool": "list_records", "arguments": {"page": 1, "limit": 5}},
    ]
    tasks = [{"request_id": str(i), "tools": tools} for i in range(3)]
    answers = [{"request_id": str(i), "tool": "list_records", "arguments": {"page": 1, "limit": 5},
                "catalog_size": 2, "track": "api", "intent_key": str(i)} for i in range(3)]
    results = [{"request_id": str(i), "content": json.dumps(row), "finish_reason": "stop"}
               for i, row in enumerate(variants)]
    result = scoring.report(tasks, answers, results)
    totals = result["by_catalog_size"]["2"]
    assert totals["right_tool"] == 2
    assert totals["schema_valid_for_emitted_tool"] == 3
    assert totals["exact_calls"] == 1
    assert result["tasks"][0]["omitted_expected_keys"] == ["limit", "page"]
    assert result["tasks"][0]["omitted_keys_matching_schema_default"] == ["page"]
    with pytest.raises(ValueError, match="complete, unique responses"):
        scoring.report(tasks, answers, list(reversed(results)))
