"""Print ranked candidates compactly for metadata review: python show_candidates.py START END"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_utils as su
a, b = int(sys.argv[1]), int(sys.argv[2])
for line in open(os.path.join(su.EXP, "dataset", "pool_candidates.jsonl")):
    r = json.loads(line)
    if a <= r["rank"] < b:
        s = su.load_schema(r["schema_id"])
        for k in ("$schema", "$id", "id"):
            if isinstance(s.get(k), str): s.pop(k)
        print(f"#{r['rank']} {r['schema_id']} [{r['stratum']}]" + (f" fn={r['glaive_function_name']}" if r['glaive_function_name'] else ""))
        print(json.dumps(s, separators=(",", ":"))[:1100])
