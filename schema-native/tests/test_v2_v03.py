"""Parent preservation, visible exact-string policy and bounded wording scope."""
import copy
import json

import pytest

from sn import v2_v03 as v


@pytest.fixture(scope="module")
def bundle():
    return v.load()


def test_gold_unchanged_and_only_ten_requests_change(bundle):
    old, clean, pool, schemas, _, _, _ = bundle
    before = {d["tool_id"]: d for d in old}
    assert sum(d["request"] != before[d["tool_id"]]["request"] for d in clean) == 10
    for d in clean:
        assert v.BASE.argument_equal(d["gold_args"], before[d["tool_id"]]["gold_args"])
        assert v.BASE.validator(schemas[d["tool_id"]]).is_valid(d["gold_args"])
        assert not v.BASE.build_tasks.leakage(d["request"], pool[d["tool_id"]], schemas[d["tool_id"]])


def test_new_ids_are_disjoint_and_catalogs_remain_identical(bundle):
    old, clean, _, _, cats, counts, _ = bundle
    previous = {r["tool_id"]: r for r in v.BASE.read_rows(v.previous.DATA / "catalogs.jsonl")}
    assert len({d["task_id"] for d in clean}) == 32
    assert {d["task_id"] for d in clean}.isdisjoint({d["task_id"] for d in old})
    for d in clean:
        assert cats[d["tool_id"]]["tool_ids"] == previous[d["tool_id"]]["tool_ids"]
        assert cats[d["tool_id"]]["task_id"] == d["task_id"]
    assert max(counts.values()) == 3


def test_supported_ambiguity_repairs_do_not_invent_selector_semantics(bundle):
    _, clean, pool, schemas, _, _, _ = bundle
    by = {d["tool_id"]: d for d in clean}
    assert 'Set the lamp\'s friendly name to "Reading nook"' in by["T018"]["request"]
    assert pool["T018"]["description"] == "Set the name, brightness level, and on/off state of a smart light."
    assert schemas["T018"]["definitions"]["core.brightlight"]["properties"]["name"]["description"].startswith("Friendly device name")
    assert "frame index 3" in by["T122"]["request"]
    assert "regular expressions exactly as written" in by["T016"]["request"]
    assert "literal patterns" not in by["T016"]["request"]
    assert '"1 medium apple"' in by["T131"]["request"]
    assert "local time" in by["T033"]["request"]
    assert by["T011"]["request"].count("each") == 2


def test_wording_source_cannot_override_gold(tmp_path, monkeypatch):
    rows = v.BASE.read_rows(v.DATA / "wording.jsonl")
    rows[0]["gold_args"] = {"changed": True}
    (tmp_path / "wording.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(v, "DATA", tmp_path)
    with pytest.raises(ValueError, match="cannot change gold"):
        v.load()


def test_visible_alias_policy_and_blind_whitelist(bundle):
    _, clean, pool, schemas, cats, _, policy = bundle
    packet = v.previous.packet(clean, pool, schemas, cats, policy)
    assert "including case" in policy
    assert "Do not substitute a synonym" in policy
    assert all(set(p) == {"task_id", "request", "system_policy", "tools"} for p in packet)
    assert all(p["system_policy"] == policy for p in packet)
    changed = copy.deepcopy(clean)
    for d in changed:
        d["gold_args"] = {"PRIVATE_GOLD": "secret"}
        d["parent_task_id"] = "PRIVATE_PARENT_ID"
    assert v.previous.packet(changed, pool, schemas, cats, policy) == packet


def test_case_alias_is_not_silently_accepted(bundle):
    _, clean, pool, schemas, _, _, _ = bundle
    d = next(d for d in clean if d["tool_id"] == "T056")
    args = dict(d["gold_args"], method="Email")
    result = v.previous.diagnose({"tool": pool["T056"]["tool_name"], "arguments": args},
                                 pool["T056"]["tool_name"], d["gold_args"], schemas["T056"])
    assert result["raw_valid"] is True
    assert result["review_error_kind"] == "valid_wrong_value"


def test_schema_position_scan_ignores_annotation_data():
    s = {"type": "object", "default": {"description": "SECRET_CAPTION"},
         "properties": {"description": {"type": "string", "description": "real field"}}}
    texts = list(v.source_texts(s))
    assert ("/properties/description", "description") in texts
    assert ("/properties/description/description", "real field") in texts
    assert all("SECRET_CAPTION" not in value for _, value in texts)


def test_pool_probe_cannot_promote_candidates_or_change_catalogs(bundle):
    _, _, pool, schemas, _, _, _ = bundle
    result = v.source_probe(pool, schemas)
    assert result["searched_pool_size"] == 300
    assert result["catalogs_changed_from_probe"] is False
    for group in result["searches"]:
        assert all(c["tool_id"] != group["target_tool_id"] for c in group["candidates"])
        assert all(not c["near_miss_verified"] and not c["units_or_api_semantics_verified"] for c in group["candidates"])


def test_build_keeps_review_and_training_gates_closed():
    outputs = v.build()
    summary = json.loads(outputs["validation.json"])
    assert summary["gold_changes_vs_v0.2"] == summary["raw_schema_changes"] == summary["tool_description_changes"] == 0
    assert summary["fresh_v0.3_blind_reviews"] == summary["approved_test_intents"] == summary["training_runs"] == 0
    assert summary["freeze_ready"] is False
    for p in map(json.loads, outputs["pairs.jsonl"].splitlines()):
        assert p["gold_unchanged"] is True
        assert p["control_catalog_tool_ids"] == p["clean_catalog_tool_ids"]
        assert p["old_answers_are_new_results"] is False


def test_synthetic_answer_agreement_is_not_approval(bundle):
    _, clean, pool, schemas, cats, _, _ = bundle
    answers = [{"task_id": d["task_id"], "tool": pool[d["tool_id"]]["tool_name"], "arguments": d["gold_args"]} for d in clean]
    result = v.previous.compare_review(clean, pool, schemas, cats, answers, "synthetic-test-only")
    assert all(r["review_error_kind"] == "correct" for r in result["comparisons"])
    assert result["approved_for_test"] is False
    assert result["independence_verified"] is False
