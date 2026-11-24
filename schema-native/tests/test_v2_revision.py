"""Revisions cannot silently rewrite the parent or turn agreement into approval."""
import copy
import json
from collections import Counter

import pytest

from sn import v2_revision as v


@pytest.fixture(scope="module")
def bundle():
    old, clean, pool, schemas, nominations = v.load()
    cats, counts = v.catalogs(clean, pool, nominations)
    return old, clean, pool, schemas, nominations, cats, counts


def test_only_poll_and_quiz_gold_change_and_both_validate(bundle):
    old, clean, _, schemas, _, _, _ = bundle
    parents = {d["tool_id"]: d for d in old}
    changed = {d["tool_id"] for d in clean if not v.parent.argument_equal(d["gold_args"], parents[d["tool_id"]]["gold_args"])}
    assert changed == {"T039", "T213"}
    for d in clean:
        assert v.parent.validator(schemas[d["tool_id"]]).is_valid(d["gold_args"])
    poll = next(d for d in clean if d["tool_id"] == "T039")
    assert all(set(option) == {"value"} for option in poll["gold_args"]["answers"])
    quiz = next(d for d in clean if d["tool_id"] == "T213")
    assert set(quiz["gold_args"]) == {"text", "correctAnswers", "incorrectAnswers"}


def test_new_ids_cannot_reuse_old_blind_answers(bundle):
    old, clean, _, _, _, _, _ = bundle
    assert {v.parent.review_id(d) for d in old}.isdisjoint({d["task_id"] for d in clean})
    assert len({d["task_id"] for d in clean}) == 32


def test_catalog_cap_and_disclosed_near_miss_gaps(bundle):
    _, clean, pool, _, nominations, cats, counts = bundle
    assert max(counts.values()) == 3
    actual = Counter()
    for d in clean:
        c = cats[d["tool_id"]]
        assert len(c["tool_ids"]) == len(set(c["tool_ids"])) == 5
        assert d["tool_id"] in c["tool_ids"]
        actual.update(t for t in c["tool_ids"] if t != d["tool_id"])
        assert c["nominated_minimum_met"] == (len(c["nominated_near_tool_ids"]) >= 2)
        assert c["independently_verified_near_misses"] is False
    assert actual == counts
    assert sum(not c["nominated_minimum_met"] for c in cats.values()) == 10
    assert v.catalogs(clean, pool, nominations) == (cats, counts)


def test_catalog_limit_not_relaxed_if_assignment_fails(bundle):
    _, clean, pool, _, _, _, _ = bundle
    two = clean[:2]
    selected = {d["tool_id"] for d in two}
    for tid in sorted(pool):
        if len(selected) == 6:
            break
        selected.add(tid)
    small = {tid: pool[tid] for tid in selected}
    nom = {"max_distractor_appearances": 1, "minimum_nominated_near_misses": 0,
           "tools": {d["tool_id"]: {"near": [], "adjacent": []} for d in two}}
    with pytest.raises(ValueError, match="within cap"):
        v.catalogs(two, small, nom)


def test_blind_packet_has_prompt_policy_but_no_gold_or_pair_metadata(bundle):
    _, clean, pool, schemas, _, cats, _ = bundle
    policy = (v.DATA / "SYSTEM_POLICY.txt").read_text()
    first = v.packet(clean, pool, schemas, cats, policy)
    assert all(set(p) == {"task_id", "request", "system_policy", "tools"} for p in first)
    assert all(p["system_policy"] == policy for p in first)
    assert "Omit optional fields the request does not ask for" in policy
    changed = copy.deepcopy(clean)
    for d in changed:
        d["gold_args"] = {"DO_NOT_EXPORT_GOLD": "secret"}
        d["change_kind"] = "DO_NOT_EXPORT_KIND"
    assert v.packet(changed, pool, schemas, cats, policy) == first
    assert "DO_NOT_EXPORT" not in json.dumps(first)


def test_pairs_keep_parent_text_and_match_catalogs_and_prompt(bundle):
    output = v.build()
    pairs = [json.loads(line) for line in output["pairs.jsonl"].splitlines()]
    summary = json.loads(output["validation.json"])
    assert len(pairs) == 32
    for p in pairs:
        assert p["control_catalog_tool_ids"] == p["clean_catalog_tool_ids"]
        assert p["control_policy_sha256"] == p["clean_policy_sha256"]
        assert p["pure_scaffolding_effect_established"] is False
        assert p["previous_blind_answers_reusable_as_new_results"] is False
    assert sum(p["wording_only_candidate"] for p in pairs) == 24
    assert summary["freeze_ready"] is False
    assert summary["fresh_blind_reviews"] == summary["approved_test_intents"] == 0


def test_default_only_failure_is_separate(bundle):
    _, clean, pool, schemas, _, _, _ = bundle
    d = next(d for d in clean if d["tool_id"] == "T107")
    args = dict(d["gold_args"], NetworkSpeed=0)
    answer = {"tool": pool["T107"]["tool_name"], "arguments": args}
    result = v.diagnose(answer, answer["tool"], d["gold_args"], schemas["T107"])
    assert result["raw_valid"] is True
    assert result["extra_default_paths"] == ["/NetworkSpeed"]
    assert result["only_extra_defaults"] is True
    assert result["review_error_kind"] == "valid_extra_default_fields"


def test_default_flag_does_not_hide_another_mapping_error(bundle):
    _, clean, pool, schemas, _, _, _ = bundle
    d = next(d for d in clean if d["tool_id"] == "T107")
    args = dict(d["gold_args"], NetworkSpeed=0, StaticIPv4Gateway="192.0.2.99")
    answer = {"tool": pool["T107"]["tool_name"], "arguments": args}
    result = v.diagnose(answer, answer["tool"], d["gold_args"], schemas["T107"])
    assert result["has_extra_default_fields"] is True
    assert result["only_extra_defaults"] is False
    assert result["review_error_kind"] == "valid_wrong_value"


def test_default_flag_preserves_boolean_number_distinction():
    schema = {"type": "object", "properties": {"flag": {"type": "boolean", "default": False}}}
    wrong = v.diagnose({"tool": "t", "arguments": {"flag": 0}}, "t", {}, schema)
    right_default = v.diagnose({"tool": "t", "arguments": {"flag": False}}, "t", {}, schema)
    assert wrong["review_error_kind"] == "invalid"
    assert wrong["extra_default_paths"] == []
    assert right_default["review_error_kind"] == "valid_extra_default_fields"


def test_nested_defaults_are_not_misrepresented_as_supported():
    schema = {"type": "object", "properties": {"settings": {"type": "object", "properties": {"x": {"default": 0}}}}}
    result = v.diagnose({"tool": "t", "arguments": {"settings": {"x": 0}}}, "t", {"settings": {}}, schema)
    assert result["default_diagnostic_scope"] == "direct_root_properties"
    assert result["extra_default_paths"] == []
    assert result["review_error_kind"] == "valid_wrong_value"


def test_synthetic_agreement_cannot_approve_tasks(bundle):
    _, clean, pool, schemas, _, cats, _ = bundle
    answers = [{"task_id": d["task_id"], "tool": pool[d["tool_id"]]["tool_name"], "arguments": d["gold_args"]} for d in clean]
    result = v.compare_review(clean, pool, schemas, cats, answers, "synthetic-test-only")
    assert all(r["review_error_kind"] == "correct" for r in result["comparisons"])
    assert result["approved_for_test"] is False
    assert result["independence_verified"] is False
    with pytest.raises(ValueError, match="reviewer"):
        v.compare_review(clean, pool, schemas, cats, answers, v.parent.AUTHOR)
    answers[-1] = answers[0]
    with pytest.raises(ValueError, match="exactly once"):
        v.compare_review(clean, pool, schemas, cats, answers, "synthetic-test-only")
