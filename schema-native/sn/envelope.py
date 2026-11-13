"""Build the JSON Schema that constrains a whole tool call.

The experiment's output contract is ``{"tool": <name>, "arguments": {...}}``. For constrained
decoding we need ONE self-contained schema for that envelope:

    {"anyOf": [ {"type":"object",
                 "properties": {"tool": {"const": name_i}, "arguments": S_i},
                 "required": ["tool","arguments"], "additionalProperties": false}, ... ]}

``S_i`` is the tool's parameter schema with every local ``$ref`` inlined (the experiment's
``normalize``), because a ``#/definitions/..`` pointer is relative to the tool schema's own root and
would dangle once the schema is nested inside the envelope. Inlining does not change what the
schema accepts (cyclic schemas are excluded from the pool).

This module is deterministic and makes no model calls. Validation of model output is still done
against the ORIGINAL raw schema by the experiment's evaluator, never against this envelope.
"""
from __future__ import annotations

import copy
import json
from typing import Any

from . import constraint_policy
from . import paths  # noqa: F401  (adds experiment/src to sys.path)
import schema_utils as su  # type: ignore  # noqa: E402

# Keywords that only exist, or mean something different, before draft 2019-09 / 2020-12.
LEGACY_KEYWORDS = ("dependencies", "additionalItems", "id", "extends", "divisibleBy", "disallow")

# Keywords an engine must enforce for its output to be valid against the raw schema.
ASSERTION_KEYWORDS = (
    "type", "enum", "const", "required", "properties", "additionalProperties", "patternProperties",
    "propertyNames", "minProperties", "maxProperties", "dependencies", "dependentRequired",
    "dependentSchemas", "items", "prefixItems", "additionalItems", "contains", "minItems", "maxItems",
    "uniqueItems", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "minLength", "maxLength", "pattern", "allOf", "anyOf", "oneOf", "not", "if", "then", "else",
    "unevaluatedProperties", "unevaluatedItems",
)


def argument_schema(raw_schema: dict) -> dict:
    """Self-contained parameter schema: local refs inlined, root metadata dropped."""
    return su.normalize(copy.deepcopy(raw_schema))


def tool_branch(tool_name: str, raw_schema: dict, policy=constraint_policy.ORIGINAL) -> dict:
    return {
        "type": "object",
        "properties": {"tool": {"const": tool_name}, "arguments": constraint_policy.prepare(argument_schema(raw_schema), policy)},
        "required": ["tool", "arguments"],
        "additionalProperties": False,
    }


def envelope(tools: list[tuple[str, dict]], policy=constraint_policy.ORIGINAL) -> dict:
    """tools: [(tool_name, raw_schema), ...] in presentation order."""
    branches = [tool_branch(n, s, policy) for n, s in tools]
    return branches[0] if len(branches) == 1 else {"anyOf": branches}


def keywords_used(schema: Any) -> set[str]:
    """Schema keywords that appear at schema positions (not inside enum/const/default/examples)."""
    out: set[str] = set()

    def rec(node: Any) -> None:
        if isinstance(node, bool) or not isinstance(node, dict):
            return
        for k, v in node.items():
            out.add(k)
            if k in su.SCHEMA_MAP_KEYS and isinstance(v, dict):
                for sub in v.values():
                    rec(sub)
            elif k in su.SCHEMA_LIST_KEYS and isinstance(v, list):
                for sub in v:
                    rec(sub)
            elif k in su.SCHEMA_SINGLE_KEYS:
                if isinstance(v, list):          # draft-4 tuple "items"
                    for sub in v:
                        rec(sub)
                else:
                    rec(v)
            elif k == "dependencies" and isinstance(v, dict):
                for sub in v.values():
                    rec(sub)

    rec(schema)
    return out


def audit(raw_schema: dict) -> dict:
    """What a constrained-decoding engine would have to enforce for this schema."""
    kws = keywords_used(argument_schema(raw_schema))
    return {
        "dialect": raw_schema.get("$schema"),
        "assertion_keywords": sorted(kws & set(ASSERTION_KEYWORDS)),
        "legacy_keywords": sorted(kws & set(LEGACY_KEYWORDS)),
        "has_format": "format" in kws,
    }


def ordered_like_schema(value: Any, schema: Any) -> Any:
    """Re-order object keys to follow the schema's ``properties`` order.

    Several engines emit properties in schema order only. JSON objects are unordered, so this does
    not change the value; it lets us ask "can this engine produce the gold answer at all?".
    """
    if isinstance(value, dict) and isinstance(schema, dict):
        props = schema.get("properties", {}) if isinstance(schema.get("properties"), dict) else {}
        keys = [k for k in props if k in value] + [k for k in value if k not in props]
        return {k: ordered_like_schema(value[k], props.get(k, schema.get("additionalProperties"))) for k in keys}
    if isinstance(value, list) and isinstance(schema, dict):
        items = schema.get("items")
        if isinstance(items, dict):
            return [ordered_like_schema(v, items) for v in value]
    return value


def gold_call(task: dict, raw_schema: dict) -> dict:
    args = ordered_like_schema(task["gold_args"], argument_schema(raw_schema))
    return {"tool": task["tool_name"], "arguments": args}


def dumps_compact(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def dumps_spaced(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)
