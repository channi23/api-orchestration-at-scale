import json

import pytest

from sn import v2_dev_pilot as pilot


def unit(task_id="first"):
    schema = {"type": "object", "required": ["count"], "properties": {"count": {"type": "integer"}}}
    return {"task_id": task_id, "visible": {
        "task_id": task_id, "request": "Find six items.", "system_policy": "Return a JSON call.",
        "tools": [{"name": name, "description": name, "parameters": schema} for name in ("find", "other")],
    }, "gold": {"task_id": task_id, "tool": "find", "arguments": {"count": 6}}}


def plan():
    return {"units": [unit(), unit("second")], "config": {
        "generation_cap": 2, "cache_prompt": True, "request_cooldown_seconds": 0,
    }, "profile": {"request_params": {"temperature": 0, "max_tokens": 512,
                                     "chat_template_kwargs": {"enable_thinking": False}}}}


def test_schema_valid_wrong_tool_is_not_correct_and_duplicate_keys_are_rejected():
    selected = unit()
    different_tool = pilot.score(selected, '{"tool":"other","arguments":{"count":6}}', "stop")
    assert different_tool == {"outcome": "wrong_tool", "tool_matches": False, "known_tool": True, "schema_valid": True}
    assert pilot.score(selected, '{"tool":"find","tool":"find","arguments":{"count":6}}', "stop") == {
        "outcome": "malformed"
    }
    assert pilot.score(selected, '{"tool":"find","arguments":{"count":8}}', "stop")["outcome"] == "valid_wrong_arguments"
    assert pilot.score(selected, '{"tool":"find","arguments":{"count":true}}', "stop")["outcome"] == "schema_invalid_arguments"
    assert pilot.score(selected, '{"tool":"find","arguments":{"count":6}}', "length") == {"outcome": "truncated"}


def test_mocked_routing_preserves_order_and_sends_only_visible_inputs(tmp_path):
    calls = []

    def post(url, body):
        assert url == "/v1/chat/completions"
        assert set(body) == {"temperature", "max_tokens", "chat_template_kwargs", "cache_prompt", "messages"}
        assert "gold" not in json.dumps(body)
        calls.append(body)
        return completion()

    result = pilot.generate(plan(), tmp_path, post, lambda: None)
    charged = [json.loads(line)["key"] for line in (tmp_path / "request-budget.jsonl").read_text().splitlines()]
    assert charged == ["first", "second"]
    assert len(calls) == result["request_count"] == 2
    assert result["outcomes"] == {"correct": 2}
    assert result["total_usage"] == {"prompt_tokens": 32, "completion_tokens": 12}


def completion():
    return {"choices": [{"message": {"content": '{"tool":"find","arguments":{"count":6}}'},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 16, "completion_tokens": 6}}


def test_failed_send_consumes_budget_and_preserves_completed_result(tmp_path):
    sent = 0

    def post(_url, _body):
        nonlocal sent
        sent += 1
        if sent == 2:
            raise RuntimeError("connection failure")
        return completion()

    with pytest.raises(RuntimeError, match="connection failure"):
        pilot.generate(plan(), tmp_path, post, lambda: None)
    assert sent == 2
    assert len((tmp_path / "request-budget.jsonl").read_text().splitlines()) == 2
    assert len((tmp_path / "results.jsonl").read_text().splitlines()) == 1
    with pytest.raises(ValueError, match="already reserved"):
        pilot.generate(plan(), tmp_path, post, lambda: None)
    assert sent == 2


def test_online_token_preflight_looks_at_template_and_rejects_overflow():
    prepared = plan()
    model = prepared["profile"]
    model.update({"server_args": ["-c", "8192"], "gguf_file": "fixture.gguf", "llama_cpp_commit": "abc123499"})
    prepared["template_sha256"] = pilot.provenance.digest("template fixture")
    calls = []

    def post(path, body=None):
        calls.append(path)
        if path == "/props":
            return {"default_generation_settings": {"n_ctx": 8192}, "build_info": "abc1234",
                    "model_path": str(pilot.model_path(model)), "chat_template": "template fixture"}
        if path == "/apply-template":
            assert body["chat_template_kwargs"] == {"enable_thinking": False}
            return {"prompt": "rendered"}
        assert path == "/tokenize" and body["content"] == "rendered"
        return {"tokens": [1] * 7681}

    with pytest.raises(RuntimeError, match="context check"):
        pilot.token_preflight(prepared, post)
    assert calls == ["/props", "/apply-template", "/tokenize"]
