"""Semantic controls and proof boundaries for development-only keyword seeds."""
import copy
import json
from collections import Counter
from types import SimpleNamespace

import pytest

from sn import keyword_seed as k


def test_declared_matrices_and_single_edit_paths():
    pairs, checks = k.audit()
    assert len(pairs) == len(checks) == 16
    assert Counter(p["pair_kind"] for p in pairs) == {"validity_separable": 7, "asymmetric_edit": 7, "equivalent_rewrite": 2}
    assert len({p["family_id"] for p in pairs}) == 10
    assert all(p["split"] == "development_only" and not p["approved_for_test"] for p in pairs)
    for p in pairs:
        assert k.proof_check(p)
        if p["edit_path"]:
            assert k.replace(p["schema_S"], p["edit_path"], k.pointer(p["schema_S2"], p["edit_path"])) == p["schema_S2"]


def test_oneof_rejects_overlap_but_anyof_accepts_it():
    by = {p["pair_id"]: p for p in k.cases()}
    both = {"id": "P03", "a": True, "b": True}
    assert not k.common.validator(by["K03"]["schema_S"]).is_valid(both)
    assert k.common.validator(by["K04"]["schema_S"]).is_valid(dict(both, id="P04"))
    assert not k.common.validator(by["K04"]["schema_S2"]).is_valid(dict(both, id="P04"))


def test_conditional_dependencies_and_tuple_positions_are_enforced():
    by = {p["pair_id"]: p for p in k.cases()}
    for key in ("K05", "K06", "K07", "K08"):
        p = by[key]
        assert not k.common.validator(p["schema_S"]).is_valid(p["gold_S2"])
        assert not k.common.validator(p["schema_S2"]).is_valid(p["gold_S"])


def test_asymmetric_changes_are_not_misreported_as_mutual_exclusion():
    p = next(p for p in k.cases() if p["pair_id"] == "K12")
    assert p["pair_kind"] == "asymmetric_edit"
    assert k.common.validator(p["schema_S2"]).is_valid(p["gold_S"])
    assert not k.common.argument_equal(p["gold_S"], p["gold_S2"])


def test_valid_wrong_witnesses_prove_raw_validity_is_not_success():
    for p in k.cases():
        for side in ("S", "S2"):
            assert k.common.validator(p["schema_" + side]).is_valid(p["valid_wrong_" + side])
            assert not k.common.argument_equal(p["valid_wrong_" + side], p["gold_" + side])


def test_negative_witnesses_are_all_validator_rejected():
    for p in k.cases():
        for a, b in (("S", "S2"), ("S2", "S")):
            invalid = k.negatives(p["schema_" + a], p["gold_" + a], p["gold_" + b])
            assert invalid
            assert all(not k.common.validator(p["schema_" + a]).is_valid(v) for v in invalid)


def test_rewrite_proofs_refuse_expansion_outside_the_reviewed_template():
    pairs = {p["pair_id"]: p for p in k.cases()}
    p = copy.deepcopy(pairs["K10"])
    p["schema_S"]["allOf"][0]["additionalProperties"] = False
    assert k.proof_check(p) is False
    p = copy.deepcopy(pairs["K10"])
    p["schema_S"]["allOf"][0]["properties"]["name"] = {"$ref": "#/allOf/1/properties/units"}
    assert k.proof_check(p) is False
    p = copy.deepcopy(pairs["K09"])
    p["schema_S"]["$defs"]["Address"]["$id"] = "https://example.com/changed-scope"
    assert k.proof_check(p) is False


def test_blind_packet_has_only_visible_inputs_and_one_fixed_tool():
    packet = k.review_packet()
    assert len(packet) == len({p["task_id"] for p in packet}) == 32
    assert all(set(p) == {"task_id", "request", "system_policy", "tools"} for p in packet)
    assert all(len(p["tools"]) == 1 for p in packet)
    assert all(set(p["tools"][0]) == {"name", "description", "parameters"} for p in packet)


def test_audit_does_not_authorize_models_or_promote_tasks():
    files = k.build()
    summary = json.loads(files["validation.json"])
    manifest = json.loads(files["manifest.json"])
    assert summary["approved_test_intents"] == summary["independent_reviews"] == 0
    assert manifest["inference_requests"] == manifest["training_runs"] == 0
    assert manifest["native_support_claimed"] is False


def test_malformed_native_result_fails_closed(monkeypatch):
    from sn import native_audit
    profile = json.loads((k.Path(k.common.paths.ROOT) / "configs/model.qwen3-1.7b.sustainable.json").read_text())
    monkeypatch.setattr(native_audit, "verified_build", lambda *a: {"helper_sha256": "x", "library_sha256": "y"})
    monkeypatch.setattr(k.subprocess, "check_output", lambda *a, **kw: profile["llguidance_commit"])
    monkeypatch.setattr(k.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout="\n".join(json.dumps({"compile_ok": True, "accepts": []}) for _ in range(32))))
    with pytest.raises(ValueError, match="Malformed native"):
        k.native_check(k.Path("/tmp/helper"), k.Path("/tmp/source/target/release/lib.a"))
