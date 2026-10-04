"""Build nested catalogs (same tasks evaluated at every size) from the frozen tool pool.

Output: catalogs/catalogs.v1.json  and catalogs/targets.v1.json
"""
from __future__ import annotations

import collections
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_utils as su  # noqa: E402

CFG = json.load(open(os.path.join(su.EXP, "config", "experiment.json")))["catalogs"]


def main():
    pool = [json.loads(l) for l in open(os.path.join(su.EXP, "dataset", "tool_pool.v1.jsonl"))]
    by_id = {t["tool_id"]: t for t in pool}
    rng = random.Random(f"{CFG['seed']}:targets")
    flat_t = [t["tool_id"] for t in pool if t["task_suitable"] and t["stratum"] == "flat"]
    str_t = [t["tool_id"] for t in pool if t["task_suitable"] and t["stratum"] == "structured"]
    rng.shuffle(flat_t)
    rng.shuffle(str_t)
    R, K = CFG["n_replicates"], CFG["targets_per_replicate"]
    targets, fi, si = {}, 0, 0
    for r in range(R):
        nf = 3 if r % 2 == 0 else 2
        chosen = []
        while len(chosen) < K:
            want_flat = sum(by_id[c]["stratum"] == "flat" for c in chosen) < nf
            lst, idx = (flat_t, fi) if want_flat else (str_t, si)
            while True:  # skip tools whose family collides with an already chosen target
                cand = lst[idx]
                idx += 1
                if by_id[cand]["family"] not in {by_id[c]["family"] for c in chosen}:
                    break
            if want_flat:
                fi = idx
            else:
                si = idx
            chosen.append(cand)
        targets[r] = chosen
    used = [t for v in targets.values() for t in v]
    assert len(set(used)) == len(used) == R * K

    catalogs = []
    for r in range(R):
        rng_r = random.Random(f"{CFG['seed']}:replicate:{r}")
        fams = {by_id[t]["family"] for t in targets[r]}
        others = [t["tool_id"] for t in pool if t["tool_id"] not in targets[r]]
        rng_r.shuffle(others)
        flat_q = [t for t in others if by_id[t]["stratum"] == "flat"]
        str_q = [t for t in others if by_id[t]["stratum"] == "structured"]
        order = list(targets[r])
        cnt = collections.Counter(by_id[t]["stratum"] for t in order)
        while len(order) < max(CFG["sizes"]):
            pick_flat = cnt["flat"] <= cnt["structured"]
            q = flat_q if pick_flat else str_q
            while True:
                cand = q.pop(0)
                if by_id[cand]["family"] not in fams:
                    break
            fams.add(by_id[cand]["family"])
            order.append(cand)
            cnt[by_id[cand]["stratum"]] += 1
        for k in CFG["sizes"]:
            members = order[:k]
            pres = list(members)
            random.Random(f"{CFG['seed']}:order:{r}:{k}").shuffle(pres)
            catalogs.append({
                "catalog_id": f"C{k:03d}_R{r:02d}", "replicate": r, "size": k,
                "tool_ids": members, "presentation_order": pres,
                "target_tool_ids": targets[r],
                "target_positions": {t: pres.index(t) for t in targets[r]},
                "strata": dict(collections.Counter(by_id[t]["stratum"] for t in members)),
                "subsets": dict(collections.Counter(by_id[t]["subset"] for t in members)),
                "mean_chars_pretty": round(sum(by_id[t]["features"]["chars_pretty"] for t in members) / k, 1),
                "mean_n_top_props": round(sum(by_id[t]["features"]["n_top_props"] for t in members) / k, 2),
                "mean_n_required": round(sum(by_id[t]["features"]["n_required"] for t in members) / k, 2),
                "seed": f"{CFG['seed']}:replicate:{r} / order:{r}:{k}",
            })
    os.makedirs(os.path.join(su.EXP, "catalogs"), exist_ok=True)
    json.dump({"config": CFG, "catalogs": catalogs}, open(os.path.join(su.EXP, "catalogs", "catalogs.v1.json"), "w"), indent=1)
    json.dump({str(r): [{"tool_id": t, "tool_name": by_id[t]["tool_name"], "stratum": by_id[t]["stratum"],
                         "schema_id": by_id[t]["schema_id"]} for t in v] for r, v in targets.items()},
              open(os.path.join(su.EXP, "catalogs", "targets.v1.json"), "w"), indent=1)
    for c in catalogs:
        if c["size"] in (5, 100):
            print(c["catalog_id"], c["strata"], c["mean_chars_pretty"], c["subsets"])


if __name__ == "__main__":
    main()
