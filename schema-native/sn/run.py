"""Run benchmark arms against any OpenAI-compatible chat endpoint.

This is the experiment's runner (``experiment/src/run.py``) with two additions:

* an ARM is now (representation, decoding, model alias) instead of a representation only;
* ``decoding: "constrained"`` adds the OpenAI ``response_format`` JSON-Schema field carrying the
  tool-call envelope (``sn.envelope``). That is the request shape ``jsonschema llm`` (Sourcemeta)
  speaks, and the one llama.cpp, vLLM and LM Studio accept.

Prompts, tasks, catalogs, tool order and the evaluator are imported unchanged from ``experiment/``.
Evaluation is always against the ORIGINAL raw schema. An engine that refuses a schema is recorded
as ``engine_error`` and kept apart from model errors in the analysis.

usage:
  python -m sn.run --config configs/runs/e0_decoding.json --server http://127.0.0.1:8080 [--run-id ID]
Results: schema-native/runs/<run_id>/results.jsonl (append-only, resumable).
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import fcntl
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

from . import envelope as env
from . import paths, provenance
from .preflight import plan, request_key
import prompts  # type: ignore  # noqa: E402
import schema_utils as su  # type: ignore  # noqa: E402
from evaluate import evaluate  # type: ignore  # noqa: E402


def http_json(url, payload=None, timeout=3600, headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}

    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        return 0, {"error": str(e)}


def error_kind(status, resp, decoding):
    """Keep infrastructure failures out of the model failure taxonomy."""
    if status == 200:
        return None
    msg = json.dumps(resp).lower()
    if "context" in msg and status in (400, 413):
        return "context_error"
    if status in (400, 422) and decoding == "constrained" and any(
        word in msg for word in ("schema", "grammar", "llguidance", "constraint")
    ):
        return "engine_error"
    return "transport_error" if status == 0 else "http_error"


def git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=paths.ROOT, text=True).strip()
    except Exception:
        return "unknown"


def response_format(schema: dict) -> dict:
    return {"type": "json_schema", "json_schema": {"name": "tool_call", "strict": True, "schema": schema}}


def build_requests(rc: dict, tasks: list[dict], cats: dict) -> list[tuple]:
    sel = [t for t in tasks if t["replicate"] in rc["replicates"]
           and (not rc.get("task_ids") or t["task_id"] in rc["task_ids"])
           and t["paraphrase_index"] in rc.get("paraphrases", [0, 1])]
    reqs = []
    if "select" in rc["families"]:
        for r in rc["replicates"]:
            for k in rc["sizes"]:
                cat = cats[f"C{k:03d}_R{r:02d}"]
                for arm in rc["arms"]:
                    for t in sel:
                        if t["replicate"] == r:
                            reqs.append(("select", arm, cat, t))
    if "arggen" in rc["families"]:
        for arm in rc["arms"]:
            for t in sel:
                reqs.append(("arggen", arm, None, t))
    return reqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--run-id")
    ap.add_argument("--preflight", help="successful online E0 preflight receipt")
    ap.add_argument("--server", default="http://127.0.0.1:8080")
    ap.add_argument("--api-key", default=os.environ.get("SN_API_KEY"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--arms", nargs="+", help="run only these arms now (one server holds one model; "
                    "restart the server with the other model and resume the same --run-id for the rest)")
    a = ap.parse_args()

    cfg_path = a.config if os.path.isabs(a.config) else os.path.join(paths.ROOT, a.config)
    rc = json.load(open(cfg_path))
    model = json.load(open(os.path.join(paths.ROOT, rc.get("model_config", "configs/model.qwen3-1.7b.json"))))
    run_id = a.run_id or f"{rc['run_prefix']}-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    if run_id in (".", "..") or os.path.basename(run_id) != run_id:
        raise ValueError("run-id must be a single directory name")
    a.server = a.server.rstrip("/")
    reqs, _ = plan(rc)
    expected = {request_key(*r) for r in reqs}
    ident = provenance.identity(rc, model)
    receipt = None
    if rc.get("requires_preflight"):
        if not a.preflight:
            raise ValueError("Run sn.preflight online and pass --preflight receipt.json")
        receipt = json.load(open(a.preflight))
        if not receipt.get("online_ok") or receipt["identity"] != ident or receipt["server"] != a.server:
            raise ValueError("Preflight is offline, stale, or for a different server/configuration")
    if a.arms and set(a.arms) - set(rc["arms"]):
        raise ValueError("Unknown --arms selection")
    rdir = os.path.join(paths.RUNS, run_id)
    os.makedirs(os.path.join(rdir, "prompts"), exist_ok=True)
    lock = open(os.path.join(rdir, ".writer.lock"), "w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    headers = {"Authorization": f"Bearer {a.api_key}"} if a.api_key else {}

    st, props = http_json(a.server + "/props", headers=headers)     # llama-server; optional elsewhere
    if receipt and (st != 200 or props != receipt["server_checks"]["props"]):
        raise ValueError("Server properties changed since preflight; run preflight again")
    manifest = os.path.join(rdir, "manifest.json")
    if os.path.exists(manifest):
        old = json.load(open(manifest))
        if (old.get("identity") != ident or old.get("server") != a.server
                or old.get("environment") != provenance.environment()
                or old.get("server_props") != (props if st == 200 else None)):
            raise ValueError("Resume identity mismatch: use a new run-id; existing data preserved")
    if not os.path.exists(manifest):
        json.dump({"run_id": run_id, "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "git_commit": git_sha(),
                   "run_config": rc, "model_config": model, "server": a.server,
                   "identity": ident, "environment": provenance.environment(), "preflight": receipt,
                   "expected_request_keys": sorted(expected),
                   "server_props": props if st == 200 else None,
                   "system_template": prompts.SYSTEM_TEMPLATE, "arggen_suffix": prompts.ARGGEN_SUFFIX},
                  open(manifest, "w"), indent=2, default=str)

    tasks, pool, cats = paths.tasks(), paths.pool(), paths.catalogs()
    raw = {}

    def raw_schema(tid):
        if tid not in raw:
            raw[tid] = su.load_schema(pool[tid]["schema_id"])
        return raw[tid]

    res_path = os.path.join(rdir, "results.jsonl")
    existing = paths.jsonl(res_path) if os.path.exists(res_path) else []
    provenance.validate_rows(existing, expected)
    done = {r["request_key"] for r in existing}
    base = dict(model["request_params"])
    base["cache_prompt"] = rc.get("cache_prompt", True)
    n_new = 0
    with open(res_path, "a") as fout:
        for fam, arm_name, cat, t in reqs:
            if a.arms and arm_name not in a.arms:
                continue
            arm = rc["arm_defs"][arm_name]
            key = request_key(fam, arm_name, cat, t)
            if key in done:
                continue
            rep = arm["representation"]
            msgs = prompts.messages_select(rep, cat["presentation_order"], t) if fam == "select" else prompts.messages_arggen(rep, t)
            sp_sha = prompts.sha(msgs[0]["content"])
            ppath = os.path.join(rdir, "prompts", f"{sp_sha[:16]}.txt.gz")
            if not os.path.exists(ppath):
                with gzip.open(ppath, "wt") as f:
                    f.write(msgs[0]["content"])
            cat_ids = cat["presentation_order"] if cat else [t["tool_id"]]
            payload = dict(base, messages=msgs)
            if arm.get("model"):
                payload["model"] = arm["model"]
            if arm["decoding"] == "constrained":
                payload["response_format"] = response_format(
                    env.envelope([(pool[i]["tool_name"], raw_schema(i)) for i in cat_ids]))
            t0 = time.perf_counter()
            status, resp = http_json(a.server + "/v1/chat/completions", payload, headers=headers)
            wall = (time.perf_counter() - t0) * 1000
            failure = error_kind(status, resp, arm["decoding"])
            ctx_err = failure == "context_error"
            engine_err = failure == "engine_error"
            content, finish, usage, timings = "", None, {}, {}
            if status == 200:
                try:
                    ch = resp["choices"][0]
                    content = ch["message"].get("content") or ""
                    if not isinstance(content, str):
                        raise ValueError("Non-text response content")
                    finish, usage, timings = ch.get("finish_reason"), resp.get("usage", {}), resp.get("timings", {})
                except (KeyError, IndexError, TypeError, ValueError):
                    failure = "response_error"
            names = {pool[i]["tool_name"] for i in cat_ids}
            ev = evaluate(content, t, raw_schema(t["tool_id"]), names, context_error=ctx_err)
            rec = {"request_key": key, "run_id": run_id, "family": fam, "arm": arm_name,
                   "representation": rep, "decoding": arm["decoding"], "model_alias": arm.get("model"),
                   "catalog_id": cat["catalog_id"] if cat else None, "size": cat["size"] if cat else 1,
                   "replicate": t["replicate"], "task_id": t["task_id"], "intent_id": t["intent_id"],
                   "tool_id": t["tool_id"], "stratum": t["stratum"],
                   "gold_position": cat["target_positions"][t["tool_id"]] if cat else 0,
                   "system_prompt_sha256": sp_sha, "user_message": msgs[1]["content"],
                   "http_status": status, "error": None if status == 200 and not failure else resp, "engine_error": engine_err, "request_error": failure,
                   "raw_content": content, "finish_reason": finish, "truncated": finish == "length",
                   "usage": usage, "server_timings": timings, "wall_latency_ms": wall, "eval": ev}
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fout.flush()
            n_new += 1
            if failure in ("transport_error", "http_error", "context_error", "response_error"):
                raise RuntimeError(f"Recorded {failure} for {key}; stopping. Inspect before starting a new run.")
            if n_new % 25 == 0:
                print(f"[{run_id}] {n_new} requests (last {key}, {wall:.0f} ms)", flush=True)
            if a.limit and n_new >= a.limit:
                break
    print(f"run {run_id}: {n_new} new requests -> {res_path}")


if __name__ == "__main__":
    main()
