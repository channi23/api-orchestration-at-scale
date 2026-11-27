import json

from sn import v2_exploratory_audit as audit


def test_nested_differences_use_frozen_equality_and_keep_arrays_as_values():
    expected = {"options": {"limit": 2, "range": {"start": 1}, "a.b": True},
                "order": ["one", "two"]}
    actual = {"options": {"limit": 2.0, "a.b": 1, "sort": "asc"}, "order": ["two", "one"]}

    assert set(audit.differences(expected, actual)) == {
        ("missing", ("options", "range")),
        ("extra", ("options", "sort")),
        ("changed", ("options", "a.b")),
        ("changed", ("order",)),
    }


def test_repeated_catalog_error_counts_one_intent():
    results = audit.summarize_changes([
        ({"intent_key": "paired", "catalog_size": 5}, [("missing", ("limit",))]),
        ({"intent_key": "paired", "catalog_size": 20}, [("missing", ("limit",)), ("extra", ("sort",))]),
    ])
    assert results["calls"] == 2
    assert results["intents"] == 1
    assert results["intents_by_change"] == {"missing": 1, "extra": 1}
    assert results["call_signatures"] == {"missing": 1, "missing+extra": 1}
    assert results["api_intents_with_same_change_kind_at_both_sizes"] == {"missing": 1}


def test_summary_reports_structure_and_defaults_without_task_content():
    schema = {"type": "object", "properties": {"optional": {"type": "integer", "default": 3}}}
    visible = {"tools": [{"name": "private_tool", "parameters": schema}]}
    gold = {"intent_key": "private_id", "catalog_size": 5, "tool": "private_tool", "arguments": {}}
    response = {"content": '{"tool":"private_tool","arguments":{"optional":3}}'}
    score = {"tasks": [{"outcome": "valid_wrong_arguments", "schema_valid": True}]}

    result = audit.summarize([visible], [gold], [response], score)

    assert result["argument_errors"]["valid_wrong_arguments"]["call_signatures"] == {"extra": 1}
    assert result["valid_wrong_argument_calls_with_extra_matching_direct_default"] == 1
    for private_text in ("private_tool", "private_id", "optional"):
        assert private_text not in json.dumps(result)
