"""The failure decomposition must reproduce the finished experiment's own numbers."""
import json
import os

from sn import ceiling, paths


def _rows(arm, fam="select"):
    rows = paths.jsonl(os.path.join(paths.EXP, "runs", "full-v2", "results.jsonl"))
    return [r for r in rows if r["arm"] == arm and r["family"] == fam]


def test_success_matches_published_results_json():
    pub = json.load(open(os.path.join(paths.EXP, "analysis", "full-v2", "results.json")))
    prim = next(c for c in pub["comparisons"] if c["name"].startswith("PRIMARY")) if "comparisons" in pub else None
    d_raw, d_tscg = ceiling.decompose(_rows("raw")), ceiling.decompose(_rows("tscg"))
    assert d_raw["n"] == 500 and d_raw["success"] == 412          # 82.4 %
    assert d_tscg["success"] == 283                               # 56.6 %
    if prim:
        assert abs(prim["acc_a"] - d_raw["success"] / 500) < 1e-9
        assert abs(prim["acc_b"] - d_tscg["success"] / 500) < 1e-9


def test_classes_partition_the_failures():
    for arm in ("raw", "minified", "normalized", "tscg", "tscg_info"):
        d = ceiling.decompose(_rows(arm))
        assert d["success"] + sum(d[k] for k in ceiling.CLASSES) == d["n"]
        assert d["success_pct"] <= d["cd_conservative_pct"] <= d["cd_upper_bound_pct"] <= 100


def test_classify_rules():
    base = {"e2e_success": False, "json_valid": True, "format_ok": True, "tool_correct": True,
            "schema_valid": True, "semantic_correct": False}
    assert ceiling.classify(dict(base, e2e_success=True)) is None
    assert ceiling.classify(dict(base, json_valid=False)) == "malformed"
    assert ceiling.classify(dict(base, tool_correct=False)) == "wrong_tool"
    assert ceiling.classify(dict(base, schema_valid=False, semantic_correct=True)) == "invalid_only"
    assert ceiling.classify(dict(base, schema_valid=False)) == "invalid_wrong"
    assert ceiling.classify(base) == "valid_wrong"


def test_pairs_needed_is_monotone():
    assert ceiling.mcnemar_pairs_needed(0.05, 0.2) > ceiling.mcnemar_pairs_needed(0.10, 0.2)
    assert ceiling.mcnemar_pairs_needed(0.05, 0.2) > ceiling.mcnemar_pairs_needed(0.05, 0.1)
