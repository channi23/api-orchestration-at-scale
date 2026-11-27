"""Offline authoring checks; no model server, engine helper, or training imports."""
import copy
import json

import pytest
from referencing.exceptions import Unresolvable

from sn import v2_authoring as v2


@pytest.fixture(scope="module")
def inputs():
    return v2.load_inputs()


def test_all_authored_golds_validate_without_becoming_test_tasks(inputs):
    drafts, pool, schemas, old, _ = inputs
    assert len(drafts) == 32
    assert {d["tool_id"] for d in drafts}.isdisjoint({t["tool_id"] for t in old})
    for d in drafts:
        assert v2.validator(schemas[d["tool_id"]]).is_valid(d["gold_args"])
        assert not v2.build_tasks.leakage(d["request"], pool[d["tool_id"]], schemas[d["tool_id"]])


def test_blind_packet_uses_only_visible_fields_and_five_distinct_tools(inputs):
    drafts, pool, schemas, _, _ = inputs
    packets = v2.review_packet(drafts, pool, schemas)
    assert len(packets) == len(drafts)
    for p in packets:
        assert set(p) == {"task_id", "request", "tools"}
        assert len(p["tools"]) == len({t["name"] for t in p["tools"]}) == 5
        assert all(set(t) == {"name", "description", "parameters"} for t in p["tools"])
        assert not any(tid in p["task_id"] for tid in pool)
    changed = copy.deepcopy(drafts)
    for d in changed:
        d["gold_args"] = {"SECRET_GOLD_SENTINEL": "never export this"}
        d["reasoning_note"] = "SECRET_NOTE_SENTINEL"
    assert v2.review_packet(changed, pool, schemas) == packets
    assert "SECRET_GOLD_SENTINEL" not in json.dumps(packets)


def test_review_packet_is_deterministic_and_does_not_mutate_inputs(inputs):
    drafts, pool, schemas, _, _ = inputs
    original = copy.deepcopy((drafts, pool, schemas))
    assert v2.review_packet(drafts, pool, schemas) == v2.review_packet(drafts, pool, schemas)
    assert (drafts, pool, schemas) == original


def answers_for(drafts, pool):
    # Synthetic fixture only, never an independent review or a persisted approval.
    return [{"task_id": v2.review_id(d), "tool": pool[d["tool_id"]]["tool_name"],
             "arguments": copy.deepcopy(d["gold_args"])} for d in drafts]


def test_agreement_does_not_automatically_approve_or_prove_independence(inputs):
    drafts, pool, schemas, _, _ = inputs
    result = v2.check_review(drafts, pool, schemas, answers_for(drafts, pool), "synthetic-test-only")
    assert result["agreement_count"] == 32
    assert result["approved_for_test"] is False
    assert result["independence_verified"] is False


def test_semantically_wrong_but_valid_answer_requires_adjudication(inputs):
    drafts, pool, schemas, _, _ = inputs
    answers = answers_for(drafts, pool)
    i = next(i for i, d in enumerate(drafts) if d["tool_id"] == "T064")
    answers[i]["arguments"]["country"] = "Panama"
    result = v2.check_review(drafts, pool, schemas, answers, "synthetic-test-only")
    r = next(r for r in result["comparisons"] if r["task_id"] == answers[i]["task_id"])
    assert r["raw_valid"] is True
    assert r["agrees_with_draft"] is False
    assert r["requires_adjudication"] is True


def test_review_must_cover_each_task_once(inputs):
    drafts, pool, schemas, _, _ = inputs
    answers = answers_for(drafts, pool)
    with pytest.raises(ValueError, match="exactly once"):
        v2.check_review(drafts, pool, schemas, answers[:-1], "synthetic-test-only")
    answers[-1] = answers[0]
    with pytest.raises(ValueError, match="exactly once"):
        v2.check_review(drafts, pool, schemas, answers, "synthetic-test-only")


def test_author_cannot_be_passed_off_as_separate_reviewer(inputs):
    drafts, pool, schemas, _, _ = inputs
    with pytest.raises(ValueError, match="separately"):
        v2.check_review(drafts, pool, schemas, answers_for(drafts, pool), v2.AUTHOR)


@pytest.mark.parametrize("text", ['{"a":1,"a":2}', '{"x":NaN}', '{"x":1e999}', '```json\n{}\n```'])
def test_review_parser_rejects_non_strict_json(text):
    with pytest.raises(ValueError):
        v2.strict_loads(text)


def test_argument_comparison_preserves_json_semantics():
    assert v2.argument_equal({"age": 25, "name": "Maya"}, {"name": "Maya", "age": 25.0})
    assert not v2.argument_equal({"age": True}, {"age": 1})
    assert not v2.argument_equal([1, 2], [2, 1])
    assert not v2.argument_equal({"name": "Maya"}, {"name ": "Maya"})
    assert not v2.argument_equal({"name": "Maya"}, {"name": "maya"})
    assert not v2.argument_equal({}, {"extra": None})


def test_unknown_dialect_is_not_silently_defaulted():
    with pytest.raises(ValueError, match="dialect"):
        v2.validator({"$schema": "https://example.com/unknown-dialect", "type": "object"})


def test_remote_references_fail_closed_without_network():
    with pytest.raises((ValueError, Unresolvable)):
        v2.validator({"$ref": "https://example.com/forbidden.json"}).is_valid({})


def test_inventory_keeps_exposure_and_family_leakage_visible():
    outputs = v2.audit()
    summary = json.loads(outputs["validation.json"])
    inventory = [json.loads(line) for line in outputs["inventory.jsonl"].splitlines()]
    assert summary["candidate_tools"] == 250
    assert summary["candidate_exposure_counts"] == {"e0_clean": 100, "original_full_v2": 246}
    assert summary["gold_raw_valid"] == 32
    assert summary["external_stress_cases_inventoried"] == 21
    assert summary["accepted_test_intents"] == summary["independent_reviews"] == 0
    assert summary["freeze_ready"] is False
    calendar = next(r for r in inventory if r["tool_id"] == "T033")
    assert calendar["split"] == "development_only"
    assert calendar["v1_target_family_siblings"]
    assert all(not r["accepted_for_test"] for r in inventory)
    assert all(r["source_license_status"] == "unverified" for r in inventory)
