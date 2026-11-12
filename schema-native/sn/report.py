"""Tables and paired statistics for a schema-native run.

Reuses the experiment's statistics (exact McNemar on discordant pairs, cluster bootstrap over
catalog replicates, Holm correction) from ``experiment/src/analyze.py`` without modifying it.

Model errors and engine errors are reported in separate columns. ``E2E`` counts an engine refusal
as a failure of the SYSTEM; ``E2E (engine ok)`` is computed only on requests the engine accepted.

usage: python -m sn.report --run <run_id>
Output: analysis/<run_id>/{REPORT.md, report.json}
"""
from __future__ import annotations

import argparse
import collections
import json
import os

from . import ceiling
from . import paths
import analyze as exp_analyze  # type: ignore  # noqa: E402


def pct(rows, key):
    return 100 * sum(bool(key(r)) for r in rows) / len(rows) if rows else float("nan")


def quantile(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    i = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
    return xs[i]


def cell(rows: list[dict]) -> dict:
    ok_engine = [r for r in rows if not r.get("engine_error")]
    lat = [r["wall_latency_ms"] for r in rows if r["http_status"] == 200]
    d = ceiling.decompose(rows)
    return {"n": len(rows), "engine_errors": len(rows) - len(ok_engine),
            "tool": pct(rows, lambda r: r["eval"]["tool_correct"]),
            "schema_valid": pct(rows, lambda r: r["eval"]["schema_valid"]),
            "semantic": pct(rows, lambda r: r["eval"]["semantic_correct"]),
            "arg_em": pct(rows, lambda r: r["eval"]["arg_exact_match"]),
            "field_acc": 100 * sum(r["eval"]["field_acc"] for r in rows) / len(rows) if rows else float("nan"),
            "e2e": pct(rows, lambda r: r["eval"]["e2e_success"]),
            "e2e_strict": pct(rows, lambda r: r["eval"]["e2e_strict"]),
            "e2e_engine_ok": pct(ok_engine, lambda r: r["eval"]["e2e_success"]),
            "classes": {k: d[k] for k in ceiling.CLASSES},
            "in_tokens": sum(r["usage"].get("prompt_tokens", 0) for r in rows) / len(rows) if rows else 0,
            "out_tokens": sum(r["usage"].get("completion_tokens", 0) for r in rows) / len(rows) if rows else 0,
            "lat_p50": quantile(lat, 0.5), "lat_p95": quantile(lat, 0.95),
            "lat_p99": quantile(lat, 0.99) if len(lat) >= 200 else None}


def run(run_id: str) -> dict:
    rdir = os.path.join(paths.RUNS, run_id)
    rows = paths.jsonl(os.path.join(rdir, "results.jsonl"))
    man = json.load(open(os.path.join(rdir, "manifest.json")))
    arms = list(man["run_config"]["arms"])
    res = {"run": run_id, "n": len(rows), "cells": [], "comparisons": []}
    for fam in ("select", "arggen"):
        fr = [r for r in rows if r["family"] == fam]
        for size in sorted({r["size"] for r in fr}):
            for arm in arms:
                rs = [r for r in fr if r["arm"] == arm and r["size"] == size]
                if rs:
                    res["cells"].append({"family": fam, "size": size, "arm": arm, **cell(rs)})
    ps = []
    for name, a, b in man["run_config"].get("comparisons", []):
        for fam in ("select", "arggen"):
            ra = [r for r in rows if r["arm"] == a and r["family"] == fam]
            rb = [r for r in rows if r["arm"] == b and r["family"] == fam]
            st = exp_analyze.paired(ra, rb, lambda r: r["eval"]["e2e_success"]) if ra and rb else None
            if st:
                res["comparisons"].append({"name": name, "family": fam, "a": a, "b": b, **st})
                ps.append(st["mcnemar_exact_p"])
    for c, adj in zip(res["comparisons"], exp_analyze.holm(ps) if ps else []):
        c["p_holm"] = adj
    out = os.path.join(paths.ANALYSIS, run_id)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report.json"), "w") as f:
        json.dump(res, f, indent=2)
    L = [f"# Report — run `{run_id}`", "", f"Requests: {res['n']}. Evaluation is against the raw schema. "
         "Engine refusals are counted separately from model errors.", "",
         "| Family | Tools | Arm | n | Tool % | Schema valid % | Semantic % | E2E % | E2E % (engine ok) | Engine errors | "
         "malformed | wrong tool | invalid only | invalid+wrong | valid, wrong | In tok | Out tok | p50 ms | p95 ms |",
         "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c in res["cells"]:
        k = c["classes"]
        L.append(f"| {c['family']} | {c['size']} | {c['arm']} | {c['n']} | {c['tool']:.1f} | {c['schema_valid']:.1f} | {c['semantic']:.1f} | "
                 f"{c['e2e']:.1f} | {c['e2e_engine_ok']:.1f} | {c['engine_errors']} | {k['malformed']} | {k['wrong_tool']} | "
                 f"{k['invalid_only']} | {k['invalid_wrong']} | {k['valid_wrong']} | {c['in_tokens']:.0f} | {c['out_tokens']:.0f} | "
                 f"{(c['lat_p50'] or 0):.0f} | {(c['lat_p95'] or 0):.0f} |")
    if res["comparisons"]:
        L += ["", "## Paired comparisons (B − A, E2E)", "",
              "| Comparison | Family | A | B | pairs | A % | B % | Δ pp [95% CI] | A-only / B-only | p (exact) | p (Holm) |",
              "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for c in res["comparisons"]:
            L.append(f"| {c['name']} | {c['family']} | {c['a']} | {c['b']} | {c['n_pairs']} | {100 * c['acc_a']:.1f} | {100 * c['acc_b']:.1f} | "
                     f"{c['diff_pp']:+.1f} [{c['ci95_diff_pp'][0]:+.1f}, {c['ci95_diff_pp'][1]:+.1f}] | "
                     f"{c['discordant_a_only']} / {c['discordant_b_only']} | {c['mcnemar_exact_p']:.3g} | {c['p_holm']:.3g} |")
    with open(os.path.join(out, "REPORT.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    res = run(a.run)
    print(f"{len(res['cells'])} cells, {len(res['comparisons'])} comparisons -> analysis/{a.run}/REPORT.md")


if __name__ == "__main__":
    main()
