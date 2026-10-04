"""Evaluator self-tests: gold must pass for every task; perturbations must fail in the right category."""
import copy, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import schema_utils as su
from evaluate import evaluate

EXP = su.EXP
tasks = [json.loads(l) for l in open(os.path.join(EXP, "tasks", "tasks.v1.jsonl"))]
pool = {json.loads(l)["tool_id"]: json.loads(l) for l in open(os.path.join(EXP, "dataset", "tool_pool.v1.jsonl"))}
names = {t["tool_name"] for t in pool.values()}


def out(tool, args, wrap=None):
    s = json.dumps({"tool": tool, "arguments": args})
    return wrap.format(s) if wrap else s


def run(content, t):
    return evaluate(content, t, su.load_schema(t["schema_id"]), names)


def test_gold_passes_all():
    for t in tasks:
        r = run(out(t["tool_name"], t["gold_args"]), t)
        assert r["e2e_success"] and r["arg_exact_match"] and r["field_acc"] == 1.0, (t["task_id"], r)
        assert r["failure_primary"] is None


def test_gold_with_think_and_fences():
    t = tasks[0]
    r = run(out(t["tool_name"], t["gold_args"], "<think>\n\n</think>\n```json\n{}\n```"), t)
    assert r["e2e_success"] and r["json_strict"]


def test_wrong_tool():
    t = tasks[0]
    other = next(n for n in names if n != t["tool_name"])
    r = run(out(other, t["gold_args"]), t)
    assert not r["e2e_success"] and r["failure_primary"] == "wrong tool"


def test_malformed():
    t = tasks[0]
    r = run("I would call the tool with id foo", t)
    assert r["failure_primary"] == "malformed output" and not r["json_valid"]


def test_missing_required():
    t = next(x for x in tasks if x["tool_name"] == "register_vendor_app")
    a = dict(t["gold_args"]); a.pop("vendor_id")
    r = run(out(t["tool_name"], a), t)
    assert r["failure_primary"] == "missing required argument", r


def test_enum_case():
    t = next(x for x in tasks if x["tool_name"] == "register_dog")
    a = dict(t["gold_args"]); a["breed"] = "Labrador"
    r = run(out(t["tool_name"], a), t)
    assert r["failure_primary"] == "invalid enum/value" and r["field_acc"] == 1.0 and not r["e2e_success"], r


def test_type_error():
    t = next(x for x in tasks if x["tool_name"] == "change_configuration")
    a = dict(t["gold_args"]); a["value"] = 300
    r = run(out(t["tool_name"], a), t)
    assert r["failure_primary"] == "invalid argument type", r


def test_hallucinated_field_strict_schema():
    t = next(x for x in tasks if x["tool_name"] == "register_vendor_app")
    a = dict(t["gold_args"]); a["color"] = "red"
    r = run(out(t["tool_name"], a), t)
    assert r["failure_primary"] == "hallucinated field", r


def test_wrong_value():
    t = next(x for x in tasks if x["tool_name"] == "calculate_distance")
    a = dict(t["gold_args"]); a["latitude2"] = 3.0
    r = run(out(t["tool_name"], a), t)
    assert r["failure_primary"] == "correct tool, wrong argument" and r["schema_valid"] and not r["e2e_success"], r


def test_unordered_and_case_insensitive():
    t = next(x for x in tasks if x["tool_name"] == "add_employees")
    a = copy.deepcopy(t["gold_args"]); a["employees"].reverse(); a["employees"][0]["title"] = "network engineer"
    r = run(out(t["tool_name"], a), t)
    assert r["e2e_success"] and not r["arg_exact_match"], r


def test_alias_format():
    t = tasks[0]
    r = run(json.dumps({"name": t["tool_name"], "parameters": t["gold_args"]}), t)
    assert r["e2e_success"] and r["format_alias_used"]


def test_constraint_violation():
    t = next(x for x in tasks if x["tool_name"] == "create_api_stage")
    a = dict(t["gold_args"]); a["RestApiId"] = "ABC"
    r = run(out(t["tool_name"], a), t)
    assert r["failure_primary"] == "ignored schema constraint", r


if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); n += 1
    print(f"{n} evaluator tests passed")
