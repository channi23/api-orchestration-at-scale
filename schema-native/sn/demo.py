"""Minimal CLI: ask one request against a frozen catalog and see what happened.

  python -m sn.demo --server http://127.0.0.1:8080 --catalog C005_R00 \
      --ask "Register our vendor's public app called Fieldnote Planner ..." [--constrained] [--shortlist 3]

Prints the raw model output, the parsed call, every validation error against the raw schema of the
tool the model picked, and token/latency numbers. With ``--task T106_p0`` the frozen request is used
and the answer is also scored against the gold arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import time

from . import envelope as env
from . import paths
from . import shortlist as sl
from .run import error_kind, http_json, constraint_payload
import prompts  # type: ignore  # noqa: E402
import render  # type: ignore  # noqa: E402
import schema_utils as su  # type: ignore  # noqa: E402
from evaluate import evaluate, parse_output, schema_errors  # type: ignore  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://127.0.0.1:8080")
    ap.add_argument("--catalog", default="C005_R00")
    ap.add_argument("--ask")
    ap.add_argument("--task")
    ap.add_argument("--representation", default="minified", choices=["raw", "minified", "normalized"])
    ap.add_argument("--constrained", action="store_true")
    ap.add_argument("--shortlist", type=int, default=0, help="keep only the BM25 top-k tools before prompting")
    ap.add_argument("--model")
    a = ap.parse_args()

    pool, cats = paths.pool(), paths.catalogs()
    task = next((t for t in paths.tasks() if t["task_id"] == a.task), None) if a.task else None
    request = task["prompt"] if task else a.ask
    if not request:
        ap.error("give --ask or --task")
    ids = list(cats[a.catalog]["presentation_order"])
    if a.shortlist:
        bm = sl.BM25({i: sl.tool_document(pool[i], "card") for i in ids})
        keep = set(bm.rank(sl.tokens(request))[:a.shortlist])
        ids = [i for i in ids if i in keep]
        print(f"shortlist: {[pool[i]['tool_name'] for i in ids]}")
    raw = {i: su.load_schema(pool[i]["schema_id"]) for i in ids}
    system = prompts.SYSTEM_TEMPLATE.format(tools=render.render_catalog(a.representation, ids))
    model = json.load(open(os.path.join(paths.ROOT, "configs", "model.qwen3-1.7b.json")))
    payload = dict(model["request_params"], messages=[{"role": "system", "content": system}, {"role": "user", "content": request}])
    if a.model:
        payload["model"] = a.model
    if a.constrained:
        payload.update(constraint_payload(env.envelope([(pool[i]["tool_name"], raw[i]) for i in ids]), model.get("constraint_transport", "response_format")))
    t0 = time.perf_counter()
    st, resp = http_json(a.server + "/v1/chat/completions", payload)
    ms = (time.perf_counter() - t0) * 1000
    if st != 200:
        print(f"HTTP {st}: {json.dumps(resp)[:500]}")
        print("-> request failure:", error_kind(st, resp, "constrained" if a.constrained else "free"))
        return
    content = resp["choices"][0]["message"].get("content") or ""
    print(f"\n--- model output ({'constrained' if a.constrained else 'free'}, {a.representation}, {len(ids)} tools)\n{content}\n")
    parsed = parse_output(content)
    if not parsed["format_ok"]:
        print("NOT a parseable tool call.")
        return
    by_name = {pool[i]["tool_name"]: i for i in ids}
    print(f"tool: {parsed['tool']}   in catalog: {parsed['tool'] in by_name}")
    if parsed["tool"] in by_name:
        errs = schema_errors(parsed["arguments"], raw[by_name[parsed["tool"]]])
        print(f"schema validation against the raw schema: {'VALID' if not errs else str(len(errs)) + ' error(s)'}")
        for e in errs:
            print(f"   - [{e['validator']}] at '{e['path']}': {e['message']}")
    if task:
        ev = evaluate(content, task, su.load_schema(task["schema_id"]), set(by_name))
        print(f"gold tool: {task['tool_name']}   tool correct: {ev['tool_correct']}   semantic: {ev['semantic_correct']}   E2E: {ev['e2e_success']}")
        wrong = [k for k, v in ev["field_semantic"].items() if not v]
        if wrong:
            print(f"wrong or missing requested values: {wrong}")
        if ev["unrequested_value_paths"]:
            print(f"invented values in fields nobody asked for: {ev['unrequested_value_paths']}")
        if ev["failure_primary"]:
            print(f"failure class: {ev['failure_primary']}")
    u = resp.get("usage", {})
    print(f"\ntokens in/out: {u.get('prompt_tokens')}/{u.get('completion_tokens')}   wall: {ms:.0f} ms")


if __name__ == "__main__":
    main()
