"""Representation rendering shared by the builder and the runner.

The ONLY thing that differs between conditions is the text produced here for the tool catalog.
JSON arms render an array of OpenAI-style function objects; TSCG renders the official compiler
output. Tool order is always the catalog's presentation order.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
ARMS = ["raw", "minified", "normalized", "tscg", "tscg_info"]
JSON_ARMS = {"raw": 2, "minified": None, "normalized": 2, "tscg_info": 2}  # indent

_cache: dict = {}


def load_arm(arm: str) -> dict:
    if arm not in _cache:
        path = os.path.join(EXP, "representations", arm, "tools.v1.jsonl")
        _cache[arm] = {json.loads(l)["tool_id"]: json.loads(l) for l in open(path)}
    return _cache[arm]


def render_tool(arm: str, tool_id: str) -> str:
    rec = load_arm(arm)[tool_id]
    if arm == "tscg":
        return rec["text"]
    if arm == "minified":
        return json.dumps(rec["tool"], ensure_ascii=False, separators=(",", ":"))
    return json.dumps(rec["tool"], ensure_ascii=False, indent=2)


def render_catalog(arm: str, tool_ids: list[str]) -> str:
    recs = load_arm(arm)
    if arm == "tscg":
        # verified: official compress(catalog) == "\n\n".join(compress([tool])) under 'conservative'
        return "\n\n".join(recs[t]["text"] for t in tool_ids)
    objs = [recs[t]["tool"] for t in tool_ids]
    if arm == "minified":
        return json.dumps(objs, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(objs, ensure_ascii=False, indent=2)
