import json

import pytest

from sn import v2_context_smoke as smoke, v2_dev_pilot as pilot


def test_candidate_profile_changes_only_the_context_setting():
    models = smoke.profiles()
    assert models[8192]["request_params"] == models[9216]["request_params"]
    assert models[8192]["server_args"][:2] == ["-c", "8192"]
    assert models[9216]["server_args"][:2] == ["-c", "9216"]
    assert models[8192]["server_args"][2:] == models[9216]["server_args"][2:]


def test_compact_catalog_is_a_lossless_opt_in():
    unit = smoke.development_unit("fixture", "AR-123", 1)
    task = unit["visible"]
    compact, user = pilot.messages(task)
    readable, _ = pilot.messages({**task, "catalog_serialization": "readable"})
    tool_json = compact["content"].split("Available tools (JSON):\n", 1)[1]
    assert json.loads(tool_json) == task["tools"]
    assert len(task["tools"]) == 20
    assert len(compact["content"]) < len(readable["content"])
    assert user["content"] == task["request"]


def test_extended_input_and_reserve_require_the_larger_context():
    models = smoke.profiles()
    template = "fixture"
    unit = smoke.development_unit("extended_long", "AR-387", 1)
    observed = 8389

    def post_for(context, model):
        def post(endpoint, body=None):
            if endpoint == "/props":
                return {"default_generation_settings": {"n_ctx": context},
                        "build_info": model["llama_cpp_commit"],
                        "chat_template": template, "model_path": str(pilot.model_path(model))}
            if endpoint == "/apply-template":
                assert body["messages"] == pilot.messages(unit["visible"])
                return {"prompt": "fixture"}
            assert endpoint == "/tokenize"
            return {"tokens": [1] * observed}
        return post

    for context, model in models.items():
        plan = {"units": [unit], "profile": model, "config": {"cache_prompt": False},
                "template_sha256": pilot.provenance.digest(template),
                "expected_prompt_tokens": {"extended_long": observed}}
        if context == 8192:
            with pytest.raises(RuntimeError, match="Token count or context check failed"):
                pilot.token_preflight(plan, post_for(context, model))
        else:
            assert pilot.token_preflight(plan, post_for(context, model))["prompt_tokens"] == {
                "extended_long": observed
            }
            plan["expected_prompt_tokens"]["extended_long"] += 1
            with pytest.raises(RuntimeError, match="locked offline counts"):
                pilot.token_preflight(plan, post_for(context, model))
