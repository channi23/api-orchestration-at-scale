"""Compile dataset/review_log.v1.txt into the frozen tool pool dataset/tool_pool.v1.jsonl.

Checks: every candidate rank 0..last reviewed exactly once and in order; tool names unique and
snake_case; names/descriptions contain no dataset identifiers; reject codes are valid.
"""
from __future__ import annotations

import collections
import gzip
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_utils as su  # noqa: E402

CFG = json.load(open(os.path.join(su.EXP, "config", "experiment.json")))
RULES = CFG["pool"]["review_rules"]
FORBIDDEN = [s.lower() for s in su.SUBSETS] + ["glaive", "github", "snowplow", "washingtonpost",
                                                "jsonschemabench", "schemastore", "kubernetes"]


def main():
    cands = {json.loads(l)["rank"]: json.loads(l) for l in open(os.path.join(su.EXP, "dataset", "pool_candidates.jsonl"))}
    audit = {json.loads(l)["schema_id"]: json.loads(l) for l in gzip.open(os.path.join(su.EXP, "dataset", "audit_schemas.jsonl.gz"), "rt")}
    rows, expected, names = [], 0, set()
    decisions = collections.Counter()
    for line in open(os.path.join(su.EXP, "dataset", "review_log.v1.txt")):
        if line.startswith("#") or not line.strip():
            continue
        parts = line.rstrip("\n").split("|")
        rank = int(parts[0])
        assert rank == expected, f"rank {rank} out of order (expected {expected})"
        expected += 1
        c = cands[rank]
        if parts[1] == "R":
            assert parts[2] in RULES["reject_codes"], parts
            decisions["reject:" + parts[2]] += 1
            continue
        assert parts[1] == "A" and len(parts) == 6, parts
        _, _, name, family, ts, desc = parts
        assert re.fullmatch(r"[a-z][a-z0-9_]*", name), name
        assert name not in names, f"duplicate tool name {name}"
        names.add(name)
        assert len(desc.split()) <= 25, (name, len(desc.split()))
        low = (name + " " + desc).lower()
        assert not any(f in low for f in FORBIDDEN), (name, desc)
        decisions["accept"] += 1
        a = audit[c["schema_id"]]
        schema = su.load_schema(c["schema_id"])
        rows.append({
            "tool_id": f"T{len(rows):03d}",
            "tool_name": name, "description": desc, "family": family,
            "task_suitable": ts == "1",
            "schema_id": c["schema_id"], "subset": c["subset"], "stratum": c["stratum"],
            "candidate_rank": rank, "schema_sha256": su.sha(schema),
            "features": {k: a[k] for k in ("n_top_props", "n_required", "max_depth", "chars_pretty",
                                           "has_ref", "has_enum", "has_oneOf", "has_anyOf", "has_allOf",
                                           "has_conditional", "has_array", "has_array_of_objects",
                                           "has_nested_object", "has_constraints", "has_format",
                                           "has_pattern", "has_default", "has_additionalProperties_false")},
        })
    out = os.path.join(su.EXP, "dataset", "tool_pool.v1.jsonl")
    with open(out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    fam = collections.Counter(r["family"] for r in rows)
    summ = {"n_reviewed": expected, "n_accepted": len(rows), "decisions": dict(decisions),
            "by_subset": dict(collections.Counter(r["subset"] for r in rows)),
            "by_stratum": dict(collections.Counter(r["stratum"] for r in rows)),
            "n_families": len(fam), "families_with_multiple_tools": {k: v for k, v in fam.items() if v > 1},
            "task_suitable": sum(r["task_suitable"] for r in rows)}
    json.dump(summ, open(os.path.join(su.EXP, "dataset", "tool_pool.v1.summary.json"), "w"), indent=2, sort_keys=True)
    print(json.dumps(summ, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
