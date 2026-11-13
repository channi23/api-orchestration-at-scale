"""Build validator-checked training examples from the leakage-safe schema pool.

For each training schema a local TEACHER model (any OpenAI-compatible endpoint; no paid API) writes
one tool card and one user request with matching arguments. Nothing is trusted:

  1. ``arguments`` must validate against the ORIGINAL raw schema (deterministic, ``jsonschema``).
  2. The request must not leak the tool name (deterministic string check).
  3. Round trip: the teacher is asked again, seeing only the tool and the request, to produce the
     arguments. The example is kept only if the two answers agree under the experiment's own
     semantic comparison (``evaluate.compare_args``).

Rejected examples are written too, with the reason, so the filter's selection effect can be
reported. The filter keeps examples the teacher finds unambiguous; that biases training data
towards easier requests. This is a stated limitation, not something the filter removes.

usage:
  python -m sn.synth --server http://127.0.0.1:8081 --split train --per-schema 2 [--limit 50]
Output: data/synth/<split>.v1.jsonl and data/synth/<split>.rejected.v1.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re

from . import envelope as env
from . import paths
from .run import http_json, response_format
import prompts  # type: ignore  # noqa: E402
import schema_utils as su  # type: ignore  # noqa: E402
from evaluate import compare_args, parse_output, schema_errors  # type: ignore  # noqa: E402

AUTHOR_SYSTEM = (
    "You write test data for a tool-calling benchmark. You are given the JSON Schema of one tool's input. "
    "Return a JSON object with: tool_name (snake_case verb phrase), description (one sentence saying what the tool does), "
    "request (what a user would naturally say, containing every value needed, without naming the tool or its field names), "
    "and arguments (the exact input the tool should receive for that request; it must satisfy the schema). "
    "Only include optional fields that the request states. Use realistic, varied values."
)


def card_schema(arg_schema: dict) -> dict:
    return {"type": "object",
            "properties": {"tool_name": {"type": "string", "pattern": "^[a-z][a-z0-9_]{2,40}$"},
                           "description": {"type": "string", "minLength": 15, "maxLength": 200},
                           "request": {"type": "string", "minLength": 20, "maxLength": 600},
                           "arguments": arg_schema},
            "required": ["tool_name", "description", "request", "arguments"], "additionalProperties": False}


def leaks_name(request: str, tool_name: str) -> bool:
    r = request.lower()
    return tool_name.lower() in r or tool_name.replace("_", " ").lower() in r


def chat(server: str, messages: list[dict], schema: dict | None, params: dict) -> tuple[int, str]:
    payload = dict(params, messages=messages)
    if schema is not None:
        payload["response_format"] = response_format(schema)
    st, resp = http_json(server + "/v1/chat/completions", payload)
    if st != 200:
        return st, json.dumps(resp)[:300]
    return st, resp["choices"][0]["message"].get("content") or ""


def make_example(server: str, row: dict, variant: int, params: dict, constrained: bool = True) -> tuple[dict | None, dict]:
    """Returns (example or None, audit record)."""
    raw = su.load_schema(row["schema_id"])
    arg_schema = env.argument_schema(raw)
    seed = int(hashlib.sha256(f"{row['schema_id']}:{variant}".encode()).hexdigest()[:8], 16)
    p = dict(params, seed=seed)
    audit = {"schema_id": row["schema_id"], "variant": variant, "family": row["family"], "split": row["split"]}
    user = "Schema:\n" + json.dumps(raw, ensure_ascii=False) + (f"\n\nThis is variant {variant}: choose different values and wording." if variant else "")
    st, out = chat(server, [{"role": "system", "content": AUTHOR_SYSTEM}, {"role": "user", "content": user}],
                   card_schema(arg_schema) if constrained else None, p)
    if st != 200:
        return None, dict(audit, reason="teacher_http_error", detail=out)
    try:
        m = re.search(r"\{.*\}", out, re.DOTALL)
        card = json.loads(m.group(0) if m else out)
        name, desc, req, args = card["tool_name"], card["description"], card["request"], card["arguments"]
    except Exception as e:
        return None, dict(audit, reason="unparseable_card", detail=f"{type(e).__name__}")
    if not isinstance(args, dict) or not args:
        return None, dict(audit, reason="empty_arguments")
    errs = schema_errors(args, raw)
    if errs:
        return None, dict(audit, reason="arguments_invalid_against_raw_schema", detail=errs[:2])
    if leaks_name(req, name):
        return None, dict(audit, reason="request_leaks_tool_name")
    # ---- round trip: tool + request -> arguments, without seeing the first answer
    tool = {"type": "function", "function": {"name": name, "description": desc, "parameters": raw}}
    sys_prompt = prompts.SYSTEM_TEMPLATE.format(tools=json.dumps([tool], ensure_ascii=False, indent=2))
    st, out2 = chat(server, [{"role": "system", "content": sys_prompt},
                             {"role": "user", "content": req + prompts.ARGGEN_SUFFIX.format(tool_name=name)}],
                    env.tool_branch(name, raw) if constrained else None, dict(params, seed=seed + 1))
    parsed = parse_output(out2) if st == 200 else {"format_ok": False}
    if not parsed.get("format_ok"):
        return None, dict(audit, reason="round_trip_unparseable")
    cmp = compare_args(parsed["arguments"], {"gold_args": args})
    if not cmp["semantic_correct"] or cmp["extra_paths"]:
        return None, dict(audit, reason="round_trip_disagrees",
                          detail={"field_acc": cmp["field_acc"], "extra": cmp["extra_paths"][:5]})
    ex = {"example_id": f"{row['schema_id']}#{variant}", "schema_id": row["schema_id"], "family": row["family"],
          "split": row["split"], "stratum": row["stratum"], "tool_name": name, "description": desc,
          "request": req, "gold_args": args}
    return ex, dict(audit, reason="kept")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://127.0.0.1:8081")
    ap.add_argument("--split", default="train", choices=["train", "valid", "holdout_family"])
    ap.add_argument("--per-schema", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--unconstrained", action="store_true", help="teacher endpoint has no response_format support")
    ap.add_argument("--pool", default=os.path.join(paths.DATA, "trainpool", "schemas.v1.jsonl"))
    ap.add_argument("--out", default=os.path.join(paths.DATA, "synth"))
    a = ap.parse_args()
    rows = [r for r in paths.jsonl(a.pool) if r["split"] == a.split]
    if a.limit:
        rows = rows[:a.limit]
    os.makedirs(a.out, exist_ok=True)
    kept_path = os.path.join(a.out, f"{a.split}.v1.jsonl")
    rej_path = os.path.join(a.out, f"{a.split}.rejected.v1.jsonl")
    done = set()
    for pth in (kept_path, rej_path):
        if os.path.exists(pth):
            for r in paths.jsonl(pth):
                done.add(r.get("example_id") or f"{r['schema_id']}#{r['variant']}")
    params = {"temperature": 0.7, "top_p": 0.9, "max_tokens": 700, "chat_template_kwargs": {"enable_thinking": False}}
    n_keep = n_rej = 0
    with open(kept_path, "a") as fk, open(rej_path, "a") as fr:
        for row in rows:
            for v in range(a.per_schema):
                if f"{row['schema_id']}#{v}" in done:
                    continue
                ex, audit = make_example(a.server, row, v, params, constrained=not a.unconstrained)
                if ex:
                    fk.write(json.dumps(ex, ensure_ascii=False) + "\n"); fk.flush(); n_keep += 1
                else:
                    fr.write(json.dumps(audit, ensure_ascii=False) + "\n"); fr.flush(); n_rej += 1
    tot = n_keep + n_rej
    print(f"{a.split}: kept {n_keep}, rejected {n_rej}" + (f" (pass rate {100 * n_keep / tot:.1f}%)" if tot else ""))


if __name__ == "__main__":
    main()
