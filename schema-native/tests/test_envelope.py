"""The constrained-decoding envelope must never make a gold answer invalid."""
import jsonschema

from sn import envelope as env
from sn import paths
import schema_utils as su


def _validator(schema):
    return jsonschema.Draft7Validator(schema)


def test_every_gold_call_validates_against_its_single_tool_envelope():
    pool = paths.pool()
    for t in paths.tasks():
        raw = su.load_schema(pool[t["tool_id"]]["schema_id"])
        call = env.gold_call(t, raw)
        errs = list(_validator(env.envelope([(t["tool_name"], raw)])).iter_errors(call))
        assert not errs, (t["task_id"], errs[0].message)


def test_every_gold_call_validates_against_its_catalog_envelope_and_matches_one_branch():
    pool, cats = paths.pool(), paths.catalogs()
    for t in paths.tasks():
        for size in (5, 20):
            cat = cats[f"C{size:03d}_R{t['replicate']:02d}"]
            tools = [(pool[i]["tool_name"], su.load_schema(pool[i]["schema_id"])) for i in cat["presentation_order"]]
            schema = env.envelope(tools)
            call = env.gold_call(t, su.load_schema(pool[t["tool_id"]]["schema_id"]))
            assert not list(_validator(schema).iter_errors(call)), t["task_id"]
            matching = [b for b in schema["anyOf"] if not list(_validator(b).iter_errors(call))]
            assert len(matching) == 1, (t["task_id"], len(matching))


def test_envelope_is_self_contained():
    pool = paths.pool()
    for tid, tool in pool.items():
        branch = env.tool_branch(tool["tool_name"], su.load_schema(tool["schema_id"]))
        assert not list(su.iter_refs(branch)), tid          # no $ref left to dangle


def test_wrong_tool_name_and_extra_envelope_keys_are_rejected():
    pool = paths.pool()
    t = paths.tasks()[0]
    raw = su.load_schema(pool[t["tool_id"]]["schema_id"])
    schema = env.envelope([(t["tool_name"], raw)])
    v = _validator(schema)
    assert list(v.iter_errors({"tool": "not_a_tool", "arguments": t["gold_args"]}))
    assert list(v.iter_errors({"tool": t["tool_name"], "arguments": t["gold_args"], "note": "x"}))
    assert list(v.iter_errors({"tool": t["tool_name"]}))


def test_ordered_like_schema_keeps_the_value():
    schema = {"properties": {"b": {}, "a": {"properties": {"y": {}, "x": {}}}}}
    value = {"a": {"x": 1, "y": 2}, "z": 3, "b": 0}
    out = env.ordered_like_schema(value, schema)
    assert out == value
    assert list(out) == ["b", "a", "z"] and list(out["a"]) == ["y", "x"]


def test_keywords_used_ignores_data_positions():
    s = {"properties": {"x": {"enum": [{"not": 1}], "default": {"if": 1}}}, "required": ["x"]}
    assert "not" not in env.keywords_used(s) and "if" not in env.keywords_used(s)
    assert {"properties", "enum", "required"} <= env.keywords_used(s)
