"""Build the five representation conditions for every pooled tool and audit TSCG information change.

Outputs:
  representations/<arm>/tools.v1.jsonl     per-tool representation (+ transform time)
  representations/tscg/catalog_check.v1.json   whole-catalog TSCG output == per-tool join? + timing
  representations/tscg/information_audit.v1.jsonl / .summary.json   what TSCG removed/changed
  representations/manifest.v1.json          versions, options, sha256 of every artifact
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_utils as su  # noqa: E402

REP = os.path.join(su.EXP, "representations")
TIMING_REPS = 15


def timed(fn, *a):
    ts, res = [], None
    for _ in range(TIMING_REPS):
        t0 = time.perf_counter()
        res = fn(*a)
        ts.append((time.perf_counter() - t0) * 1000)
    return res, statistics.median(ts)


def tool_obj(t, params):
    return {"type": "function", "function": {"name": t["tool_name"], "description": t["description"], "parameters": params}}


def json_types(s):
    if not isinstance(s, dict):
        return []
    t = s.get("type")
    if isinstance(t, str):
        return [t]
    if isinstance(t, list):
        return list(t)
    if "enum" in s:
        m = {bool: "boolean", int: "integer", float: "number", str: "string", type(None): "null"}
        return sorted({m.get(type(v), "object") for v in s["enum"]})
    if "properties" in s:
        return ["object"]
    if "items" in s:
        return ["array"]
    return []


def tscg_info_params(sdm_params: dict) -> dict:
    """JSON Schema containing exactly what @tscg/core normalizeToInternal keeps:
    top-level property name, type (missing -> 'string'), description (SDM-rewritten), enum,
    and required flag for properties that exist."""
    props = sdm_params.get("properties") or {}
    req = sdm_params.get("required") or []
    out_props = {}
    for name, p in props.items():
        p = p if isinstance(p, dict) else {}
        q = {"type": p.get("type") or "string"}
        if p.get("description"):
            q["description"] = p["description"]
        if p.get("enum") is not None:
            q["enum"] = p["enum"]
        out_props[name] = q
    out = {"type": "object", "properties": out_props}
    r = [x for x in req if x in props]
    if r:
        out["required"] = r
    return out


def info_audit(t, raw, norm, sdm_tool):
    sdm_params = sdm_tool["function"]["parameters"]
    a = {"tool_id": t["tool_id"], "stratum": t["stratum"]}
    props = raw.get("properties") or {}
    nprops = norm.get("properties") or {}
    req = raw.get("required") or []
    a["n_top_props"] = len(props)
    a["required_not_in_properties"] = [r for r in req if r not in props]
    type_changes, lost_enums, lost_structure = [], [], []
    for name, p in props.items():
        p = p if isinstance(p, dict) else {}
        shown = p.get("type") or "string"
        shown_l = shown if isinstance(shown, list) else [shown]
        actual = json_types(nprops.get(name, {}))
        if actual and sorted(actual) != sorted(shown_l):
            type_changes.append({"param": name, "shown": shown, "actual": actual})
        if "enum" not in p and isinstance(nprops.get(name), dict) and "enum" in nprops[name]:
            lost_enums.append(name)
        np_ = nprops.get(name, {})
        if isinstance(np_, dict) and any(k in np_ for k in ("properties", "items", "oneOf", "anyOf", "allOf", "patternProperties", "additionalProperties")):
            lost_structure.append(name)
    a["type_changes"] = type_changes
    a["lost_enums_behind_ref"] = lost_enums
    a["params_with_dropped_substructure"] = lost_structure
    f = su.features(raw)
    a["dropped_keywords_present"] = sorted(k for k in ("has_ref", "has_oneOf", "has_anyOf", "has_allOf", "has_conditional",
                                                     "has_constraints", "has_format", "has_pattern", "has_default",
                                                     "has_additionalProperties_false", "has_nested_object",
                                                     "has_array_of_objects") if f.get(k))
    titles = [k for k, p in props.items() if isinstance(p, dict) and p.get("title") and not p.get("description")]
    a["title_only_params_dropped_text"] = titles
    rawd = {k: (p.get("description") if isinstance(p, dict) else None) for k, p in props.items()}
    sdmd = {k: (p.get("description") if isinstance(p, dict) else None) for k, p in (sdm_params.get("properties") or {}).items()}
    a["param_descriptions_rewritten"] = sorted(k for k in rawd if rawd[k] and rawd[k] != sdmd.get(k))
    a["tool_description_rewritten"] = sdm_tool["function"]["description"] != t["description"]
    a["root_description_dropped"] = bool(raw.get("description") or raw.get("title"))
    a["lossless_except_text"] = not (type_changes or lost_enums or lost_structure or a["required_not_in_properties"]
                                     or set(a["dropped_keywords_present"]) - {"has_format"} or titles)
    return a


def sha_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    pool = [json.loads(l) for l in open(os.path.join(su.EXP, "dataset", "tool_pool.v1.jsonl"))]
    for arm in ("raw", "minified", "normalized", "tscg", "tscg_info"):
        os.makedirs(os.path.join(REP, arm), exist_ok=True)

    raw_schemas = {t["tool_id"]: su.load_schema(t["schema_id"]) for t in pool}
    recs = collections.defaultdict(list)
    for t in pool:
        raw = raw_schemas[t["tool_id"]]
        obj = tool_obj(t, raw)
        _, ms_raw = timed(lambda o: json.dumps(o, ensure_ascii=False, indent=2), obj)
        _, ms_min = timed(lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")), obj)
        norm, ms_norm = timed(su.normalize, raw)
        recs["raw"].append({"tool_id": t["tool_id"], "tool": obj, "transform_ms_median": ms_raw})
        recs["minified"].append({"tool_id": t["tool_id"], "tool": obj, "transform_ms_median": ms_min})
        recs["normalized"].append({"tool_id": t["tool_id"], "tool": tool_obj(t, norm), "transform_ms_median": ms_norm})

    # ---- official TSCG via node
    inp = os.path.join(REP, "tscg", "_input_tools.json")
    json.dump([{"tool_id": t["tool_id"], "tool": tool_obj(t, raw_schemas[t["tool_id"]])} for t in pool], open(inp, "w"))
    cats = json.load(open(os.path.join(su.EXP, "catalogs", "catalogs.v1.json")))["catalogs"]
    cin = os.path.join(REP, "tscg", "_input_catalogs.json")
    json.dump([{"catalog_id": c["catalog_id"], "order": c["presentation_order"]} for c in cats], open(cin, "w"))
    proc = subprocess.run(["node", os.path.join(REP, "tscg", "run_tscg.mjs"), inp, cin],
                          cwd=os.path.join(REP, "tscg"), capture_output=True, text=True, check=True)
    res = json.loads(proc.stdout)
    os.remove(inp)
    os.remove(cin)
    by = {r["tool_id"]: r for r in res["tools"]}
    audits = []
    for t in pool:
        r = by[t["tool_id"]]
        raw = raw_schemas[t["tool_id"]]
        recs["tscg"].append({"tool_id": t["tool_id"], "text": r["compressed"], "transform_ms_median": r["compress_ms_median"],
                             "applied_principles": r["applied"], "tscg_reported_tokens": r["tscg_metrics"]})
        t0 = time.perf_counter()
        info = tool_obj({"tool_name": r["sdm_tool"]["function"]["name"], "description": r["sdm_tool"]["function"]["description"]},
                        tscg_info_params(r["sdm_tool"]["function"]["parameters"]))
        ms = (time.perf_counter() - t0) * 1000
        recs["tscg_info"].append({"tool_id": t["tool_id"], "tool": info, "transform_ms_median": ms,
                                  "note": "built from official compressDescriptions() output + TSCG field selection"})
        audits.append(info_audit(t, raw, su.normalize(raw), r["sdm_tool"]))
    for arm, rows in recs.items():
        with open(os.path.join(REP, arm, "tools.v1.jsonl"), "w") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    # ---- catalog-level equivalence check (official whole-catalog output vs per-tool join)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import render  # noqa: E402
    render._cache.clear()
    check = []
    for c in res["catalogs"]:
        joined = render.render_catalog("tscg", next(x["presentation_order"] for x in cats if x["catalog_id"] == c["catalog_id"]))
        check.append({"catalog_id": c["catalog_id"], "equal_to_per_tool_join": joined == c["compressed"],
                      "compress_ms_median": c["compress_ms_median"], "applied": c["applied"]})
    assert all(x["equal_to_per_tool_join"] for x in check), "TSCG catalog output differs from per-tool join"
    json.dump(check, open(os.path.join(REP, "tscg", "catalog_check.v1.json"), "w"), indent=1)

    with open(os.path.join(REP, "tscg", "information_audit.v1.jsonl"), "w") as f:
        for a in audits:
            f.write(json.dumps(a, sort_keys=True) + "\n")
    summ = {"n_tools": len(audits)}
    for strat in ("flat", "structured", "all"):
        sel = [a for a in audits if strat == "all" or a["stratum"] == strat]
        summ[strat] = {
            "n": len(sel),
            "lossless_except_text": sum(a["lossless_except_text"] for a in sel),
            "with_type_changes": sum(bool(a["type_changes"]) for a in sel),
            "with_lost_enums_behind_ref": sum(bool(a["lost_enums_behind_ref"]) for a in sel),
            "with_dropped_substructure": sum(bool(a["params_with_dropped_substructure"]) for a in sel),
            "with_required_not_in_properties": sum(bool(a["required_not_in_properties"]) for a in sel),
            "with_dropped_constraints": sum("has_constraints" in a["dropped_keywords_present"] for a in sel),
            "with_dropped_defaults": sum("has_default" in a["dropped_keywords_present"] for a in sel),
            "with_title_only_text_dropped": sum(bool(a["title_only_params_dropped_text"]) for a in sel),
            "with_param_descriptions_rewritten": sum(bool(a["param_descriptions_rewritten"]) for a in sel),
            "with_tool_description_rewritten": sum(a["tool_description_rewritten"] for a in sel),
            "with_root_description_or_title_dropped": sum(a["root_description_dropped"] for a in sel),
        }
    json.dump(summ, open(os.path.join(REP, "tscg", "information_audit.v1.summary.json"), "w"), indent=2)

    manifest = {"tscg": {"package": "@tscg/core", "version": res["version"], "options": res["options"],
                         "invocation": "compress([tool], {model:'qwen-3', profile:'conservative'}) per tool; catalog = '\\n\\n'.join (verified equal to compress(catalog))",
                         "node": res["node"], "repo_commit_inspected": "51378d6c5e2306d82832b7eca3287bc0f29d31d2",
                         "timing_reps": res["reps_for_timing"]},
                "normalized": "local $ref inlined (siblings merged over target), definitions/$defs/$schema/$id/$comment/root id removed; nothing else changed",
                "minified": "identical content to raw, json separators (',',':') and no indentation",
                "raw": "original JSONSchemaBench schema verbatim as `parameters`, json indent=2",
                "tscg_info": "JSON Schema with exactly the fields TSCG keeps (top-level name/type/SDM description/enum/required), tool description SDM-rewritten by official compressDescriptions()",
                "files": {f"{arm}/tools.v1.jsonl": sha_file(os.path.join(REP, arm, "tools.v1.jsonl")) for arm in recs}}
    json.dump(manifest, open(os.path.join(REP, "manifest.v1.json"), "w"), indent=2)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
