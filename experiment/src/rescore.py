"""Re-evaluate stored raw model outputs with the current evaluator and task set (no model calls).
usage: python src/rescore.py runs/<run_id>   -> rewrites runs/<run_id>/results.jsonl eval fields (backup kept)"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_utils as su
from evaluate import evaluate

run = sys.argv[1]
path = os.path.join(run, "results.jsonl")
tasks = {json.loads(l)["task_id"]: json.loads(l) for l in open(os.path.join(su.EXP, "tasks", "tasks.v1.jsonl"))}
pool = {json.loads(l)["tool_id"]: json.loads(l) for l in open(os.path.join(su.EXP, "dataset", "tool_pool.v1.jsonl"))}
cats = {c["catalog_id"]: c for c in json.load(open(os.path.join(su.EXP, "catalogs", "catalogs.v1.json")))["catalogs"]}
rows = [json.loads(l) for l in open(path)]
shutil.copy(path, path + ".pre-rescore")
changed = 0
with open(path, "w") as f:
    for r in rows:
        t = tasks[r["task_id"]]
        ids = cats[r["catalog_id"]]["presentation_order"] if r["catalog_id"] else [t["tool_id"]]
        ctx = r["http_status"] != 200 and "context" in json.dumps(r["error"]).lower()
        ev = evaluate(r["raw_content"], t, su.load_schema(t["schema_id"]), {pool[i]["tool_name"] for i in ids}, context_error=ctx)
        changed += ev["e2e_success"] != r["eval"]["e2e_success"]
        r["eval"] = ev
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"rescored {len(rows)} rows; e2e changed in {changed}")
