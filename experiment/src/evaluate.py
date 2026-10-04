"""Deterministic evaluation of one model output against one task.

Identical code for every representation condition. Arguments are always validated against the
RAW schema (the true API contract), whatever representation the model saw.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

import jsonschema

TOOL_KEYS = ("tool", "name", "function", "tool_name")
ARG_KEYS = ("arguments", "args", "parameters", "input")

# ------------------------------------------------------------------ parsing


def _strip(content: str) -> str:
    c = re.sub(r"<think>.*?</think>", "", content or "", flags=re.S).strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", c, flags=re.S)
    return m.group(1).strip() if m else c


def _first_balanced(s: str) -> list[str]:
    """All top-level balanced {...} substrings (string-aware)."""
    out, depth, start, in_str, esc = [], 0, None, False, False
    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0:
                out.append(s[start:i + 1])
    return out


def parse_output(content: str) -> dict:
    r = {"json_valid": False, "json_strict": False, "n_json_objects": 0, "tool": None, "arguments": None,
         "format_ok": False, "format_alias_used": False, "arguments_was_string": False, "multiple_calls": False}
    body = _strip(content)
    obj = None
    try:
        obj = json.loads(body)
        r["json_strict"] = True
    except Exception:
        cands = []
        for frag in _first_balanced(body):
            try:
                cands.append(json.loads(frag))
            except Exception:
                pass
        r["n_json_objects"] = len(cands)
        if cands:
            obj = cands[0]
            r["multiple_calls"] = len(cands) > 1
    if isinstance(obj, list):
        r["multiple_calls"] = len(obj) > 1
        obj = obj[0] if obj and isinstance(obj[0], dict) else None
    if not isinstance(obj, dict):
        return r
    r["json_valid"] = True
    r["n_json_objects"] = max(r["n_json_objects"], 1)
    tk = next((k for k in TOOL_KEYS if k in obj), None)
    ak = next((k for k in ARG_KEYS if k in obj), None)
    if tk and isinstance(obj[tk], dict) and "name" in obj[tk]:  # {"function": {"name":..., "arguments":...}}
        inner = obj[tk]
        r["tool"] = inner.get("name")
        args = inner.get("arguments", inner.get("parameters"))
        r["format_alias_used"] = True
    else:
        r["tool"] = obj.get(tk) if tk else None
        args = obj.get(ak) if ak else None
        r["format_alias_used"] = (tk not in (None, "tool")) or (ak not in (None, "arguments"))
    if isinstance(args, str):
        try:
            args = json.loads(args)
            r["arguments_was_string"] = True
        except Exception:
            pass
    r["arguments"] = args
    r["format_ok"] = isinstance(r["tool"], str) and isinstance(args, dict)
    return r


# ------------------------------------------------------------------ comparison


def _norm_str(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().casefold()).rstrip(".")


def scalar_exact(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return a == b


def scalar_semantic(pred, gold) -> bool:
    if scalar_exact(pred, gold):
        return True
    if isinstance(pred, str) and isinstance(gold, str):
        return _norm_str(pred) == _norm_str(gold)
    # cross-type scalar coercion ("300" ~ 300, "true" ~ true, "0.5" ~ 0.5)
    if isinstance(pred, (str, int, float, bool)) and isinstance(gold, (str, int, float, bool)):
        ps = json.dumps(pred) if not isinstance(pred, str) else pred
        gs = json.dumps(gold) if not isinstance(gold, str) else gold
        try:
            return float(ps) == float(gs)
        except ValueError:
            return _norm_str(ps) == _norm_str(gs)
    return False


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


def _get(obj, path):
    for tok in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        if tok.startswith("["):
            i = int(tok[1:-1])
            if not isinstance(obj, list) or i >= len(obj):
                return KeyError
            obj = obj[i]
        else:
            if not isinstance(obj, dict) or tok not in obj:
                return KeyError
            obj = obj[tok]
    return obj


def _set(obj, path, value):
    toks = re.findall(r"[^.\[\]]+|\[\d+\]", path)
    for tok in toks[:-1]:
        obj = obj[int(tok[1:-1])] if tok.startswith("[") else obj[tok]
    last = toks[-1]
    if last.startswith("["):
        obj[int(last[1:-1])] = value
    else:
        obj[last] = value


def _elem_score(p, g) -> int:
    gp = leaf_paths(g)
    return sum(1 for k, v in gp.items() if (pv := _get(p, k)) is not KeyError and scalar_semantic(pv, v))


def align_unordered(pred: Any, gold: Any, unordered_paths: list[str]) -> Any:
    """Reorder predicted arrays at unordered paths to best match gold (greedy). Returns a copy."""
    pred = copy.deepcopy(pred)
    for path in unordered_paths:
        pa, ga = _get(pred, path), _get(gold, path)
        if not isinstance(pa, list) or not isinstance(ga, list):
            continue
        remaining = list(range(len(pa)))
        new = []
        for g in ga:
            if not remaining:
                break
            best = max(remaining, key=lambda i: (_elem_score(pa[i], g) if isinstance(g, (dict, list)) else int(scalar_semantic(pa[i], g)), -i))
            new.append(pa[best])
            remaining.remove(best)
        new += [pa[i] for i in remaining]
        _set(pred, path, new)
    return pred


def compare_args(pred: dict, task: dict) -> dict:
    gold = task["gold_args"]
    aligned = align_unordered(pred, gold, task.get("unordered_paths", []))
    gl = leaf_paths(gold)
    variants = task.get("acceptable_variants", {})
    per_field, exact_fields = {}, {}
    for path, gv in gl.items():
        pv = _get(aligned, path)
        if pv is KeyError:
            per_field[path], exact_fields[path] = False, False
            continue
        alts = [gv] + variants.get(path, [])
        per_field[path] = any(scalar_semantic(pv, a) if not isinstance(a, list) else pv == a for a in alts)
        exact_fields[path] = any(scalar_exact(pv, a) if not isinstance(a, list) else pv == a for a in alts)
    pl = leaf_paths(aligned)
    extra = sorted(p for p in pl if p not in gl and not any(p.startswith(g + "[") or p.startswith(g + ".") for g in gl))
    n = len(gl)
    exact = all(exact_fields.values()) and not extra and _same_shape(aligned, gold)
    return {"field_semantic": per_field, "field_acc": sum(per_field.values()) / n if n else 1.0,
            "field_exact_acc": sum(exact_fields.values()) / n if n else 1.0,
            "semantic_correct": all(per_field.values()), "exact_match": exact, "extra_paths": extra,
            "aligned_args": aligned}


def _same_shape(a, b) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_same_shape(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same_shape(x, y) for x, y in zip(a, b))
    return not isinstance(a, (dict, list)) and not isinstance(b, (dict, list))


# ------------------------------------------------------------------ schema validation / mock


def schema_errors(args: Any, schema: dict) -> list[dict]:
    V = jsonschema.validators.validator_for(schema, default=jsonschema.Draft7Validator)
    errs = []
    for e in V(schema).iter_errors(args):  # format is an annotation (not asserted), as in the spec default
        errs.append({"validator": e.validator, "path": "/".join(map(str, e.absolute_path)), "message": e.message[:300]})
    return errs


def schema_property_names(schema: Any) -> set:
    names = set()
    if isinstance(schema, dict):
        for k, v in schema.items():
            if k == "properties" and isinstance(v, dict):
                names |= set(v)
            names |= schema_property_names(v)
    elif isinstance(schema, list):
        for v in schema:
            names |= schema_property_names(v)
    return names


def _canon_norm(obj):
    if isinstance(obj, dict):
        return {k: _canon_norm(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_canon_norm(v) for v in obj]
    if isinstance(obj, str):
        return _norm_str(obj)
    if isinstance(obj, bool) or obj is None:
        return obj
    return float(obj)


def mock_execute(tool_name: str, args: dict, catalog_tool_names: set, raw_schema: dict, task: dict) -> dict:
    """Deterministic mock API. Rejects unknown tools and schema-invalid arguments; otherwise returns a
    receipt = sha256 of the canonicalized task-relevant argument values (normalized). The final task
    succeeds iff the receipt equals the receipt of the gold arguments."""
    if tool_name not in catalog_tool_names:
        return {"status": "error", "error": "unknown_tool"}
    errs = schema_errors(args, raw_schema)
    if errs:
        return {"status": "error", "error": "invalid_arguments", "n_errors": len(errs)}
    aligned = align_unordered(args, task["gold_args"], task.get("unordered_paths", []))
    relevant = {}
    for path, gv in leaf_paths(task["gold_args"]).items():
        pv = _get(aligned, path)
        alts = [gv] + task.get("acceptable_variants", {}).get(path, [])
        # map an accepted variant/semantically-equal value onto the gold value (normalization layer)
        relevant[path] = gv if pv is not KeyError and any(scalar_semantic(pv, a) for a in alts if not isinstance(a, list)) else pv if pv is not KeyError else "__MISSING__"
    receipt = hashlib.sha256(json.dumps(_canon_norm(relevant), sort_keys=True).encode()).hexdigest()
    expected = hashlib.sha256(json.dumps(_canon_norm(leaf_paths(task["gold_args"])), sort_keys=True).encode()).hexdigest()
    return {"status": "ok", "receipt": receipt, "expected_receipt": expected, "final_success": receipt == expected}


# ------------------------------------------------------------------ failure taxonomy

SCHEMA_ERR_MAP = [("required", "missing required argument"), ("type", "invalid argument type"),
                  ("enum", "invalid enum/value"), ("const", "invalid enum/value"),
                  ("additionalProperties", "hallucinated field")]


def classify(parsed, tool_ok, errs, cmp, exec_res, hallucinated_keys, context_error) -> tuple[str | None, list[str]]:
    sec: list[str] = []
    if context_error:
        return "context-length failure", sec
    if not parsed["json_valid"] or not parsed["format_ok"]:
        return "malformed output", sec
    if parsed["multiple_calls"]:
        sec.append("multiple-tool confusion")
    if not tool_ok:
        prim = "multiple-tool confusion" if parsed["multiple_calls"] else "wrong tool"
        return prim, [s for s in sec if s != prim]
    cats = []
    for e in errs:
        cats.append(next((c for v, c in SCHEMA_ERR_MAP if e["validator"] == v), "ignored schema constraint"))
    order = ["missing required argument", "invalid argument type", "invalid enum/value", "hallucinated field",
             "ignored schema constraint"]
    cats = sorted(set(cats), key=order.index)
    if hallucinated_keys and "hallucinated field" not in cats:
        sec.append("hallucinated field")
    if cmp and not cmp["semantic_correct"]:
        sec_sem = "correct tool, wrong argument"
    else:
        sec_sem = None
    if cats:
        prim = cats[0]
        sec += cats[1:] + ([sec_sem] if sec_sem else [])
        return prim, sec
    if sec_sem:
        return sec_sem, sec
    if exec_res.get("status") != "ok":
        return "execution failure", sec
    if not exec_res.get("final_success"):
        return "semantic/task failure", sec
    return None, sec


def evaluate(content: str, task: dict, raw_schema: dict, catalog_tool_names: set,
             context_error: bool = False) -> dict:
    parsed = parse_output(content) if not context_error else parse_output("")
    tool_ok = parsed["format_ok"] and parsed["tool"] == task["tool_name"]
    errs, cmp, exec_res, halluc = [], None, {"status": "not_executed"}, []
    if parsed["format_ok"]:
        args = parsed["arguments"]
        if tool_ok:
            errs = schema_errors(args, raw_schema)
            cmp = compare_args(args, task)
            known = schema_property_names(raw_schema)
            halluc = sorted({p.split(".")[-1].split("[")[0] for p in leaf_paths(args)} - known - {""})
            exec_res = mock_execute(parsed["tool"], args, catalog_tool_names, raw_schema, task)
        else:
            exec_res = {"status": "error", "error": "unknown_tool"} if parsed["tool"] not in catalog_tool_names else {"status": "wrong_tool_executed"}
    primary, secondary = classify(parsed, tool_ok, errs, cmp, exec_res, halluc, context_error)
    schema_valid = tool_ok and not errs
    return {
        "json_valid": parsed["json_valid"], "json_strict": parsed["json_strict"], "format_ok": parsed["format_ok"],
        "format_alias_used": parsed["format_alias_used"], "multiple_calls": parsed["multiple_calls"],
        "pred_tool": parsed["tool"], "pred_args": parsed["arguments"],
        "pred_tool_in_catalog": parsed["tool"] in catalog_tool_names if parsed["tool"] else False,
        "tool_correct": tool_ok,
        "schema_valid": schema_valid, "schema_errors": errs,
        "arg_exact_match": bool(cmp and cmp["exact_match"]),
        "field_acc": cmp["field_acc"] if cmp else 0.0,
        "field_exact_acc": cmp["field_exact_acc"] if cmp else 0.0,
        "semantic_correct": bool(cmp and cmp["semantic_correct"]),
        "field_semantic": cmp["field_semantic"] if cmp else {},
        "hallucinated_keys": halluc,
        "execution_status": exec_res.get("status"),
        "execution_success": exec_res.get("status") == "ok",
        "e2e_success": bool(tool_ok and schema_valid and exec_res.get("final_success")),
        "failure_primary": primary, "failure_secondary": secondary,
    }
