import json

import pytest

from sn import resources, v2_exploratory_run as run


def rows(count):
    return [{"request_id": str(i), "expected_prompt_tokens": 3,
             "payload": {"messages": [], "max_tokens": 512, "chat_template_kwargs": {}}}
            for i in range(count)]


def config(count):
    return {"generation_cap": count, "metadata_cap": 12, "request_cooldown_seconds": 0}


def test_resume_twice_does_not_repeat_completed_requests(tmp_path, monkeypatch):
    sent = []

    def segment(directory, current, config, manifest, profile, full, pending, budget, growth):
        def post(path, body, *, key):
            budget.reserve("benchmark", key)
            sent.append(key)
            return {"choices": [{"message": {"content": "{}"}, "finish_reason": "length"}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 512}}

        run.generate(directory, pending[:1], post, lambda: None, 0)
        if len(pending) > 1:
            raise resources.ResourceWarning("test guard")

    monkeypatch.setattr(run, "segment_run", segment)
    request_rows = rows(3)
    for _ in range(2):
        with pytest.raises(resources.ResourceWarning):
            run.execute(tmp_path, config(3), {}, {}, request_rows, {})
    run.execute(tmp_path, config(3), {}, {}, request_rows, {})
    run.execute(tmp_path, config(3), {}, {}, request_rows, {})
    assert sent == ["0", "1", "2"]
    assert (tmp_path / "COMPLETED.json").exists()
    assert len(list(tmp_path.glob("segment-*/STOPPED.json"))) == 2


def test_uncertain_dispatch_is_charged_and_blocks_resume(tmp_path, monkeypatch):
    def segment(directory, current, config, manifest, profile, full, pending, budget, growth):
        budget.reserve("benchmark", pending[0]["request_id"])
        raise resources.ResourceWarning("warning during HTTP")

    monkeypatch.setattr(run, "segment_run", segment)
    with pytest.raises(resources.ResourceWarning):
        run.execute(tmp_path, config(1), {}, {}, rows(1), {})
    stopped = json.loads((tmp_path / "segment-001/STOPPED.json").read_bytes())
    assert not stopped["resumable"]
    assert stopped["saved_results"] == 0
    assert run.records(tmp_path / "request-budget.jsonl") == [{"key": "0", "category": "benchmark"}]
    with pytest.raises(RuntimeError, match="final stop"):
        run.execute(tmp_path, config(1), {}, {}, rows(1), {})


def test_prompt_checks_reuse_only_verified_lengths(tmp_path):
    calls = []

    def post(path, body):
        calls.append(path)
        return {"prompt": "rendered"} if path == "/apply-template" else {"tokens": [1, 2, 3]}

    run.token_preflight(tmp_path, rows(1), post)
    run.token_preflight(tmp_path, rows(2), post)
    run.token_preflight(tmp_path, rows(2), post)
    assert calls == ["/apply-template", "/tokenize"] * 2
    assert len(run.records(tmp_path / "prompt-counts.jsonl")) == 2


def test_prompt_length_mismatch_is_not_cached(tmp_path):
    def post(path, body):
        return {"prompt": "rendered"} if path == "/apply-template" else {"tokens": [1, 2]}

    with pytest.raises(RuntimeError, match="frozen prompt length"):
        run.token_preflight(tmp_path, rows(1), post)
    assert not (tmp_path / "prompt-counts.jsonl").exists()


def test_wrong_usage_is_not_saved(tmp_path):
    def post(path, body, *, key):
        return {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1}}

    with pytest.raises(RuntimeError, match="token usage"):
        run.generate(tmp_path, rows(1), post, lambda: None, 0)
    assert not (tmp_path / "results.jsonl").exists()
