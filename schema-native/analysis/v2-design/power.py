"""Model-free planning from published outcomes; never imports a model or runner.

Run from any directory with Python 3.10+: python path/to/power.py [--check].
Only power.json and POWER.md beside this script can be written. Historical rows
are read verbatim, hash-checked, and never evaluated or relabelled.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import NormalDist, mean, variance


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = "schema-native/analysis/e0b-amendment3-v1/results.jsonl.gz"
SOURCE_RAW_SHA256 = "b439a463e53cae55fa38cd1a62399332602fd97b2d779e28195120e99c5baf90"


def final_select(rows, arm):
    """Exclude determinism controls and retry attempts, including same-arm rows."""
    result = {}
    for row in rows:
        if row["arm"] != arm or row["family"] != "select":
            continue
        if row["request_key"] != arm + "|" + row["unit_key"]:
            continue
        key = row["unit_key"]
        if key in result:
            raise ValueError("Duplicate final unit: " + key)
        if type(row["eval"]["e2e_success"]) is not bool:
            raise ValueError("Expected a stored Boolean outcome")
        result[key] = row
    return result


def paired_audit(rows, a, b):
    aa, bb = final_select(rows, a), final_select(rows, b)
    if not aa or aa.keys() != bb.keys():
        raise ValueError("Unmatched or empty final-unit sets")
    groups = defaultdict(list)
    differences = []
    for key in sorted(aa):
        x, y = aa[key], bb[key]
        if x["intent_id"] != y["intent_id"]:
            raise ValueError("Intent identity differs across arms")
        d = int(y["eval"]["e2e_success"]) - int(x["eval"]["e2e_success"])
        differences.append(d)
        groups[x["intent_id"]].append(d)
    if len(groups) < 2 or len(set(map(len, groups.values()))) != 1:
        raise ValueError("This planning audit requires balanced intent clusters")
    cluster_means = [mean(groups[k]) for k in sorted(groups)]
    row_var, cluster_var = variance(differences), variance(cluster_means)
    result = {
        "a": a, "b": b, "final_select_pairs": len(differences),
        "independent_intents": len(groups), "rows_per_intent": len(differences) // len(groups),
        "b_only_correct": differences.count(1), "a_only_correct": differences.count(-1),
        "both_correct": sum(aa[k]["eval"]["e2e_success"] and bb[k]["eval"]["e2e_success"] for k in aa),
        "both_wrong": sum(not aa[k]["eval"]["e2e_success"] and not bb[k]["eval"]["e2e_success"] for k in aa),
        "difference_pp": 100 * mean(cluster_means),
        "row_discordance": sum(d != 0 for d in differences) / len(differences),
        "intent_mean_distribution": {str(k): v for k, v in sorted(Counter(cluster_means).items())},
        "row_difference_variance": row_var, "intent_mean_variance": cluster_var,
        "descriptive_design_effect": len(differences) * cluster_var / (len(groups) * row_var) if row_var else None,
    }
    return result, cluster_means


def paired_n(delta, discordance, alpha=0.05, power=0.8):
    """Normal approximation for independent binary paired outcomes.

    D is -1, 0, +1; E[D]=delta, P(D!=0)=q, Var[D]=q-delta**2.
    n=ceil((z_(1-alpha/2)*sqrt(q)+z_power*sqrt(q-delta**2))**2/delta**2).
    This is a planning approximation, not exact McNemar or clustered power.
    """
    if not (0 < delta <= discordance <= 1 and 0 < alpha < 1 and 0.5 < power < 1):
        raise ValueError("Invalid paired planning assumptions")
    z = NormalDist().inv_cdf(1 - alpha / 2)
    zp = NormalDist().inv_cdf(power)
    return math.ceil(((z * math.sqrt(discordance) + zp * math.sqrt(discordance - delta**2)) / delta)**2)


def observed_cluster_power(values, n, alpha, repeats=2000, seed=20261125):
    """Conditional simulation: resample whole intent means, normal z decision.

    Retains observed within-intent dependence. Does not model unseen families,
    shifts in difficulty, training gains, or the later hierarchical test.
    """
    if n < 2 or len(values) < 2:
        raise ValueError("At least two intents required")
    rng = random.Random(seed)
    critical = NormalDist().inv_cdf(1 - alpha / 2)
    detected = 0
    for _ in range(repeats):
        sample = rng.choices(values, k=n)
        avg, var = mean(sample), variance(sample)
        detected += avg > 0 and var > 0 and avg / math.sqrt(var / n) > critical
    estimate = detected / repeats
    return {"n_intents": n, "alpha": alpha, "repeats": repeats, "seed": seed,
            "conditional_power": estimate,
            "monte_carlo_se": math.sqrt(estimate * (1 - estimate) / repeats)}


def build_report():
    compressed = (REPO / SOURCE).read_bytes()
    raw = gzip.decompress(compressed)
    if hashlib.sha256(raw).hexdigest() != SOURCE_RAW_SHA256:
        raise ValueError("Published source rows changed")
    rows = [json.loads(line) for line in raw.splitlines()]
    audits, simulations = [], []
    for a, b in (("C1", "C2"), ("F0", "V")):
        audit, values = paired_audit(rows, a, b)
        if (audit["final_select_pairs"], audit["independent_intents"], audit["rows_per_intent"]) != (200, 50, 4):
            raise ValueError("Unexpected published cluster structure")
        audits.append(audit)
        simulations.append({"contrast": b + " - " + a,
                            "scenarios": [observed_cluster_power(values, n, alpha)
                                          for alpha in (0.05, 0.025) for n in (25, 50, 100, 250)]})
    scenarios = [{"effect_pp": 100 * delta, "discordance": q, "alpha": alpha,
                  "target_power": 0.8, "independent_binary_pairs_approx": paired_n(delta, q, alpha)}
                 for alpha in (0.05, 0.025) for delta in (0.03, 0.05, 0.08)
                 for q in (0.05, 0.1, 0.19, 0.2, 0.3) if delta <= q]
    return {"status": "DESIGN ONLY; NOT A POWER GUARANTEE OR NEW MODEL RESULT",
            "planning_date": "2026-11-25", "source": SOURCE,
            "source_gzip_sha256": hashlib.sha256(compressed).hexdigest(),
            "source_uncompressed_sha256": SOURCE_RAW_SHA256,
            "stored_records": len(rows), "historical_scores_used_verbatim": True,
            "historical_metric": "Stored eval.e2e_success, not a re-evaluation under the proposed v2 strict contract",
            "paired_audits": audits, "normal_approximation_scenarios": scenarios,
            "whole_intent_conditional_simulations": simulations,
            "limits": ["Only 50 observed independent intents; no family-level sampling frame.",
                       "The order contrast cannot predict a semantic training effect.",
                       "Row discordance is not independent-intent discordance.",
                       "Simulations use observed intent effects and a normal z rule, not the proposed hierarchical analysis.",
                       "Only four pilot intents show V gains; resampling cannot create unseen regressions and may be optimistic. Do not size v2 from that simulation.",
                       "800 test intents is a provisional authoring target, not guaranteed power.",
                       "A 5-point effect scenario does not power a 5-point threshold at 80% if the true effect is exactly 5 points."]}


def markdown(report):
    lines = ["# v2 sample-size planning", "", "**Design only, 2026-11-25. No inference, training or rescoring.**", "",
             "Reproduce: `python schema-native/analysis/v2-design/power.py --check`.", "",
             "## Published-row audit", "",
             "Each contrast has 200 select rows but only 50 intent clusters, with four rows per intent.", "",
             "| Contrast | B-only correct | A-only correct | Difference | Descriptive design effect |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for a in report["paired_audits"]:
        lines.append(f"| {a['b']} − {a['a']} | {a['b_only_correct']} | {a['a_only_correct']} | {a['difference_pp']:.1f} pp | {a['descriptive_design_effect']:.3f} |")
    lines += ["", "Design effect compares variance of the equal-weight intent mean with a naive row-independent mean; it is descriptive, not an inflation factor transferable to v2.", "",
              "## Independent-pair sensitivity: a true 5-point improvement", "",
              "Two-sided normal approximation, 80% target power against zero; q is the assumed fraction of discordant independent binary pairs.",
              "Alpha .025 is a conservative first-step threshold for two Holm tests, not a change to historical multiplicity.", "",
              "| Assumed q | n at alpha .05 | n at alpha .025 |", "| --- | ---: | ---: |"]
    for q in (0.05, 0.1, 0.19, 0.2, 0.3):
        lines.append(f"| {q:.2f} | {paired_n(.05, q, .05)} | {paired_n(.05, q, .025)} |")
    lines += ["", "For D∈{−1,0,+1}, E[D]=δ and Var[D]=q−δ²:", "",
              "`n ≈ ceil((z_(1−alpha/2) sqrt(q) + z_.8 sqrt(q−δ²))² / δ²)`.", "",
              "The JSON also contains 3/8-point scenarios and whole-intent resampling simulations. Those simulations preserve the observed four-row dependence by sampling intent means; they estimate detecting the observed effect under a normal z rule. They do not predict a future training gain or validate the planned family/intent bootstrap.", "",
              "## Planning consequence", "",
              "The 250 unused tools are an authoring seed, not a sufficient independent test-set guarantee. Propose 800 locked-test intents plus 200 development intents, subject to provenance and family audits. At q=.20, a single 5-point binary-pair contrast needs approximately 626 independent pairs; a conservative two-test threshold needs 758. At q=.30 even 800 may be insufficient (940/1,139).", "",
              "Do not multiply paraphrases, two catalog sizes, pair members, or renamed schemas into the independent n. Recompute power using development-set cluster sizes and variance before freezing any campaign. No current dataset or campaign is launch-ready.", "", "## Limits", ""]
    lines += ["- " + s for s in report["limits"]]
    lines += ["", "Source uncompressed SHA-256: `" + SOURCE_RAW_SHA256 + "`.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare generated artifacts without writing")
    args = parser.parse_args()
    report = build_report()
    outputs = {"power.json": json.dumps(report, indent=2, allow_nan=False) + "\n", "POWER.md": markdown(report)}
    for name, content in outputs.items():
        path = HERE / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise SystemExit("Generated artifact differs: " + name)
        else:
            path.write_text(content)
    print("PASS: published-row audit and deterministic planning artifacts" if args.check else "Wrote power.json and POWER.md; model-free planning only")


if __name__ == "__main__":
    main()
