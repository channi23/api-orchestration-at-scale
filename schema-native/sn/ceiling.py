"""Zero-compute analysis of an existing run: what could constrained decoding fix, and how much
statistical power does the frozen task set have?

Every failed request is put in exactly one class, in this order:

  malformed      output is not a parseable tool call
  wrong_tool     parseable, but the wrong tool
  invalid_only   right tool, arguments violate the raw schema, requested values are all correct
  invalid_wrong  right tool, arguments violate the raw schema, and a requested value is wrong
  valid_wrong    right tool, arguments satisfy the raw schema, a requested value is wrong

Constrained decoding against a sound and complete engine can only change the first four classes
(it forces a parseable call, a listed tool name and schema-valid arguments). It cannot repair
``valid_wrong`` by construction: those outputs are already inside the language the grammar accepts.
So ``success + malformed + wrong_tool* + invalid_*`` is an UPPER BOUND for a decoding-only fix and
``valid_wrong`` is a LOWER BOUND on what must be learned (or retrieved, or asked).
(* a grammar restricts the tool name to the catalog; it does not pick the right one.)

usage: python -m sn.ceiling --run full-v2 [--arms raw minified normalized]
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import statistics

from . import paths

CLASSES = ["malformed", "wrong_tool", "invalid_only", "invalid_wrong", "valid_wrong"]


def classify(ev: dict) -> str | None:
    if ev["e2e_success"]:
        return None
    if not ev["json_valid"] or not ev.get("format_ok", True):
        return "malformed"
    if not ev["tool_correct"]:
        return "wrong_tool"
    if not ev["schema_valid"]:
        return "invalid_only" if ev["semantic_correct"] else "invalid_wrong"
    return "valid_wrong"


def decompose(rows: list[dict]) -> dict:
    n = len(rows)
    c = collections.Counter(classify(r["eval"]) for r in rows)
    ok = c.pop(None, 0)
    out = {"n": n, "success": ok, "success_pct": 100 * ok / n}
    for k in CLASSES:
        out[k] = c.get(k, 0)
    structural = out["malformed"] + out["invalid_only"] + out["invalid_wrong"]
    out["structural"] = structural
    # decoding-only upper bound: every structural failure becomes a success (wrong_tool excluded:
    # an enum over tool names cannot choose for the model).
    out["cd_upper_bound_pct"] = 100 * (ok + structural) / n
    # conservative bound: only failures whose requested values were already right
    out["cd_conservative_pct"] = 100 * (ok + out["invalid_only"]) / n
    out["semantic_floor_pct"] = 100 * (out["valid_wrong"] + out["wrong_tool"]) / n
    return out


def design_effect(rows: list[dict], cluster="tool_id") -> dict:
    """Intra-cluster correlation of success within a target tool, by one-way ANOVA estimator."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r[cluster]].append(int(r["eval"]["e2e_success"]))
    k = len(by)
    sizes = [len(v) for v in by.values()]
    n = sum(sizes)
    grand = sum(sum(v) for v in by.values()) / n
    ssb = sum(len(v) * (sum(v) / len(v) - grand) ** 2 for v in by.values())
    ssw = sum(sum((x - sum(v) / len(v)) ** 2 for x in v) for v in by.values())
    msb, msw = ssb / (k - 1), ssw / (n - k)
    m0 = (n - sum(s * s for s in sizes) / n) / (k - 1)
    icc = max(0.0, (msb - msw) / (msb + (m0 - 1) * msw)) if msb + (m0 - 1) * msw > 0 else 0.0
    mbar = n / k
    deff = 1 + (mbar - 1) * icc
    return {"clusters": k, "n": n, "mean_cluster_size": mbar, "icc": icc, "design_effect": deff,
            "effective_n": n / deff, "tools_with_any_failure": sum(1 for v in by.values() if min(v) == 0),
            "share_of_failures_in_top5_tools": _top_share(by, 5)}


def _top_share(by: dict, k: int) -> float:
    fails = sorted((len(v) - sum(v) for v in by.values()), reverse=True)
    tot = sum(fails)
    return sum(fails[:k]) / tot if tot else 0.0


def mcnemar_pairs_needed(delta: float, discordant: float, alpha_z: float = 1.96, power_z: float = 0.84) -> float:
    """Pairs needed to detect an absolute difference `delta` when a share `discordant` of pairs
    disagree (normal approximation to McNemar; Connor 1987)."""
    return (alpha_z * math.sqrt(discordant) + power_z * math.sqrt(discordant - delta ** 2)) ** 2 / delta ** 2


def run(run_id: str, arms: list[str], out_dir: str) -> dict:
    rows = paths.jsonl(os.path.join(paths.EXP, "runs", run_id, "results.jsonl"))
    res = {"run": run_id, "arms": {}}
    for arm in arms:
        a = {}
        sel = [r for r in rows if r["arm"] == arm and r["family"] == "select"]
        ag = [r for r in rows if r["arm"] == arm and r["family"] == "arggen"]
        a["select_pooled"] = decompose(sel)
        a["select_by_size"] = {str(s): decompose([r for r in sel if r["size"] == s]) for s in sorted({r["size"] for r in sel})}
        a["select_by_stratum"] = {s: decompose([r for r in sel if r["stratum"] == s]) for s in ("flat", "structured")}
        a["arggen"] = decompose(ag) if ag else None
        a["design"] = design_effect(sel)
        res["arms"][arm] = a
    # power table for the paired design, using the measured design effect of the first arm
    d = res["arms"][arms[0]]["design"]
    res["power"] = []
    for delta in (0.03, 0.05, 0.08, 0.10):
        for disc in (0.10, 0.20):
            if disc <= delta ** 2:
                continue
            need = mcnemar_pairs_needed(delta, disc)
            res["power"].append({"delta_pp": 100 * delta, "discordant_share": disc,
                                 "independent_pairs_needed": math.ceil(need),
                                 "requests_needed_at_measured_design_effect": math.ceil(need * d["design_effect"]),
                                 "independent_intents_needed_if_1_request_each": math.ceil(need)})
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "ceiling.json"), "w") as f:
        json.dump(res, f, indent=2)
    _write_md(res, os.path.join(out_dir, "CEILING.md"))
    return res


def _row(label: str, d: dict) -> str:
    return (f"| {label} | {d['n']} | {d['success_pct']:.1f} | {d['malformed']} | {d['wrong_tool']} | {d['invalid_only']} | "
            f"{d['invalid_wrong']} | {d['valid_wrong']} | {d['cd_conservative_pct']:.1f} | {d['cd_upper_bound_pct']:.1f} |")


def _write_md(res: dict, path: str) -> None:
    H = ("| Slice | n | E2E % | malformed | wrong tool | invalid only | invalid + wrong value | valid, wrong value | "
         "CD conservative % | CD upper bound % |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    L = [f"# What constrained decoding could fix — run `{res['run']}`", "",
         "Computed from the stored outputs of the finished run. No model was called.", "",
         "- **CD conservative**: success if only the failures that already had every requested value right become successes.",
         "- **CD upper bound**: success if every malformed or schema-invalid output becomes a success. "
         "This assumes the engine is sound and complete and that forcing validity never changes a correct answer.",
         "- **valid, wrong value** outputs already satisfy the raw schema. A grammar cannot change them.", ""]
    for arm, a in res["arms"].items():
        L += [f"## Arm: {arm}", "", H, _row("select, all sizes", a["select_pooled"])]
        for s, d in a["select_by_size"].items():
            L.append(_row(f"select, {s} tools", d))
        for s, d in a["select_by_stratum"].items():
            L.append(_row(f"select, {s} targets", d))
        if a["arggen"]:
            L.append(_row("arggen (tool fixed)", a["arggen"]))
        d = a["design"]
        L += ["", f"Clustering: {d['clusters']} target tools, intra-tool correlation {d['icc']:.2f}, design effect {d['design_effect']:.1f}, "
              f"effective sample size {d['effective_n']:.0f} of {d['n']}. "
              f"{d['tools_with_any_failure']} tools have at least one failure; the 5 worst tools hold "
              f"{100 * d['share_of_failures_in_top5_tools']:.0f}% of all failures.", ""]
    L += ["## Power of a paired comparison", "",
          "Pairs needed for 80% power at two-sided 5% (McNemar, normal approximation). "
          "'Requests at measured design effect' inflates this by the clustering measured above, which applies if the "
          "extra requests reuse the same 50 target tools. New, independent target tools do not pay that penalty.", "",
          "| Difference to detect (pp) | Discordant share | Independent pairs | Requests at measured design effect |",
          "|---:|---:|---:|---:|"]
    for p in res["power"]:
        L.append(f"| {p['delta_pp']:.0f} | {p['discordant_share']:.2f} | {p['independent_pairs_needed']} | {p['requests_needed_at_measured_design_effect']} |")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="full-v2")
    ap.add_argument("--arms", nargs="+", default=["raw", "minified", "normalized"])
    ap.add_argument("--out")
    a = ap.parse_args()
    out = a.out or os.path.join(paths.ANALYSIS, f"ceiling-{a.run}")
    res = run(a.run, a.arms, out)
    for arm, v in res["arms"].items():
        d = v["select_pooled"]
        print(f"{arm:11s} E2E {d['success_pct']:.1f}  CD-conservative {d['cd_conservative_pct']:.1f}  CD-upper {d['cd_upper_bound_pct']:.1f}  valid-wrong {d['valid_wrong']}")
    print("written:", out)


if __name__ == "__main__":
    main()
