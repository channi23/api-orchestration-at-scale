"""Leakage guarantees of the training pool."""
import collections

from sn import paths, trainpool
import schema_utils as su

RES = trainpool.build(holdout_subsets=("WashingtonPost",))
ROWS = RES["rows"]


def test_no_test_tool_and_no_family_across_splits():
    trainpool.check_no_leak(ROWS)


def test_no_training_schema_is_close_to_a_test_tool():
    pool = paths.pool()
    test_props = [trainpool.prop_set(su.load_schema(t["schema_id"])) for t in pool.values()]
    test_glaive = {trainpool.glaive_base(t["schema_id"]) for t in pool.values() if t["subset"] == "Glaiveai2K"}
    for r in ROWS:
        ps = trainpool.prop_set(su.load_schema(r["schema_id"]))
        assert max(trainpool.jaccard(ps, q) for q in test_props) < 0.5, r["schema_id"]
        if r["subset"] == "Glaiveai2K":
            assert trainpool.glaive_base(r["schema_id"]) not in test_glaive


def test_holdout_subset_is_never_trained_on():
    assert all(r["split"] == "holdout_family" for r in ROWS if r["subset"] == "WashingtonPost")
    fam_split = collections.defaultdict(set)
    for r in ROWS:
        fam_split[r["family"]].add(r["split"])
    assert all(len(v) == 1 for v in fam_split.values())


def test_build_is_deterministic():
    again = trainpool.build(holdout_subsets=("WashingtonPost",))["rows"]
    assert again == ROWS
