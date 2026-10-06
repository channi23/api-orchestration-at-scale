"""Token counts with the MODEL'S OWN tokenizer (llama-server /tokenize), same tokenizer for all arms.

Outputs:
  representations/token_counts.v1.jsonl          per tool x arm: tokens, chars, bytes, transform time
  representations/catalog_token_counts.v1.jsonl  per catalog x arm: system-prompt tokens
  representations/representation_metrics.v1.json summary (reduction / compression vs raw)
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prompts  # noqa: E402
import render  # noqa: E402
import schema_utils as su  # noqa: E402
from run import http_json  # noqa: E402


def ntok(server, text):
    st, r = http_json(server + "/tokenize", {"content": text, "add_special": False})
    assert st == 200, r
    return len(r["tokens"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://127.0.0.1:8080")
    ap.add_argument("--out", default=None, help="output dir (default representations/)")
    a = ap.parse_args()
    st, props = http_json(a.server + "/props")
    tok_id = os.path.basename(props.get("model_path", "unknown"))
    pool = [json.loads(l) for l in open(os.path.join(su.EXP, "dataset", "tool_pool.v1.jsonl"))]
    rows = []
    for t in pool:
        base = None
        for arm in render.ARMS:
            text = render.render_tool(arm, t["tool_id"])
            n = ntok(a.server, text)
            if arm == "raw":
                base = n
            rows.append({"tool_id": t["tool_id"], "stratum": t["stratum"], "arm": arm, "tokens": n,
                         "raw_tokens": base, "token_reduction": base - n,
                         "compression_pct": round(100 * (base - n) / base, 2), "chars": len(text),
                         "bytes": len(text.encode()),
                         "transform_ms_median": render.load_arm(arm)[t["tool_id"]]["transform_ms_median"],
                         "tokenizer": tok_id})
    out = a.out or os.path.join(su.EXP, "representations")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "token_counts.v1.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    cats = json.load(open(os.path.join(su.EXP, "catalogs", "catalogs.v1.json")))["catalogs"]
    crow = []
    for c in cats:
        for arm in render.ARMS:
            crow.append({"catalog_id": c["catalog_id"], "size": c["size"], "replicate": c["replicate"], "arm": arm,
                         "system_prompt_tokens": ntok(a.server, prompts.system_prompt(arm, c["presentation_order"]))})
    with open(os.path.join(out, "catalog_token_counts.v1.jsonl"), "w") as f:
        for r in crow:
            f.write(json.dumps(r) + "\n")
    summ = {"tokenizer": tok_id, "note": "tokens of the per-tool representation text (no chat template)"}
    for arm in render.ARMS:
        for strat in ("all", "flat", "structured"):
            sel = [r for r in rows if r["arm"] == arm and (strat == "all" or r["stratum"] == strat)]
            summ[f"{arm}/{strat}"] = {"mean_tokens": round(statistics.mean(r["tokens"] for r in sel), 1),
                                      "median_compression_pct": round(statistics.median(r["compression_pct"] for r in sel), 1),
                                      "mean_compression_pct": round(statistics.mean(r["compression_pct"] for r in sel), 1),
                                      "median_transform_ms": round(statistics.median(r["transform_ms_median"] for r in sel), 4)}
    for k in sorted({c["size"] for c in cats}):
        for arm in render.ARMS:
            v = [r["system_prompt_tokens"] for r in crow if r["size"] == k and r["arm"] == arm]
            summ[f"catalog/{k}/{arm}"] = {"mean": round(statistics.mean(v), 1), "max": max(v)}
    json.dump(summ, open(os.path.join(out, "representation_metrics.v1.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in summ.items() if k.startswith("catalog/100") or k.endswith("/all")}, indent=1))


if __name__ == "__main__":
    main()
