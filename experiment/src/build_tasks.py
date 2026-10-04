"""Compile the frozen task source into tasks/tasks.v1.jsonl with full validation.

Checks: gold args validate against the RAW schema; leakage audit on every prompt (tool name,
spaced tool name, schema ID / file name, dataset subset names, representation names,
>=6-word verbatim overlap with the tool description or any schema description text).
Each task record lists the catalogs in which it is evaluated (all sizes of its replicate).
"""
from __future__ import annotations

import json
import os
import re
import sys

import jsonschema

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_utils as su  # noqa: E402

REP_NAMES = ["raw", "minified", "normalized", "tscg", "tscg_info", "json schema", "representation"]
SUBSET_WORDS = ["glaive", "github", "snowplow", "washington post", "jsonschemabench", "kubernetes", "schemastore"]


def leaf_paths(obj, prefix=""):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out.update(leaf_paths(v, f"{prefix}.{k}" if prefix else k))
        return out
    if isinstance(obj, list):
        out = {}
        for i, v in enumerate(obj):
            out.update(leaf_paths(v, f"{prefix}[{i}]"))
        return out or {prefix: []}
    return {prefix: obj}


def schema_texts(s):
    out = []
    if isinstance(s, dict):
        for k, v in s.items():
            if k in ("description", "title") and isinstance(v, str):
                out.append(v)
            out += schema_texts(v)
    elif isinstance(s, list):
        for v in s:
            out += schema_texts(v)
    return out


def ngrams(text, n=6):
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def leakage(prompt, tool, schema):
    p = prompt.lower()
    issues = []
    name = tool["tool_name"]
    if name in p:
        issues.append("tool_name")
    if name.replace("_", " ") in p:
        issues.append("spaced_tool_name")
    sid = tool["schema_id"].lower()
    if sid in p or sid.split("/")[1] in p:
        issues.append("schema_id")
    if tool["tool_id"].lower() in p.split():
        issues.append("tool_id")
    for w in SUBSET_WORDS:
        if w in p:
            issues.append("dataset_identifier:" + w)
    for w in REP_NAMES:
        if re.search(r"\b" + re.escape(w) + r"\b", p):
            issues.append("representation_name:" + w)
    pg = ngrams(prompt)
    if pg & ngrams(tool["description"]):
        issues.append("copies_tool_description")
    for t in schema_texts(schema):
        if pg & ngrams(t):
            issues.append("copies_schema_text")
            break
    return issues


def main():
    src = json.load(open(os.path.join(su.EXP, "tasks", "tasks_source.v1.json")))
    pool = {json.loads(l)["tool_id"]: json.loads(l) for l in open(os.path.join(su.EXP, "dataset", "tool_pool.v1.jsonl"))}
    cats = json.load(open(os.path.join(su.EXP, "catalogs", "catalogs.v1.json")))["catalogs"]
    targets = json.load(open(os.path.join(su.EXP, "catalogs", "targets.v1.json")))
    rep_of = {t["tool_id"]: int(r) for r, v in targets.items() for t in v}
    assert sorted(rep_of) == sorted(t["tool_id"] for t in src["tasks"]), "every target needs exactly one task entry"
    out, problems = [], []
    for entry in src["tasks"]:
        tool = pool[entry["tool_id"]]
        schema = su.load_schema(tool["schema_id"])
        V = jsonschema.validators.validator_for(schema, default=jsonschema.Draft7Validator)
        errs = list(V(schema).iter_errors(entry["gold_args"]))
        if errs:
            problems.append((entry["tool_id"], "gold_invalid", [e.message for e in errs]))
        r = rep_of[entry["tool_id"]]
        cat_ids = [c["catalog_id"] for c in cats if c["replicate"] == r]
        for pi, prompt in enumerate(entry["prompts"]):
            issues = leakage(prompt, tool, schema)
            if issues:
                problems.append((entry["tool_id"], pi, issues))
            out.append({
                "task_id": f"{entry['tool_id']}_p{pi}",
                "tool_id": entry["tool_id"], "acceptable_tool_ids": [entry["tool_id"]],
                "tool_name": tool["tool_name"], "schema_id": tool["schema_id"], "stratum": tool["stratum"],
                "replicate": r, "catalog_ids": cat_ids, "paraphrase_index": pi, "intent_id": entry["tool_id"],
                "prompt": prompt, "gold_args": entry["gold_args"],
                "gold_leaf_paths": sorted(leaf_paths(entry["gold_args"])),
                "unordered_paths": entry.get("unordered_paths", []),
                "acceptable_variants": entry.get("acceptable_variants", {}),
                "expected_semantic_outcome": "mock returns sha256 of the canonicalized gold arguments",
                "task_generation": {"source": "tasks/tasks_source.v1.json", "method": "manual authoring, frozen",
                                    "seed": None, "version": src["version"]},
            })
    if problems:
        for p in problems:
            print("PROBLEM", p)
        sys.exit(1)
    with open(os.path.join(su.EXP, "tasks", "tasks.v1.jsonl"), "w") as f:
        for t in out:
            f.write(json.dumps(t, sort_keys=True) + "\n")
    print(f"tasks={len(out)} intents={len(src['tasks'])} leakage_issues=0 gold_valid=all")


if __name__ == "__main__":
    main()
