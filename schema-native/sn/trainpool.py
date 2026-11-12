"""Leakage-safe training pool of schemas.

Source: the same JSONSchemaBench audit the experiment used (``dataset/audit_schemas.jsonl.gz``).
A schema may be used for training only if ALL of these hold:

  1. it passed the experiment's eligibility filter (same definition as the test pool);
  2. it is not one of the 300 frozen test tools;
  3. it is not a near-duplicate of any test tool
       - identical normalized schema hash, or
       - top-level property-name Jaccard >= ``jaccard`` (default 0.5; the pool itself used 0.8,
         so this is stricter), or
       - same Glaive function name (Glaive ids are ``<function>_<hash>``);
  4. it is not a near-duplicate of a schema already kept (families are formed instead).

Kept schemas are grouped into FAMILIES (connected by property-set Jaccard >= ``family_jaccard`` or
equal Glaive function name). Train/validation are split by family, never by row, so a paraphrase or
a sibling schema cannot sit on both sides.

Split names used everywhere in this project:
  known-schema   test tool also seen in training   (NOT available here by design: none are)
  unseen-schema  test tool never seen, same sources as training   -> the frozen 300-tool pool
  unseen-family  test tool from a source held out entirely        -> ``holdout_subsets``

usage: python -m sn.trainpool [--jaccard 0.5] [--holdout-subsets WashingtonPost Snowplow]
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import os
import re

from . import envelope as env
from . import paths
import schema_utils as su  # type: ignore  # noqa: E402


def glaive_base(sid: str) -> str:
    return re.sub(r"_[0-9a-f]{8}$", "", sid.split("/", 1)[1]).lower()


def prop_set(s: dict) -> frozenset:
    return frozenset(k.lower() for k in (s.get("properties") or {}))


def jaccard(a: frozenset, b: frozenset) -> float:
    u = a | b
    return len(a & b) / len(u) if u else 0.0


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def build(jac: float = 0.5, family_jaccard: float = 0.5, holdout_subsets: tuple[str, ...] = (),
          valid_fraction: float = 0.1, seed: int = 20261112) -> dict:
    audit = [json.loads(line) for line in gzip.open(os.path.join(paths.EXP, "dataset", "audit_schemas.jsonl.gz"), "rt")]
    pool = paths.pool()
    test_ids = {t["schema_id"] for t in pool.values()}
    test_hash = {t["schema_sha256"] for t in pool.values()}
    test_props, test_glaive, test_norm = [], set(), set()
    for t in pool.values():
        s = su.load_schema(t["schema_id"])
        test_props.append(prop_set(s))
        if t["subset"] == "Glaiveai2K":
            test_glaive.add(glaive_base(t["schema_id"]))
    by_id = {r["schema_id"]: r for r in audit}
    for sid in test_ids:
        test_norm.add(by_id[sid].get("normalized_sha256"))

    reasons = collections.Counter()
    kept = []
    for r in sorted(audit, key=lambda r: hashlib.sha256(f"{seed}:{r['schema_id']}".encode()).hexdigest()):
        sid = r["schema_id"]
        if not r["eligible"]:
            reasons["not_eligible"] += 1
            continue
        if sid in test_ids:
            reasons["is_test_tool"] += 1
            continue
        s = su.load_schema(sid)
        if su.sha(s) in test_hash or r.get("normalized_sha256") in test_norm:
            reasons["same_schema_as_test_tool"] += 1
            continue
        if r["subset"] == "Glaiveai2K" and glaive_base(sid) in test_glaive:
            reasons["same_glaive_function_as_test_tool"] += 1
            continue
        ps = prop_set(s)
        if any(jaccard(ps, q) >= jac for q in test_props):
            reasons["near_duplicate_of_test_tool"] += 1
            continue
        kept.append({"schema_id": sid, "subset": r["subset"], "stratum": r["stratum"], "props": ps,
                     "keywords": sorted(env.keywords_used(env.argument_schema(s)) & set(env.ASSERTION_KEYWORDS))})
        reasons["kept"] += 1

    # families among kept schemas
    dsu = DSU()
    glaive_rep: dict[str, str] = {}
    by_prop = collections.defaultdict(list)          # inverted index: property name -> schema ids
    for k in kept:
        dsu.find(k["schema_id"])
        if k["subset"] == "Glaiveai2K":
            b = glaive_base(k["schema_id"])
            if b in glaive_rep:
                dsu.union(k["schema_id"], glaive_rep[b])
            glaive_rep.setdefault(b, k["schema_id"])
        for p in k["props"]:
            by_prop[p].append(k)
    for k in kept:
        cands = {}
        for p in k["props"]:
            for o in by_prop[p]:
                if o["schema_id"] > k["schema_id"]:
                    cands[o["schema_id"]] = o
        for o in cands.values():
            if jaccard(k["props"], o["props"]) >= family_jaccard:
                dsu.union(k["schema_id"], o["schema_id"])
    fam_members = collections.defaultdict(list)
    for k in kept:
        fam_members[dsu.find(k["schema_id"])].append(k)
    fam_ids = {root: f"F{i:05d}" for i, root in enumerate(sorted(fam_members))}

    rows = []
    for root, members in fam_members.items():
        fid = fam_ids[root]
        h = int(hashlib.sha256(f"{seed}:split:{fid}".encode()).hexdigest(), 16) / 2 ** 256
        subsets = {m["subset"] for m in members}
        if subsets & set(holdout_subsets):
            split = "holdout_family"              # never trained on: unseen-family test material
        else:
            split = "valid" if h < valid_fraction else "train"
        for m in members:
            rows.append({"schema_id": m["schema_id"], "subset": m["subset"], "stratum": m["stratum"],
                         "family": fid, "split": split, "keywords": m["keywords"]})
    rows.sort(key=lambda r: r["schema_id"])

    summary = {"params": {"jaccard_vs_test": jac, "family_jaccard": family_jaccard, "holdout_subsets": list(holdout_subsets),
                          "valid_fraction": valid_fraction, "seed": seed},
               "filter_counts": dict(reasons), "families": len(fam_members),
               "split_counts": dict(collections.Counter(r["split"] for r in rows)),
               "split_by_stratum": {s: dict(collections.Counter(r["stratum"] for r in rows if r["split"] == s))
                                    for s in ("train", "valid", "holdout_family")},
               "train_keyword_counts": dict(collections.Counter(k for r in rows if r["split"] == "train" for k in r["keywords"]).most_common())}
    return {"rows": rows, "summary": summary}


def check_no_leak(rows: list[dict]) -> None:
    """Hard guarantees; raises AssertionError on any violation."""
    pool_ids = {t["schema_id"] for t in paths.pool().values()}
    assert not ({r["schema_id"] for r in rows} & pool_ids), "test tool in training pool"
    fam_split = collections.defaultdict(set)
    for r in rows:
        fam_split[r["family"]].add(r["split"])
    assert all(len(v) == 1 for v in fam_split.values()), "a family spans two splits"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jaccard", type=float, default=0.5)
    ap.add_argument("--family-jaccard", type=float, default=0.5)
    ap.add_argument("--holdout-subsets", nargs="*", default=["WashingtonPost"])
    ap.add_argument("--out", default=os.path.join(paths.DATA, "trainpool"))
    a = ap.parse_args()
    res = build(a.jaccard, a.family_jaccard, tuple(a.holdout_subsets))
    check_no_leak(res["rows"])
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "schemas.v1.jsonl"), "w") as f:
        for r in res["rows"]:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(a.out, "summary.v1.json"), "w") as f:
        json.dump(res["summary"], f, indent=2)
    print(json.dumps(res["summary"], indent=2))


if __name__ == "__main__":
    main()
