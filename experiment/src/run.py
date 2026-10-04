"""Run the experiment against a running llama-server (see scripts/start_server.sh).

usage: python src/run.py --config config/runs/pilot.json [--run-id ID]  (resumes if run dir exists)

Per request the following is persisted to runs/<run_id>/results.jsonl (append-only):
ids (task/catalog/arm/family/size/replicate), system-prompt sha256, user message, raw response
(content, finish_reason, usage, server timings), wall latency, and the full evaluation record.
System prompts are stored once per (catalog, arm) in runs/<run_id>/prompts/*.txt.gz.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prompts  # noqa: E402
import schema_utils as su  # noqa: E402
from evaluate import evaluate  # noqa: E402

EXP = su.EXP


def http_json(url, payload=None, timeout=3600):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}


def git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=EXP, text=True).strip()
    except Exception:
        return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--run-id")
    ap.add_argument("--server", default="http://127.0.0.1:8080")
    ap.add_argument("--limit", type=int, default=0, help="debug: stop after N requests")
    args = ap.parse_args()

    rc = json.load(open(os.path.join(EXP, args.config) if not os.path.isabs(args.config) else args.config))
    model = json.load(open(os.path.join(EXP, "config", "model.json")))
    run_id = args.run_id or f"{rc['run_prefix']}-{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{git_sha()[:7]}"
    rdir = os.path.join(EXP, "runs", run_id)
    os.makedirs(os.path.join(rdir, "prompts"), exist_ok=True)

    st, props = http_json(args.server + "/props")
    assert st == 200, f"server not reachable: {props}"
    manifest_path = os.path.join(rdir, "manifest.json")
    if not os.path.exists(manifest_path):
        json.dump({"run_id": run_id, "created_utc": dt.datetime.utcnow().isoformat() + "Z", "git_commit": git_sha(),
                   "run_config": rc, "model_config": model,
                   "server_props": {k: props.get(k) for k in ("model_path", "n_ctx", "total_slots", "build_info", "chat_template")
                                    if k in props} | {"default_generation_settings": props.get("default_generation_settings")},
                   "system_template": prompts.SYSTEM_TEMPLATE, "arggen_suffix": prompts.ARGGEN_SUFFIX},
                  open(manifest_path, "w"), indent=2)

    tasks = [json.loads(l) for l in open(os.path.join(EXP, "tasks", "tasks.v1.jsonl"))]
    pool = {json.loads(l)["tool_id"]: json.loads(l) for l in open(os.path.join(EXP, "dataset", "tool_pool.v1.jsonl"))}
    cats = {c["catalog_id"]: c for c in json.load(open(os.path.join(EXP, "catalogs", "catalogs.v1.json")))["catalogs"]}
    raw_schemas = {}

    res_path = os.path.join(rdir, "results.jsonl")
    done = set()
    if os.path.exists(res_path):
        for l in open(res_path):
            r = json.loads(l)
            done.add(r["request_key"])

    # ---- build the request list in cache-friendly order: group by (catalog, arm)
    reqs = []
    sel_tasks = [t for t in tasks if t["replicate"] in rc["replicates"]
                 and (not rc.get("task_ids") or t["task_id"] in rc["task_ids"])
                 and t["paraphrase_index"] in rc.get("paraphrases", [0, 1])]
    if "select" in rc["families"]:
        for r in rc["replicates"]:
            for k in rc["sizes"]:
                cat = cats[f"C{k:03d}_R{r:02d}"]
                for arm in rc["arms"]:
                    for t in sel_tasks:
                        if t["replicate"] == r:
                            reqs.append(("select", arm, cat, t))
    if "arggen" in rc["families"]:
        for arm in rc["arms"]:
            for t in sel_tasks:
                reqs.append(("arggen", arm, None, t))

    params = dict(model["request_params"])
    params["cache_prompt"] = rc.get("cache_prompt", True)
    n_new = 0
    with open(res_path, "a") as fout:
        for fam, arm, cat, t in reqs:
            key = f"{fam}|{arm}|{cat['catalog_id'] if cat else 'single'}|{t['task_id']}"
            if key in done:
                continue
            msgs = prompts.messages_select(arm, cat["presentation_order"], t) if fam == "select" else prompts.messages_arggen(arm, t)
            sp = msgs[0]["content"]
            sp_sha = prompts.sha(sp)
            ppath = os.path.join(rdir, "prompts", f"{sp_sha[:16]}.txt.gz")
            if not os.path.exists(ppath):
                with gzip.open(ppath, "wt") as f:
                    f.write(sp)
            payload = dict(params, messages=msgs)
            t0 = time.perf_counter()
            status, resp = http_json(args.server + "/v1/chat/completions", payload)
            wall = (time.perf_counter() - t0) * 1000
            ctx_err = status != 200 and "context" in json.dumps(resp).lower()
            content, finish, usage, timings = "", None, {}, {}
            if status == 200:
                ch = resp["choices"][0]
                content = ch["message"].get("content") or ""
                finish = ch.get("finish_reason")
                usage = resp.get("usage", {})
                timings = resp.get("timings", {})
            if t["tool_id"] not in raw_schemas:
                raw_schemas[t["tool_id"]] = su.load_schema(t["schema_id"])
            cat_ids = cat["presentation_order"] if cat else [t["tool_id"]]
            names = {pool[i]["tool_name"] for i in cat_ids}
            ev = evaluate(content, t, raw_schemas[t["tool_id"]], names, context_error=ctx_err)
            rec = {"request_key": key, "run_id": run_id, "family": fam, "arm": arm,
                   "catalog_id": cat["catalog_id"] if cat else None, "size": cat["size"] if cat else 1,
                   "replicate": t["replicate"], "task_id": t["task_id"], "intent_id": t["intent_id"],
                   "tool_id": t["tool_id"], "stratum": t["stratum"],
                   "gold_position": cat["target_positions"][t["tool_id"]] if cat else 0,
                   "system_prompt_sha256": sp_sha, "user_message": msgs[1]["content"],
                   "http_status": status, "error": None if status == 200 else resp,
                   "raw_content": content, "finish_reason": finish, "truncated": finish == "length",
                   "usage": usage, "server_timings": timings, "wall_latency_ms": wall,
                   "cache_prompt": params["cache_prompt"], "eval": ev}
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fout.flush()
            n_new += 1
            if n_new % 25 == 0:
                print(f"[{run_id}] {n_new} new requests done (last: {key}, {wall:.0f} ms)", flush=True)
            if args.limit and n_new >= args.limit:
                break
    print(f"run {run_id}: {n_new} new requests, results at {res_path}")


if __name__ == "__main__":
    main()
