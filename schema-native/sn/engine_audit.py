"""Model-free audit of constrained-decoding engines on the frozen tools and gold answers.

Question answered: *before any model runs*, can each engine (a) compile the tool's schema and
(b) produce the gold answer at all? If an engine's grammar rejects the gold call, that engine makes
the task unsolvable no matter how good the model is (a "false rejection"). If the engine reports
keywords it does not enforce, schema-valid output is no longer guaranteed (possible "false
acceptance"). Both are engine properties and must not be booked as model errors.

Engines audited when importable: llguidance, xgrammar, outlines_core. Each is driven at the
character/byte level, so no model tokenizer is needed. This does not test token-boundary
behaviour (see .txt's MaskBench for that); it is a necessary check, not a sufficient one.

usage: python -m sn.engine_audit [--out analysis/engine-audit]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import signal
from contextlib import contextmanager

from . import envelope as env
from . import paths
import schema_utils as su  # type: ignore  # noqa: E402


class Timeout(Exception):
    pass


@contextmanager
def time_limit(seconds: int):
    def handler(signum, frame):
        raise Timeout()
    old = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


# --------------------------------------------------------------------------- engine adapters
class LLGuidance:
    name = "llguidance"

    def __init__(self):
        import llguidance
        self.ll = llguidance
        self.tok = llguidance.LLTokenizer("byte")
        self.version = getattr(llguidance, "__version__", None) or _dist_version("llguidance")

    def compile(self, schema: dict):
        g = self.ll.LLMatcher.grammar_from_json_schema(json.dumps(schema))
        is_err, msgs = self.ll.LLMatcher.validate_grammar_with_warnings(g, self.tok)
        if is_err:
            raise ValueError("; ".join(msgs)[:300])
        return g, list(msgs)

    def accepts(self, grammar, text: str) -> bool:
        m = self.ll.LLMatcher(self.tok, grammar)
        toks = self.tok.tokenize_str(text)
        return m.try_consume_tokens(toks) == len(toks) and m.is_accepting()


class XGrammar:
    name = "xgrammar"

    def __init__(self):
        import xgrammar
        import xgrammar.testing as xt
        self.xg, self.xt = xgrammar, xt
        self.version = _dist_version("xgrammar")

    def compile(self, schema: dict):
        # strict_mode=True is the library default: properties not listed are rejected.
        return self.xg.Grammar.from_json_schema(json.dumps(schema)), []

    def accepts(self, grammar, text: str) -> bool:
        return bool(self.xt._is_grammar_accept_string(grammar, text))


class OutlinesCore:
    name = "outlines_core"

    def __init__(self):
        from outlines_core import json_schema
        self.js = json_schema
        self.version = _dist_version("outlines_core")

    def compile(self, schema: dict):
        rx = self.js.build_regex_from_schema(json.dumps(schema))
        return re.compile(rx, re.DOTALL), []

    def accepts(self, grammar, text: str) -> bool:
        return grammar.fullmatch(text) is not None


def _dist_version(name: str):
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return None


def available_engines() -> list:
    out = []
    for cls in (LLGuidance, XGrammar, OutlinesCore):
        try:
            out.append(cls())
        except Exception as e:  # not installed on this machine
            print(f"[engine-audit] {cls.name} unavailable: {type(e).__name__}: {e}")
    return out


# --------------------------------------------------------------------------- audit
def audit_tool(engine, tool_name: str, raw_schema: dict, gold_tasks: list[dict], timeout_s: int = 20) -> dict:
    rec = {"compile_ok": False, "compile_error": None, "warnings": [], "gold": []}
    try:
        with time_limit(timeout_s):
            branch = env.tool_branch(tool_name, raw_schema)
            grammar, warns = engine.compile(branch)
        rec["compile_ok"], rec["warnings"] = True, warns
    except Timeout:
        rec["compile_error"] = f"timeout>{timeout_s}s"
        return rec
    except Exception as e:
        rec["compile_error"] = f"{type(e).__name__}: {str(e)[:240]}"
        return rec
    for t in gold_tasks:
        call = env.gold_call(t, raw_schema)
        try:
            with time_limit(timeout_s):
                ok_c = engine.accepts(grammar, env.dumps_compact(call))
                ok_s = engine.accepts(grammar, env.dumps_spaced(call))
        except Timeout:
            ok_c = ok_s = None
        rec["gold"].append({"task_id": t["task_id"], "accept_compact": ok_c, "accept_spaced": ok_s})
    return rec


def run(out_dir: str, pool_wide: bool = True) -> dict:
    pool, tasks = paths.pool(), paths.tasks()
    by_tool = collections.defaultdict(list)
    for t in tasks:
        if t["paraphrase_index"] == 0:           # paraphrases share gold arguments
            by_tool[t["tool_id"]].append(t)
    tool_ids = sorted(pool) if pool_wide else sorted(by_tool)
    engines = available_engines()
    rows, summary = [], {}
    for eng in engines:
        s = collections.Counter()
        for tid in tool_ids:
            raw = su.load_schema(pool[tid]["schema_id"])
            r = audit_tool(eng, pool[tid]["tool_name"], raw, by_tool.get(tid, []))
            r.update({"engine": eng.name, "tool_id": tid, "stratum": pool[tid]["stratum"],
                      "is_target": tid in by_tool, "schema_audit": env.audit(raw)})
            rows.append(r)
            s["tools"] += 1
            s["compile_ok"] += r["compile_ok"]
            s["compile_ok_with_warnings"] += bool(r["compile_ok"] and r["warnings"])
            if tid in by_tool:
                s["targets"] += 1
                s["targets_compile_ok"] += r["compile_ok"]
                g = r["gold"][0] if r["gold"] else None
                if g:
                    s["gold_accept_either"] += bool(g["accept_compact"] or g["accept_spaced"])
                    s["gold_accept_compact"] += bool(g["accept_compact"])
                    s["gold_accept_spaced"] += bool(g["accept_spaced"])
        summary[eng.name] = {"version": eng.version, **s}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "engine_audit.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    res = {"n_tools": len(tool_ids), "n_targets": len(by_tool), "engines": summary}
    with open(os.path.join(out_dir, "engine_audit.summary.json"), "w") as f:
        json.dump(res, f, indent=2)
    _write_md(res, rows, pool, os.path.join(out_dir, "ENGINE_AUDIT.md"))
    return res


def _write_md(res: dict, rows: list[dict], pool: dict, path: str) -> None:
    L = ["# Engine audit (model-free)", "",
         "Each engine is asked to compile the constrained-decoding schema of every tool and then to "
         "accept the frozen gold call, character by character. No model is involved. "
         "A rejected gold call means the engine makes that task unsolvable.", "",
         f"Tools: {res['n_tools']}. Target tools with a gold answer: {res['n_targets']}.", "",
         "| Engine | Version | Schemas compiled | Compiled with warnings | Targets compiled | Gold accepted (compact) | Gold accepted (spaced) | Gold accepted (either) |",
         "|---|---|---:|---:|---:|---:|---:|---:|"]
    for name, s in res["engines"].items():
        L.append(f"| {name} | {s['version']} | {s['compile_ok']}/{s['tools']} | {s['compile_ok_with_warnings']} | "
                 f"{s['targets_compile_ok']}/{s['targets']} | {s['gold_accept_compact']}/{s['targets']} | "
                 f"{s['gold_accept_spaced']}/{s['targets']} | {s['gold_accept_either']}/{s['targets']} |")
    L += ["", "## Target tools where an engine cannot produce the gold call", "",
          "| Engine | Tool | Stratum | Problem | Schema keywords |", "|---|---|---|---|---|"]
    for r in rows:
        if not r["is_target"]:
            continue
        g = r["gold"][0] if r["gold"] else None
        problem = None
        if not r["compile_ok"]:
            problem = "compile: " + (r["compile_error"] or "")[:110]
        elif g and not (g["accept_compact"] or g["accept_spaced"]):
            problem = "gold call rejected"
        if problem:
            kws = ", ".join(k for k in r["schema_audit"]["assertion_keywords"] if k not in ("type", "properties", "required"))
            L.append(f"| {r['engine']} | {pool[r['tool_id']]['tool_name']} ({r['tool_id']}) | {r['stratum']} | {problem.replace('|', '/')} | {kws} |")
    warn = collections.Counter()
    for r in rows:
        for w in r["warnings"]:
            warn[(r["engine"], w[:120])] += 1
    if warn:
        L += ["", "## Warnings (keywords accepted but not enforced)", "", "| Engine | Warning | Tools |", "|---|---|---:|"]
        for (e, w), n in warn.most_common(20):
            L.append(f"| {e} | {w.replace('|', '/')} | {n} |")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(paths.ANALYSIS, "engine-audit"))
    ap.add_argument("--targets-only", action="store_true")
    a = ap.parse_args()
    res = run(a.out, pool_wide=not a.targets_only)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
