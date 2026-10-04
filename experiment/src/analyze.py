"""Analysis: tables, paired statistics, failure taxonomy and plots for one main run
(+ optional uncached latency run).

usage: python src/analyze.py --run runs/<main_run_id> [--latency-run runs/<latency_run_id>] [--out analysis/<name>]
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import random
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_utils as su  # noqa: E402

ARMS = ["raw", "minified", "normalized", "tscg", "tscg_info"]
LABEL = {"raw": "Raw", "minified": "Raw-minified", "normalized": "Normalized", "tscg": "TSCG", "tscg_info": "TSCG-info JSON"}
COLOR = {"raw": "#2a78d6", "minified": "#eb6834", "normalized": "#1baf7a", "tscg": "#eda100", "tscg_info": "#e87ba4"}
MARKER = {"raw": "o", "minified": "s", "normalized": "^", "tscg": "D", "tscg_info": "v"}
FAILURES = ["wrong tool", "multiple-tool confusion", "correct tool, wrong argument", "missing required argument",
            "invalid argument type", "invalid enum/value", "hallucinated field", "ignored schema constraint",
            "context-length failure", "malformed output", "execution failure", "semantic/task failure", "other"]
N_BOOT = 5000


def load(run):
    return [json.loads(l) for l in open(os.path.join(run, "results.jsonl"))]


def boot_ci_mean(rows, key, n=N_BOOT, seed=0):
    """Cluster bootstrap over catalog replicates (tasks within a replicate are correlated)."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r["replicate"]].append(key(r))
    reps = sorted(by)
    rng = random.Random(seed)
    est = []
    for _ in range(n):
        vals = []
        for rep in (rng.choice(reps) for _ in reps):
            vals += by[rep]
        est.append(sum(vals) / len(vals))
    est.sort()
    return est[int(0.025 * n)], est[int(0.975 * n) - 1]


def paired(rows_a, rows_b, key):
    """Pair by (catalog/single, task). Returns stats for B - A."""
    ka = {(r["catalog_id"], r["task_id"]): r for r in rows_a}
    kb = {(r["catalog_id"], r["task_id"]): r for r in rows_b}
    keys = sorted(set(ka) & set(kb))
    a = np.array([key(ka[k]) for k in keys], dtype=int)
    b = np.array([key(kb[k]) for k in keys], dtype=int)
    n = len(keys)
    if n == 0:
        return None
    n10 = int(((a == 1) & (b == 0)).sum())  # A right, B wrong
    n01 = int(((a == 0) & (b == 1)).sum())  # A wrong, B right
    p = stats.binomtest(n01, n01 + n10, 0.5).pvalue if n01 + n10 else 1.0
    pa, pb = a.mean(), b.mean()
    # odds ratio of discordant pairs with Haldane correction + Wald CI on log scale
    orr = (n01 + 0.5) / (n10 + 0.5)
    se = math.sqrt(1 / (n01 + 0.5) + 1 / (n10 + 0.5))
    # cluster bootstrap CI of the paired difference (resample replicates)
    reps = collections.defaultdict(list)
    for k, x, y in zip(keys, a, b):
        reps[ka[k]["replicate"]].append(y - x)
    rl = sorted(reps)
    rng = random.Random(1)
    diffs = []
    for _ in range(N_BOOT):
        v = []
        for rep in (rng.choice(rl) for _ in rl):
            v += reps[rep]
        diffs.append(sum(v) / len(v))
    diffs.sort()
    return {"n_pairs": n, "acc_a": pa, "acc_b": pb, "diff_pp": 100 * (pb - pa),
            "rel_improvement_pct": (100 * (pb - pa) / pa) if pa > 0 else None,
            "ci95_diff_pp": [100 * diffs[int(0.025 * N_BOOT)], 100 * diffs[int(0.975 * N_BOOT) - 1]],
            "discordant_a_only": n10, "discordant_b_only": n01, "mcnemar_exact_p": p,
            "discordant_odds_ratio": orr, "or_ci95": [math.exp(math.log(orr) - 1.96 * se), math.exp(math.log(orr) + 1.96 * se)]}


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def fmt(x, pct=True):
    return "" if x is None else (f"{100 * x:.1f}" if pct else f"{x:.0f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--latency-run")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = load(a.run)
    run_id = os.path.basename(a.run.rstrip("/"))
    out = a.out or os.path.join(su.EXP, "analysis", run_id)
    os.makedirs(os.path.join(out, "figures"), exist_ok=True)
    lat = load(a.latency_run) if a.latency_run else []
    sel = [r for r in rows if r["family"] == "select"]
    arg = [r for r in rows if r["family"] == "arggen"]
    sizes = sorted({r["size"] for r in sel})
    E = lambda k: (lambda r: int(bool(r["eval"][k])))  # noqa: E731
    res = {"run_id": run_id, "n_requests": len(rows), "sizes": sizes, "arms": ARMS}

    # ---------------- main table (selection + E2E family)
    table = []
    for k in sizes:
        for arm in ARMS:
            g = [r for r in sel if r["size"] == k and r["arm"] == arm]
            if not g:
                continue
            l = [r for r in lat if r["size"] == k and r["arm"] == arm and r["http_status"] == 200]
            row = {"tools": k, "arm": arm, "n": len(g), "n_replicates": len({r["replicate"] for r in g}),
                   "selection": np.mean([E("tool_correct")(r) for r in g]),
                   "arg_em": np.mean([E("arg_exact_match")(r) for r in g]),
                   "field_acc": np.mean([r["eval"]["field_acc"] for r in g]),
                   "schema_valid": np.mean([E("schema_valid")(r) for r in g]),
                   "json_valid": np.mean([E("json_valid")(r) for r in g]),
                   "e2e": np.mean([E("e2e_success")(r) for r in g]),
                   "e2e_strict": np.mean([int(bool(r["eval"].get("e2e_strict"))) for r in g]),
                   "e2e_ci95": boot_ci_mean(g, E("e2e_success")),
                   "selection_ci95": boot_ci_mean(g, E("tool_correct")),
                   "input_tokens": np.mean([r["usage"].get("prompt_tokens", np.nan) for r in g]),
                   "output_tokens": np.mean([r["usage"].get("completion_tokens", np.nan) for r in g]),
                   "latency_ms_cached": np.median([r["wall_latency_ms"] for r in g]),
                   "latency_ms_uncached": float(np.median([r["wall_latency_ms"] for r in l])) if l else None,
                   "context_failures": sum(r["eval"]["failure_primary"] == "context-length failure" for r in g),
                   "truncated": sum(bool(r["truncated"]) for r in g)}
            table.append(row)
    res["main_table"] = table

    # ---------------- argument-generation family (tool fixed)
    argt = []
    for arm in ARMS:
        g = [r for r in arg if r["arm"] == arm]
        if g:
            argt.append({"arm": arm, "n": len(g), "json_valid": np.mean([E("json_valid")(r) for r in g]),
                         "tool_echo_correct": np.mean([E("tool_correct")(r) for r in g]),
                         "arg_em": np.mean([E("arg_exact_match")(r) for r in g]),
                         "field_acc": np.mean([r["eval"]["field_acc"] for r in g]),
                         "schema_valid": np.mean([E("schema_valid")(r) for r in g]),
                         "semantic_correct": np.mean([E("semantic_correct")(r) for r in g]),
                         "e2e": np.mean([E("e2e_success")(r) for r in g]),
                         "e2e_strict": np.mean([int(bool(r["eval"].get("e2e_strict"))) for r in g]),
                         "input_tokens": np.mean([r["usage"].get("prompt_tokens", np.nan) for r in g])})
    res["arggen_table"] = argt

    # ---------------- paired comparisons
    comps = []
    def add(name, fam_rows, aa, bb, metric, filt=lambda r: True, primary=False):
        A = [r for r in fam_rows if r["arm"] == aa and filt(r)]
        B = [r for r in fam_rows if r["arm"] == bb and filt(r)]
        s = paired(A, B, E(metric))
        if s:
            comps.append(dict(s, name=name, a=aa, b=bb, metric=metric, primary=primary))
    add("PRIMARY: TSCG vs Raw, E2E, pooled sizes", sel, "raw", "tscg", "e2e_success", primary=True)
    for m in ("tool_correct", "arg_exact_match", "schema_valid"):
        add(f"TSCG vs Raw, {m}, pooled", sel, "raw", "tscg", m)
    for arm in ("minified", "normalized", "tscg_info"):
        add(f"{LABEL[arm]} vs Raw, E2E, pooled", sel, "raw", arm, "e2e_success")
    add("TSCG vs TSCG-info JSON (format at fixed information), E2E, pooled", sel, "tscg_info", "tscg", "e2e_success")
    add("TSCG vs Raw-minified, E2E, pooled", sel, "minified", "tscg", "e2e_success")
    add("TSCG vs Raw, E2E-strict, pooled", sel, "raw", "tscg", "e2e_strict")
    for k in sizes:
        add(f"TSCG vs Raw, E2E, size {k}", sel, "raw", "tscg", "e2e_success", lambda r, k=k: r["size"] == k)
        add(f"TSCG vs Raw, selection, size {k}", sel, "raw", "tscg", "tool_correct", lambda r, k=k: r["size"] == k)
    for st in ("flat", "structured"):
        add(f"TSCG vs Raw, E2E, {st} targets", sel, "raw", "tscg", "e2e_success", lambda r, st=st: r["stratum"] == st)
        add(f"TSCG vs TSCG-info, E2E, {st} targets", sel, "tscg_info", "tscg", "e2e_success", lambda r, st=st: r["stratum"] == st)
    add("ARGGEN: TSCG vs Raw, E2E (tool fixed)", arg, "raw", "tscg", "e2e_success")
    add("ARGGEN: TSCG vs Raw, arg EM (tool fixed)", arg, "raw", "tscg", "arg_exact_match")
    add("ARGGEN: TSCG vs TSCG-info, E2E (tool fixed)", arg, "tscg_info", "tscg", "e2e_success")
    sec = [c for c in comps if not c["primary"]]
    for c, p in zip(sec, holm([c["mcnemar_exact_p"] for c in sec])):
        c["holm_p"] = p
    for c in comps:
        if c["primary"]:
            c["holm_p"] = c["mcnemar_exact_p"]
    res["paired_comparisons"] = comps

    # ---------------- degradation point: first size significantly below size-5 (same tasks), per arm
    deg = {}
    for arm in ARMS:
        base = [r for r in sel if r["arm"] == arm and r["size"] == sizes[0]]
        ps, ks, ds = [], [], []
        for k in sizes[1:]:
            other = [dict(r, catalog_id="X") for r in sel if r["arm"] == arm and r["size"] == k]
            s = paired([dict(r, catalog_id="X") for r in base], other, E("e2e_success"))
            if s:
                ps.append(s["mcnemar_exact_p"]); ks.append(k); ds.append(s["diff_pp"])
        adj = holm(ps) if ps else []
        first = next((k for k, d, p in zip(ks, ds, adj) if d < 0 and p < 0.05), None)
        deg[arm] = {"first_significant_drop_size": first,
                    "per_size": [{"size": k, "diff_pp_vs_smallest": d, "holm_p": p} for k, d, p in zip(ks, ds, adj)]}
    res["degradation"] = deg

    # ---------------- token covariate model (is the effect explained by input length?)
    try:
        import statsmodels.api as sm
        X, y, groups = [], [], []
        for r in sel:
            if not r["usage"].get("prompt_tokens"):
                continue
            X.append([1.0, math.log(r["usage"]["prompt_tokens"])] + [1.0 if r["arm"] == arm else 0.0 for arm in ARMS[1:]])
            y.append(E("e2e_success")(r)); groups.append(r["intent_id"])
        g_codes = {g: i for i, g in enumerate(sorted(set(groups)))}
        m = sm.GLM(np.array(y), np.array(X), family=sm.families.Binomial()).fit(
            cov_type="cluster", cov_kwds={"groups": np.array([g_codes[g] for g in groups])})
        names = ["const", "log_input_tokens"] + [f"arm[{x}]" for x in ARMS[1:]]
        res["token_covariate_glm"] = {"formula": "E2E ~ log(input tokens) + arm (ref=raw); logit; cluster-robust SE by intent",
                                      "coef": dict(zip(names, map(float, m.params))),
                                      "se": dict(zip(names, map(float, m.bse))),
                                      "p": dict(zip(names, map(float, m.pvalues)))}
        if np.linalg.matrix_rank(np.array(X)) < len(names):
            res["token_covariate_glm"]["warning"] = "design matrix rank-deficient"
    except Exception as e:  # pragma: no cover
        res["token_covariate_glm"] = {"error": repr(e)}

    # ---------------- failure taxonomy
    fail = collections.defaultdict(collections.Counter)
    fail_sec = collections.defaultdict(collections.Counter)
    for r in sel:
        f = r["eval"]["failure_primary"]
        if f:
            fail[(r["arm"], r["size"])][f] += 1
            fail[(r["arm"], "all")][f] += 1
            for s in r["eval"]["failure_secondary"]:
                fail_sec[(r["arm"], "all")][s] += 1
    res["failures_primary"] = {f"{a}|{k}": dict(v) for (a, k), v in fail.items()}
    res["failures_secondary"] = {f"{a}|{k}": dict(v) for (a, k), v in fail_sec.items()}
    afail = collections.defaultdict(collections.Counter)
    for r in arg:
        if r["eval"]["failure_primary"]:
            afail[r["arm"]][r["eval"]["failure_primary"]] += 1
    res["arggen_failures_primary"] = {k: dict(v) for k, v in afail.items()}

    json.dump(res, open(os.path.join(out, "results.json"), "w"), indent=1, default=float)
    write_markdown(res, out)
    plots(res, sel, out)
    print(open(os.path.join(out, "RESULTS.md")).read()[:6000])


def write_markdown(res, out):
    L = [f"# Results — {res['run_id']}", "", f"Requests analysed: {res['n_requests']}", "",
         "## Selection + arguments + end-to-end (full catalog shown)", "",
         "Proportions in %. E2E 95% CI = cluster bootstrap over catalog replicates. Latency = median wall-clock; "
         "'cached' uses llama.cpp prompt-prefix caching (catalog shared across a cell's tasks), 'uncached' from the latency sub-run.", "",
         "| Tools | Representation | n | Selection | Arg EM | Field Acc | Schema valid | E2E [95% CI] | E2E-strict | Input tokens | Output tokens | Latency cached (ms) | Latency uncached (ms) | Ctx fail |",
         "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in res["main_table"]:
        unc = '' if r['latency_ms_uncached'] is None else f"{r['latency_ms_uncached']:.0f}"
        L.append(f"| {r['tools']} | {LABEL[r['arm']]} | {r['n']} | {fmt(r['selection'])} | {fmt(r['arg_em'])} | {fmt(r['field_acc'])} | "
                 f"{fmt(r['schema_valid'])} | {fmt(r['e2e'])} [{fmt(r['e2e_ci95'][0])}, {fmt(r['e2e_ci95'][1])}] | {fmt(r['e2e_strict'])} | "
                 f"{r['input_tokens']:.0f} | {r['output_tokens']:.1f} | {r['latency_ms_cached']:.0f} | "
                 f"{unc} | {r['context_failures']} |")
    L += ["", "## Argument generation (tool fixed; only the gold tool shown)", "",
          "| Representation | n | JSON valid | Arg EM | Field Acc | Schema valid | Semantic correct | E2E | E2E-strict | Input tokens |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in res["arggen_table"]:
        L.append(f"| {LABEL[r['arm']]} | {r['n']} | {fmt(r['json_valid'])} | {fmt(r['arg_em'])} | {fmt(r['field_acc'])} | "
                 f"{fmt(r['schema_valid'])} | {fmt(r['semantic_correct'])} | {fmt(r['e2e'])} | {fmt(r['e2e_strict'])} | {r['input_tokens']:.0f} |")
    L += ["", "## Paired comparisons (B − A)", "",
          "Exact McNemar on discordant pairs; Holm-adjusted across all secondary comparisons (primary reported unadjusted).", "",
          "| Comparison | A | B | n pairs | A % | B % | Δ pp [95% CI] | rel. % | A-only / B-only | p (exact) | p (Holm) | OR disc. [95% CI] |",
          "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c in res["paired_comparisons"]:
        rel = "" if c["rel_improvement_pct"] is None else f"{c['rel_improvement_pct']:.1f}"
        L.append(f"| {c['name']} | {LABEL[c['a']]} | {LABEL[c['b']]} | {c['n_pairs']} | {100 * c['acc_a']:.1f} | {100 * c['acc_b']:.1f} | "
                 f"{c['diff_pp']:+.1f} [{c['ci95_diff_pp'][0]:+.1f}, {c['ci95_diff_pp'][1]:+.1f}] | {rel} | "
                 f"{c['discordant_a_only']} / {c['discordant_b_only']} | {c['mcnemar_exact_p']:.3g} | {c['holm_p']:.3g} | "
                 f"{c['discordant_odds_ratio']:.2f} [{c['or_ci95'][0]:.2f}, {c['or_ci95'][1]:.2f}] |")
    L += ["", "## Degradation vs smallest catalog (same tasks, E2E, Holm within arm)", "",
          "| Representation | first size with significant drop | per-size Δ pp (Holm p) |", "|---|---:|---|"]
    for arm, d in res["degradation"].items():
        L.append(f"| {LABEL[arm]} | {d['first_significant_drop_size'] or 'none'} | " +
                 "; ".join(f"{x['size']}: {x['diff_pp_vs_smallest']:+.1f} ({x['holm_p']:.2g})" for x in d["per_size"]) + " |")
    g = res.get("token_covariate_glm", {})
    if "coef" in g:
        L += ["", "## Token-count covariate model", "", g["formula"], "", "| term | coef | SE | p |", "|---|---:|---:|---:|"]
        for k in g["coef"]:
            L.append(f"| {k} | {g['coef'][k]:+.3f} | {g['se'][k]:.3f} | {g['p'][k]:.3g} |")
    L += ["", "## Primary failure categories (selection family, all sizes)", "",
          "| Failure | " + " | ".join(LABEL[a] for a in ARMS) + " |", "|---|" + "---:|" * len(ARMS)]
    for f in FAILURES:
        L.append(f"| {f} | " + " | ".join(str(res["failures_primary"].get(f"{a}|all", {}).get(f, 0)) for a in ARMS) + " |")
    open(os.path.join(out, "RESULTS.md"), "w").write("\n".join(L) + "\n")


def plots(res, sel, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"axes.axisbelow": True, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                         "ytick.color": "#52514e", "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6,
                         "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "legend.frameon": False})
    T = res["main_table"]
    sizes = res["sizes"]

    def line_plot(metric, ci_key, ylabel, fname, title):
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        for i, arm in enumerate(ARMS):
            rr = [r for r in T if r["arm"] == arm]
            if not rr:
                continue
            x = [r["tools"] * (1 + (i - 2) * 0.03) for r in rr]  # small dodge so CIs don't overlap exactly
            y = [100 * r[metric] for r in rr]
            ax.plot(x, y, color=COLOR[arm], lw=2, marker=MARKER[arm], ms=7, label=LABEL[arm],
                    markeredgecolor="#fcfcfb", markeredgewidth=1.5)
            if ci_key:
                lo = [100 * r[ci_key][0] for r in rr]
                hi = [100 * r[ci_key][1] for r in rr]
                ax.vlines(x, lo, hi, color=COLOR[arm], lw=1.2, alpha=0.8)
        ax.set_xscale("log")
        ax.set_xticks(sizes)
        ax.set_xticklabels([str(s) for s in sizes])
        ax.set_ylim(0, 100)
        ax.set_xlabel("Tools in catalog (log scale)")
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left", fontsize=11)
        ax.legend(loc="lower left", fontsize=8.5)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "figures", fname), dpi=160)
        plt.close(fig)

    line_plot("selection", "selection_ci95", "Tool-selection accuracy (%)", "1_accuracy_vs_tools.png",
              "Tool selection vs catalog size (95% cluster-bootstrap CI)")
    line_plot("e2e", "e2e_ci95", "End-to-end success (%)", "5_e2e_vs_tools.png",
              "End-to-end success vs catalog size (95% cluster-bootstrap CI)")

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for arm in ARMS:
        rr = [r for r in T if r["arm"] == arm]
        ax.plot([r["tools"] for r in rr], [r["input_tokens"] for r in rr], color=COLOR[arm], lw=2, marker=MARKER[arm],
                ms=7, label=LABEL[arm], markeredgecolor="#fcfcfb", markeredgewidth=1.5)
    ax.axhline(32768, color="#52514e", lw=1, ls="--")
    ax.text(sizes[0], 32768 * 1.08, "model context 32,768", fontsize=8, color="#52514e")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks(sizes); ax.set_xticklabels([str(s) for s in sizes])
    ax.set_xlabel("Tools in catalog (log scale)"); ax.set_ylabel("Mean input tokens per request (log scale)")
    ax.set_title("Input tokens vs catalog size (model tokenizer)", loc="left", fontsize=11)
    ax.legend(loc="upper left", fontsize=8.5)
    fig.tight_layout(); fig.savefig(os.path.join(out, "figures", "2_input_tokens_vs_tools.png"), dpi=160); plt.close(fig)

    # accuracy vs input tokens: one point per (catalog, arm) cell
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    cell = collections.defaultdict(list)
    for r in sel:
        cell[(r["catalog_id"], r["arm"])].append(r)
    for arm in ARMS:
        pts = [(np.mean([x["usage"].get("prompt_tokens", np.nan) for x in v]), 100 * np.mean([x["eval"]["e2e_success"] for x in v]))
               for (c, a), v in cell.items() if a == arm]
        if pts:
            xs, ys = zip(*pts)
            ax.scatter(xs, ys, s=36, color=COLOR[arm], marker=MARKER[arm], label=LABEL[arm], edgecolor="#fcfcfb", linewidth=1, alpha=0.85)
    ax.set_xscale("log"); ax.set_ylim(-3, 103)
    ax.set_xlabel("Mean input tokens in cell (log scale)"); ax.set_ylabel("End-to-end success in cell (%)")
    ax.set_title("E2E vs input tokens (one point per catalog × representation)", loc="left", fontsize=11)
    ax.legend(loc="lower left", fontsize=8.5)
    fig.tight_layout(); fig.savefig(os.path.join(out, "figures", "3_accuracy_vs_input_tokens.png"), dpi=160); plt.close(fig)

    # failure distribution: horizontal stacked bars per arm (all sizes), share of tasks
    present = [f for f in FAILURES if any(res["failures_primary"].get(f"{a}|all", {}).get(f, 0) for a in ARMS)]
    seq = ["#0d366b", "#1c5cab", "#2a78d6", "#5fa0e8", "#9cc6f2", "#e34948", "#eb6834", "#eda100", "#4a3aa7", "#9085e9", "#52514e", "#a3a29c", "#c3c2b7"]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    n_per_arm = {a: sum(1 for r in sel if r["arm"] == a) for a in ARMS}
    for yi, arm in enumerate(ARMS):
        left = 0.0
        for fi, f in enumerate(present):
            v = 100 * res["failures_primary"].get(f"{arm}|all", {}).get(f, 0) / max(1, n_per_arm[arm])
            if v:
                ax.barh(yi, v, left=left, color=seq[fi % len(seq)], edgecolor="#fcfcfb", linewidth=2, height=0.6,
                        label=f if yi == 0 or f not in ax.get_legend_handles_labels()[1] else None)
                left += v
    ax.set_yticks(range(len(ARMS))); ax.set_yticklabels([LABEL[a] for a in ARMS]); ax.invert_yaxis()
    ax.set_xlabel("Share of selection-family requests (%) by primary failure")
    ax.set_title("Failure-type distribution (all catalog sizes)", loc="left", fontsize=11)
    h, l = ax.get_legend_handles_labels()
    ax.legend(h, l, loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8)
    ax.grid(axis="y", visible=False)
    fig.tight_layout(); fig.savefig(os.path.join(out, "figures", "4_failure_distribution.png"), dpi=160); plt.close(fig)


if __name__ == "__main__":
    main()
