"""Deterministic ranking of eligible schemas into a candidate list for the tool pool.

The ranked list is reviewed in order (accept/reject with recorded reason, see
dataset/tool_metadata.v1.jsonl). Ranking, deduplication and stratification are
fully determined by config/experiment.json["pool"].
Output: dataset/pool_candidates.jsonl (rank order, interleaved by stratum).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_utils as su  # noqa: E402

CFG = json.load(open(os.path.join(su.EXP, "config", "experiment.json")))
P = CFG["pool"]


def rank_key(sid: str) -> str:
    return hashlib.sha256(f"{P['seed']}:{sid}".encode()).hexdigest()


def glaive_base(sid: str) -> str:
    return re.sub(r"_[0-9a-f]{8}$", "", sid.split("/", 1)[1]).lower()


def prop_set(s: dict) -> frozenset:
    return frozenset(k.lower() for k in (s.get("properties") or {}))


def main():
    recs = [json.loads(l) for l in gzip.open(os.path.join(su.EXP, "dataset", "audit_schemas.jsonl.gz"), "rt")]
    el = sorted((r for r in recs if r["eligible"]), key=lambda r: rank_key(r["schema_id"]))
    chosen, seen_glaive, seen_props = [], set(), []
    skipped = {"glaive_same_function_name": 0, "near_duplicate_property_set": 0}
    for r in el:
        s = su.load_schema(r["schema_id"])
        if r["subset"] == "Glaiveai2K":
            b = glaive_base(r["schema_id"])
            if b in seen_glaive:
                skipped["glaive_same_function_name"] += 1
                continue
            seen_glaive.add(b)
        ps = prop_set(s)
        dup = next((sid for sid, q in seen_props
                    if len(ps | q) and len(ps & q) / len(ps | q) >= P["near_duplicate_jaccard"]), None)
        if dup:
            skipped["near_duplicate_property_set"] += 1
            continue
        seen_props.append((r["schema_id"], ps))
        chosen.append(r)
    # interleave strata (flat, structured, flat, ...) so any prefix is balanced
    flat = [r for r in chosen if r["stratum"] == "flat"]
    struct = [r for r in chosen if r["stratum"] == "structured"]
    out = []
    for i in range(max(len(flat), len(struct))):
        for lst in (flat, struct):
            if i < len(lst):
                out.append(lst[i])
    path = os.path.join(su.EXP, "dataset", "pool_candidates.jsonl")
    with open(path, "w") as f:
        for i, r in enumerate(out):
            f.write(json.dumps({"rank": i, "schema_id": r["schema_id"], "subset": r["subset"],
                                "stratum": r["stratum"], "rank_key": rank_key(r["schema_id"]),
                                "glaive_function_name": glaive_base(r["schema_id"]) if r["subset"] == "Glaiveai2K" else None}) + "\n")
    print(f"candidates={len(out)} flat={len(flat)} structured={len(struct)} skipped={skipped}")


if __name__ == "__main__":
    main()
