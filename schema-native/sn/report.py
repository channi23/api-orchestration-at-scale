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
import re
from .lookalike import key_flags

from . import ceiling
from . import paths, provenance
import analyze as exp_analyze  # type: ignore  # noqa: E402


def pct(rows, key):
    return 100 * sum(bool(key(r)) for r in rows) / len(rows) if rows else None


def quantile(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    i = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
    return xs[i]


def cell(rows: list[dict]) -> dict:
    ok_engine = [r for r in rows if not r.get("engine_error")]
    lat = [r["wall_latency_ms"] for r in rows if r["http_status"] == 200 and not r.get("request_error")]
    model_rows = [r for r in rows if r["http_status"] == 200 and not r.get("request_error")]
    cd_truncated = [r for r in model_rows if r.get('decoding') == 'constrained' and r.get('truncated')]
    untruncated = [r for r in model_rows if not (r.get('decoding') == 'constrained' and r.get('truncated'))]
    d = ceiling.decompose(untruncated) if untruncated else dict.fromkeys(ceiling.CLASSES, 0)
    lookalike = sum(bool(lookalike_key_flag(r)) for r in rows)
    return {"n": len(rows), 'lookalike_key': lookalike, "engine_errors": len(rows) - len(ok_engine),
            "request_errors": dict(collections.Counter(r.get("request_error") or "http_error"
                                                       for r in rows if r["http_status"] != 200 or r.get("request_error"))),
            "truncated": sum(bool(r.get("truncated")) for r in rows),
            "tool": pct(rows, lambda r: r["eval"]["tool_correct"]),
            "schema_valid": pct(rows, lambda r: r["eval"]["schema_valid"]),
            "semantic": pct(rows, lambda r: r["eval"]["semantic_correct"]),
            "arg_em": pct(rows, lambda r: r["eval"]["arg_exact_match"]),
            "field_acc": 100 * sum(r["eval"]["field_acc"] for r in rows) / len(rows) if rows else None,
            "e2e": pct(rows, lambda r: r["eval"]["e2e_success"]),
            "e2e_strict": pct(rows, lambda r: r["eval"]["e2e_strict"]),
            "e2e_engine_ok": pct(ok_engine, lambda r: r["eval"]["e2e_success"]),
            "classes": {**{k: d[k] for k in ceiling.CLASSES}, 'cd_truncated': len(cd_truncated)},
            "in_tokens": sum(r["usage"].get("prompt_tokens", 0) for r in rows) / len(rows) if rows else 0,
            "out_tokens": sum(r["usage"].get("completion_tokens", 0) for r in rows) / len(rows) if rows else 0,
            "lat_p50": quantile(lat, 0.5), "lat_p95": quantile(lat, 0.95),
            "lat_p99": quantile(lat, 0.99) if len(lat) >= 200 else None}


def lookalike_key_flag(row):
    """A parallel diagnostic; frozen eval fields and raw outputs are never modified."""
    from .router import strict_loads
    from . import envelope
    import schema_utils as su
    try:
        call = strict_loads(row.get('raw_content', ''))
        if not isinstance(call, dict) or not isinstance(call.get('tool'), str):
            return []
        tool = next((t for t in paths.pool().values() if t['tool_name'] == call['tool']), None)
        if tool is None:
            return []
        return key_flags(call.get('arguments'), envelope.argument_schema(su.load_schema(tool['schema_id'])))
    except (ValueError, TypeError):
        return []


def truncation_sensitivity(ra, rb):
    """Descriptive, outcome-conditioned subset; never replaces the all-pair primary result."""
    def key(r):
        return (r['family'], r.get('catalog_id'), r['task_id'])
    b = {key(r): r for r in rb}
    pairs = [(r, b[key(r)]) for r in ra if key(r) in b]
    retained = [(a, b) for a, b in pairs if not a.get('truncated') and not b.get('truncated')]
    n = len(retained)
    return {'a_truncated': sum(bool(a.get('truncated')) for a, b in pairs),
            'b_truncated': sum(bool(b.get('truncated')) for a, b in pairs),
            'both_complete_n': n,
            'both_complete_a_pct': 100 * sum(a['eval']['e2e_success'] for a, b in retained) / n if n else None,
            'both_complete_b_pct': 100 * sum(b['eval']['e2e_success'] for a, b in retained) / n if n else None,
            'note': 'Post-hoc outcome-conditioned subset; excludes either-side truncations. Not a causal estimate or the primary comparison.'}


def run(run_id: str, server_log: str | None = None, order_audit: str | None = None) -> dict:
    rdir = os.path.join(paths.RUNS, run_id)
    rows = paths.jsonl(os.path.join(rdir, "results.jsonl"))
    man = json.load(open(os.path.join(rdir, "manifest.json")))
    memory = None
    if server_log:
        with open(server_log) as log:
            peaks = re.findall(r"(\d+)\s+maximum resident set size", log.read())
        memory = max(map(int, peaks)) if peaks else None
    arms = list(man["run_config"]["arms"])
    expected = man.get("expected_request_keys")
    if expected is None:
        raise ValueError("Legacy manifest lacks frozen request plan; do not infer completeness")
    provenance.validate_rows(rows, expected)
    missing = sorted(set(expected) - {r["request_key"] for r in rows})
    complete = not missing
    order = None
    if order_audit:
        order = json.load(open(order_audit))
        if order['run'] != run_id or order['source_results_sha256'] != provenance.file_sha(os.path.join(rdir, 'results.jsonl')):
            raise ValueError('Key-order audit does not match these results')
    infra = sum(bool(r.get("request_error")) or r["http_status"] != 200 for r in rows)
    res = {"run": run_id, "n": len(rows), "cells": [], "comparisons": [], "complete": complete, "expected_n": len(expected),
           "missing_n": len(missing), "infrastructure_failures": infra,
           "result_kind": man["run_config"].get("result_kind", "synthetic"),
           "inference_ready": complete and not infra and bool(man.get("preflight", {}).get("online_ok") if man.get("preflight") else False) and man["run_config"].get("result_kind") == "benchmark",
           "server_peak_rss_bytes": memory,
           "memory_note": "Maximum of macOS time -l RSS measurements in the supplied log; supply only this run's server sessions. Includes server lifetimes, not Metal allocator peak",
           "notes": ["Partial runs have descriptive tables only; no paired inference.",
                     "Cached sequential latencies are descriptive, not uncached speed benchmarks.",
                     "Failure taxonomy covers returned model outputs; request errors are separate."]}
    if order:
        res['key_order_audit'] = {k: order[k] for k in ('kind', 'tested_free_correct', 'all_free_correct', 'split', 'engine_build')}
    for fam in ("select", "arggen"):
        fr = [r for r in rows if r["family"] == fam]
        for size in sorted({r["size"] for r in fr}):
            for arm in arms:
                rs = [r for r in fr if r["arm"] == arm and r["size"] == size]
                if rs:
                    res["cells"].append({"family": fam, "size": size, "arm": arm, **cell(rs)})
    if complete:
        for name, a, b in man["run_config"].get("comparisons", []):
            for fam in ("select", "arggen"):
                sizes = [None] + sorted({r["size"] for r in rows if r["family"] == fam}) if fam == "select" else [1]
                for size in sizes:
                    ra = [r for r in rows if r["arm"] == a and r["family"] == fam and (size is None or r["size"] == size)]
                    rb = [r for r in rows if r["arm"] == b and r["family"] == fam and (size is None or r["size"] == size)]
                    st = exp_analyze.paired(ra, rb, lambda r: r["eval"]["e2e_success"]) if ra and rb else None
                    if st:
                        primary = name.startswith("PRIMARY:") and fam == "select" and size is None
                        res["comparisons"].append({"name": name, "family": fam, "size": size,
                                                   "primary": primary, "a": a, "b": b, **st,
                                                   'truncation_sensitivity': truncation_sensitivity(ra, rb)})
    secondary = [c for c in res["comparisons"] if not c["primary"]]
    for c, adj in zip(secondary, exp_analyze.holm([c["mcnemar_exact_p"] for c in secondary])):
        c["p_holm"] = adj
    for c in res["comparisons"]:
        if c["primary"]:
            c["p_holm"] = None
    out = os.path.join(paths.ANALYSIS, run_id)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report.json"), "w") as f:
        json.dump(res, f, indent=2, allow_nan=False)
    L = [f"# Report — run `{run_id}`", "", f"Evidence kind: {res['result_kind']}. Status: {'COMPLETE' if complete else 'PARTIAL: no paired inference'}. Requests: {res['n']}/{len(expected)}. Infrastructure failures: {infra}. Evaluation is against the raw schema. "
         "Engine refusals are counted separately from model errors.", "",
         "Cached sequential latency is descriptive. Taxonomy excludes request failures. p99 appears in JSON only for cells with at least 200 responses.", "",
         "| Family | Tools | Arm | n | Tool % | Schema valid % | Semantic % | E2E % | E2E % (engine ok) | Engine errors | "
         "CD truncated | malformed | wrong tool | invalid only | invalid+wrong | valid, wrong | In tok | Out tok | p50 ms | p95 ms |",
         "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c in res["cells"]:
        k = c["classes"]
        L.append(f"| {c['family']} | {c['size']} | {c['arm']} | {c['n']} | {c['tool']:.1f} | {c['schema_valid']:.1f} | {c['semantic']:.1f} | "
                 f"{c['e2e']:.1f} | {format(c['e2e_engine_ok'], '.1f') if c['e2e_engine_ok'] is not None else 'NA'} | {c['engine_errors']} | {k['cd_truncated']} | {k['malformed']} | {k['wrong_tool']} | "
                 f"{k['invalid_only']} | {k['invalid_wrong']} | {k['valid_wrong']} | {c['in_tokens']:.0f} | {c['out_tokens']:.0f} | "
                 f"{(c['lat_p50'] or 0):.0f} | {(c['lat_p95'] or 0):.0f} |")
    if res["comparisons"]:
        L += ["", "## Paired comparisons (B − A, E2E)", "",
              "| Comparison | Family | A | B | pairs | A % | B % | Δ pp [95% CI] | A-only / B-only | p (exact) | p (Holm) |",
              "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for c in res["comparisons"]:
            L.append(f"| {c['name']} (tools={c['size'] or 'pooled'}) | {c['family']} | {c['a']} | {c['b']} | {c['n_pairs']} | {100 * c['acc_a']:.1f} | {100 * c['acc_b']:.1f} | "
                     f"{c['diff_pp']:+.1f} [{c['ci95_diff_pp'][0]:+.1f}, {c['ci95_diff_pp'][1]:+.1f}] | "
                     f"{c['discordant_a_only']} / {c['discordant_b_only']} | {c['mcnemar_exact_p']:.3g} | {format(c['p_holm'], '.3g') if c['p_holm'] is not None else 'primary'} |")
    L += ["", "## Exact and field metrics", "",
          "| Family | Tools | Arm | Argument exact match % | Field accuracy % | Strict E2E % |",
          "|---|---:|---|---:|---:|---:|"]
    for c in res["cells"]:
        L.append(f"| {c['family']} | {c['size']} | {c['arm']} | {c['arg_em']:.1f} | {c['field_acc']:.1f} | {c['e2e_strict']:.1f} |")
    L += ["", "## Request failures and truncation", "",
          "| Family | Tools | Arm | Request errors by kind | Truncated outputs |",
          "|---|---:|---|---|---:|"]
    for c in res["cells"]:
        L.append(f"| {c['family']} | {c['size']} | {c['arm']} | {json.dumps(c['request_errors'])} | {c['truncated']} |")
    if res['comparisons']:
        L += ['', '## Truncation sensitivity (descriptive only)', '',
              'The primary comparison above includes every pair. The subset below conditions on both outputs finishing; it is biased by output behavior and is not a causal estimate.', '',
              '| Comparison | Family | Tools | A truncated | B truncated | Both finished pairs | A E2E % | B E2E % |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
        for c in res['comparisons']:
            t = c['truncation_sensitivity']
            a = f"{t['both_complete_a_pct']:.1f}" if t['both_complete_n'] else 'NA'
            b = f"{t['both_complete_b_pct']:.1f}" if t['both_complete_n'] else 'NA'
            L.append(f"| {c['name']} | {c['family']} | {c['size'] or 'pooled'} | {t['a_truncated']} | {t['b_truncated']} | {t['both_complete_n']} | {a} | {b} |")
    if order:
        L += ['', '## Post-hoc exact-engine key-order audit', '',
              f"Strict-contract JSON checked: {order['tested_free_correct']}/{order['all_free_correct']} free-correct outputs. Remaining outputs are excluded from this diagnostic, not from benchmark accuracy. Byte-token reachability is not model-token sampling or causal proof.", '',
              '| Free output category | Constrained correct | Constrained wrong | Constrained truncated |',
              '|---|---:|---:|---:|']
        split = order['split']['pooled']
        for category in ('accepted_original_order', 'order_only_rejection', 'other_rejection'):
            L.append('| ' + category + ' | ' + ' | '.join(str(split.get(category + '|' + outcome, 0)) for outcome in ('correct', 'wrong', 'truncated')) + ' |')
    L += ["", f"Server peak RSS: {memory if memory is not None else 'unrecorded'} bytes. See JSON memory_note for scope."]
    L += ['', '## Look-alike-key flags (overlapping diagnostic)', '',
          'No keys are renamed and no evaluator scores are changed.', '',
          '| Family | Tools | Arm | Flagged outputs |', '|---|---:|---|---:|']
    for c in res['cells']:
        L.append(f"| {c['family']} | {c['size']} | {c['arm']} | {c['lookalike_key']} |")
    L += ["", "E1 remains gated on a complete, infrastructure-clean E0 readout, inspection of engine errors, "
          "and unseen-schema v2/stress tasks. E2 is deferred until those datasets exist."]
    with open(os.path.join(out, "REPORT.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--server-log", help="macOS time -l server log, after stopping the server")
    ap.add_argument('--order-audit', help='Matching post-hoc native order-audit JSON')
    a = ap.parse_args()
    res = run(a.run, a.server_log, a.order_audit)
    print(f"{len(res['cells'])} cells, {len(res['comparisons'])} comparisons -> analysis/{a.run}/REPORT.md")


if __name__ == "__main__":
    main()
