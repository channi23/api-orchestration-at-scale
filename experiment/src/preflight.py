"""Pre-run checks for the full experiment. Exits non-zero if any check fails.

1. server/model: model path, context size, GGUF sha256 == config/model.json
2. context limit: for EVERY catalog x representation, exact chat-templated prompt tokens (model tokenizer,
   longest task message of that replicate) + max_tokens <= context
3. artifact integrity: representation file hashes == manifest; tasks rebuild cleanly; evaluator tests pass
4. request counts of full and latency configs
Writes runs/preflight.json (committed with the run).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prompts  # noqa: E402
import schema_utils as su  # noqa: E402
from run import http_json  # noqa: E402

S = "http://127.0.0.1:8080"
EXP = su.EXP


def main():
    model = json.load(open(os.path.join(EXP, "config", "model.json")))
    out = {"checks": {}}
    ok = True

    st, props = http_json(S + "/props")
    mp = props.get("model_path", "")
    h = hashlib.sha256()
    with open(mp, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    n_ctx = (props.get("default_generation_settings") or {}).get("n_ctx") or model["context_length"]
    c1 = {"model_path": mp, "gguf_sha256": h.hexdigest(), "expected_sha256": model["gguf_sha256"],
          "n_ctx": n_ctx, "build": props.get("build_info")}
    c1["pass"] = c1["gguf_sha256"] == model["gguf_sha256"] and n_ctx == model["context_length"]
    out["checks"]["model"] = c1
    ok &= c1["pass"]

    tasks = [json.loads(l) for l in open(os.path.join(EXP, "tasks", "tasks.v1.jsonl"))]
    cats = json.load(open(os.path.join(EXP, "catalogs", "catalogs.v1.json")))["catalogs"]
    max_new = model["request_params"]["max_tokens"]
    rows, worst = [], {}
    for c in cats:
        longest = max((t for t in tasks if t["replicate"] == c["replicate"]), key=lambda t: len(t["prompt"]))
        for arm in ["raw", "minified", "normalized", "tscg", "tscg_info"]:
            msgs = prompts.messages_select(arm, c["presentation_order"], longest)
            st, tpl = http_json(S + "/apply-template", {"messages": msgs, "chat_template_kwargs": {"enable_thinking": False}})
            assert st == 200, tpl
            st, tk = http_json(S + "/tokenize", {"content": tpl["prompt"], "add_special": True})
            n = len(tk["tokens"])
            rows.append({"catalog_id": c["catalog_id"], "arm": arm, "prompt_tokens": n, "plus_max_new": n + max_new})
            key = (c["size"], arm)
            worst[key] = max(worst.get(key, 0), n + max_new)
    over = [r for r in rows if r["plus_max_new"] > n_ctx]
    out["checks"]["context_limit"] = {"n_ctx": n_ctx, "max_new_tokens": max_new, "n_prompts_checked": len(rows),
                                      "worst_case_by_size_arm": {f"{k}/{a}": v for (k, a), v in sorted(worst.items())},
                                      "exceeding": over, "pass": not over}
    ok &= not over

    man = json.load(open(os.path.join(EXP, "representations", "manifest.v1.json")))
    bad = [f for f, hsh in man["files"].items()
           if hashlib.sha256(open(os.path.join(EXP, "representations", f), "rb").read()).hexdigest() != hsh]
    out["checks"]["representation_hashes"] = {"mismatch": bad, "pass": not bad}
    ok &= not bad
    for name, cmd in (("tasks_build", ["python3", "src/build_tasks.py"]), ("evaluator_tests", ["python3", "tests/test_evaluate.py"])):
        p = subprocess.run(cmd, cwd=EXP, capture_output=True, text=True)
        out["checks"][name] = {"stdout": p.stdout.strip()[-300:], "pass": p.returncode == 0}
        ok &= p.returncode == 0

    counts = {}
    for cfgname in ("full", "latency"):
        rc = json.load(open(os.path.join(EXP, "config", "runs", f"{cfgname}.json")))
        sel = [t for t in tasks if t["replicate"] in rc["replicates"] and t["paraphrase_index"] in rc["paraphrases"]
               and (not rc.get("task_ids") or t["task_id"] in rc["task_ids"])]
        n = 0
        if "select" in rc["families"]:
            n += len(sel) * len(rc["sizes"]) * len(rc["arms"])
        if "arggen" in rc["families"]:
            n += len(sel) * len(rc["arms"])
        counts[cfgname] = n
    out["checks"]["request_counts"] = {**counts, "pass": counts == {"full": 3000, "latency": 50}}
    ok &= counts == {"full": 3000, "latency": 50}
    free = shutil.disk_usage(EXP).free / 1e9
    out["checks"]["disk_free_gb"] = {"value": round(free, 1), "pass": free > 2}
    ok &= free > 2
    out["all_pass"] = bool(ok)
    json.dump(out, open(os.path.join(EXP, "runs", "preflight.json"), "w"), indent=1)
    for k, v in out["checks"].items():
        print(f"{'PASS' if v['pass'] else 'FAIL'}  {k}")
    print(json.dumps({k: v for k, v in out["checks"]["context_limit"]["worst_case_by_size_arm"].items() if k.startswith("100/")}, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
