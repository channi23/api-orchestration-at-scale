"""Shared JSON Schema utilities: loading, local $ref dereferencing, feature extraction.

All functions are deterministic and pure (no network). Only *local* references
("#", "#/definitions/...", "#/$defs/...", any "#/<json-pointer>") are resolved;
anything else is reported as non-local.
"""
from __future__ import annotations

import copy
import glob
import hashlib
import json
import os
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
DATA_DIR = os.path.join(EXP, "dataset", "upstream", "jsonschemabench", "data")

SUBSETS = ["Glaiveai2K", "Github_trivial", "Github_easy", "Github_medium", "Github_hard",
           "Github_ultra", "JsonSchemaStore", "Kubernetes", "Snowplow", "WashingtonPost"]

# Keywords whose subtrees are schemas (used for walking).
SCHEMA_MAP_KEYS = ("properties", "patternProperties", "definitions", "$defs", "dependentSchemas")
SCHEMA_LIST_KEYS = ("allOf", "anyOf", "oneOf", "prefixItems")
SCHEMA_SINGLE_KEYS = ("items", "additionalProperties", "additionalItems", "not", "if", "then",
                      "else", "contains", "propertyNames", "unevaluatedProperties",
                      "unevaluatedItems")
CONSTRAINT_KEYS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
                   "minLength", "maxLength", "pattern", "format", "minItems", "maxItems",
                   "uniqueItems", "minProperties", "maxProperties", "const", "default")
NON_SEMANTIC_ROOT_KEYS = ("$schema", "$id", "$comment")


def schema_id(subset: str, fname: str) -> str:
    return f"{subset}/{fname[:-5] if fname.endswith('.json') else fname}"


def load_all() -> list[tuple[str, Any]]:
    out = []
    for subset in SUBSETS:
        for path in sorted(glob.glob(os.path.join(DATA_DIR, subset, "*.json"))):
            with open(path) as f:
                out.append((schema_id(subset, os.path.basename(path)), json.load(f)))
    return out


def load_schema(sid: str) -> Any:
    subset, name = sid.split("/", 1)
    with open(os.path.join(DATA_DIR, subset, name + ".json")) as f:
        return json.load(f)


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(obj: Any) -> str:
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


# ---------------------------------------------------------------- $ref handling
class RefError(Exception):
    pass


class CyclicRef(RefError):
    pass


def _pointer(root: Any, ref: str) -> Any:
    if ref == "#":
        return root
    if not ref.startswith("#/"):
        raise RefError(f"non-local ref {ref!r}")
    node = root
    for tok in ref[2:].split("/"):
        tok = tok.replace("~1", "/").replace("~0", "~")
        from urllib.parse import unquote
        tok = unquote(tok)
        if isinstance(node, list):
            node = node[int(tok)]
        elif isinstance(node, dict) and tok in node:
            node = node[tok]
        else:
            raise RefError(f"unresolvable ref {ref!r}")
    return node


def iter_refs(s: Any):
    if isinstance(s, dict):
        r = s.get("$ref")
        if isinstance(r, str):
            yield r
        for v in s.values():
            yield from iter_refs(v)
    elif isinstance(s, list):
        for v in s:
            yield from iter_refs(v)


def dereference(root: Any) -> Any:
    """Return a copy of `root` with every local $ref inlined.

    Sibling keywords next to $ref are merged over the resolved target (siblings win).
    Raises CyclicRef for recursive schemas and RefError for non-local/unresolvable refs.
    """

    def rec(node: Any, stack: tuple[str, ...]) -> Any:
        if isinstance(node, dict):
            if isinstance(node.get("$ref"), str):
                ref = node["$ref"]
                if ref in stack:
                    raise CyclicRef(ref)
                target = rec(copy.deepcopy(_pointer(root, ref)), stack + (ref,))
                siblings = {k: rec(v, stack) for k, v in node.items() if k != "$ref"}
                if isinstance(target, dict):
                    merged = dict(target)
                    merged.update(siblings)
                    return merged
                return target
            return {k: rec(v, stack) for k, v in node.items()}
        if isinstance(node, list):
            return [rec(v, stack) for v in node]
        return node

    return rec(root, ())


def normalize(root: dict) -> dict:
    """NORMALIZED representation: dereference, then drop definition containers and
    non-semantic root metadata. Nothing else is changed (order preserved)."""
    d = dereference(root)
    for k in ("definitions", "$defs") + NON_SEMANTIC_ROOT_KEYS:
        d.pop(k, None)
    if isinstance(d.get("id"), str):  # draft-4 style root id
        d.pop("id")
    return d


# ---------------------------------------------------------------- features
def _types(s: dict) -> list[str]:
    t = s.get("type")
    if isinstance(t, str):
        return [t]
    if isinstance(t, list):
        return [x for x in t if isinstance(x, str)]
    return []


def features(s: Any) -> dict:
    f = {k: False for k in ("has_ref", "has_enum", "has_oneOf", "has_anyOf", "has_allOf",
                            "has_not", "has_conditional", "has_patternProperties",
                            "has_constraints", "has_array", "has_array_of_objects",
                            "has_nested_object", "has_format", "has_pattern", "has_const",
                            "has_additionalProperties_false", "has_default")}
    f["max_depth"] = 0
    f["n_schema_nodes"] = 0

    def walk(node: Any, depth: int):
        if isinstance(node, list):
            for x in node:
                walk(x, depth)
            return
        if not isinstance(node, dict):
            return
        f["n_schema_nodes"] += 1
        if "$ref" in node:
            f["has_ref"] = True
        if "enum" in node:
            f["has_enum"] = True
        if "const" in node:
            f["has_const"] = True
        for kw, key in (("oneOf", "has_oneOf"), ("anyOf", "has_anyOf"), ("allOf", "has_allOf"),
                        ("not", "has_not"), ("patternProperties", "has_patternProperties")):
            if kw in node:
                f[key] = True
        if any(k in node for k in ("if", "then", "else", "dependencies", "dependentSchemas",
                                   "dependentRequired")):
            f["has_conditional"] = True
        if any(k in node for k in CONSTRAINT_KEYS if k not in ("default", "const")):
            f["has_constraints"] = True
        if "format" in node:
            f["has_format"] = True
        if "pattern" in node:
            f["has_pattern"] = True
        if "default" in node:
            f["has_default"] = True
        if node.get("additionalProperties") is False:
            f["has_additionalProperties_false"] = True
        types = _types(node)
        if "array" in types or "items" in node:
            f["has_array"] = True
            it = node.get("items")
            if isinstance(it, dict) and ("properties" in it or "object" in _types(it)):
                f["has_array_of_objects"] = True
        props = node.get("properties")
        if isinstance(props, dict):
            if depth >= 1 and props:
                f["has_nested_object"] = True
            f["max_depth"] = max(f["max_depth"], depth + 1)
            for v in props.values():
                walk(v, depth + 1)
        for k in SCHEMA_MAP_KEYS:
            if k != "properties" and isinstance(node.get(k), dict):
                for v in node[k].values():
                    walk(v, depth)
        for k in SCHEMA_LIST_KEYS:
            if isinstance(node.get(k), list):
                walk(node[k], depth)
        for k in SCHEMA_SINGLE_KEYS:
            if isinstance(node.get(k), dict):
                walk(node[k], depth + (1 if k == "items" else 0))

    walk(s, 0)
    return f


def top_level_info(s: dict) -> dict:
    props = s.get("properties") if isinstance(s, dict) else None
    props = props if isinstance(props, dict) else {}
    req = s.get("required") if isinstance(s.get("required"), list) else []
    structured_props = []
    for name, p in props.items():
        if not isinstance(p, dict):
            continue
        t = _types(p)
        if ("object" in t or "array" in t or "properties" in p or "items" in p or "$ref" in p
                or any(k in p for k in ("oneOf", "anyOf", "allOf"))):
            structured_props.append(name)
    return {
        "n_top_props": len(props),
        "n_required": len([r for r in req if r in props]),
        "structured_top_props": structured_props,
        "stratum": "structured" if structured_props else "flat",
        "has_title_or_description": bool(isinstance(s, dict) and (s.get("title") or s.get("description"))),
    }


def _unsat_node(s: dict) -> bool:
    if "oneOf" not in s or not isinstance(s.get("required"), list):
        return False
    req = set(s["required"])
    branches = [b for b in s["oneOf"] if isinstance(b, dict)]
    if len(branches) < 2:
        return False
    branch_keys = [set(b.get("required", [])) | set((b.get("properties") or {}).keys()) for b in branches]
    return all(k and k <= req for k in branch_keys)


def tscg_glaive_unsat_pattern(s) -> bool:
    """Detect the documented GlaiveAI unsatisfiable pattern (upstream issue #16) at any depth:
    an object's `required` lists the keys of *every* oneOf branch, so whenever `required` is
    satisfied all branches match and oneOf (exactly one) fails."""
    if isinstance(s, dict):
        if _unsat_node(s):
            return True
        return any(tscg_glaive_unsat_pattern(v) for v in s.values())
    if isinstance(s, list):
        return any(tscg_glaive_unsat_pattern(v) for v in s)
    return False
