"""Strict deployment routing. This API has no task, gold, or evaluator argument."""
import json
import math
import jsonschema


def strict_loads(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key: ' + key)
            result[key] = value
        return result

    def constant(value):
        raise ValueError('non-finite number: ' + value)

    value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)

    def finite(node):
        if isinstance(node, float) and not math.isfinite(node):
            raise ValueError('non-finite number')
        if isinstance(node, dict):
            for child in node.values():
                finite(child)
        elif isinstance(node, list):
            for child in node:
                finite(child)
    finite(value)
    return value


def route(raw_content, tools, *, truncated=False):
    """tools maps catalog tool names to original schemas. Return retry decision, not a score."""
    if truncated:
        return {'retry': True, 'reason': 'truncated', 'call': None}
    try:
        call = strict_loads(raw_content)
    except (ValueError, TypeError, RecursionError) as exc:
        return {'retry': True, 'reason': 'strict_json: ' + str(exc), 'call': None}
    if not isinstance(call, dict) or set(call) != {'tool', 'arguments'} or not isinstance(call['tool'], str):
        return {'retry': True, 'reason': 'envelope', 'call': None}
    if call['tool'] not in tools:
        return {'retry': True, 'reason': 'tool_not_in_catalog', 'call': call}
    schema = tools[call['tool']]
    validator = jsonschema.validators.validator_for(schema, default=jsonschema.Draft7Validator)
    if not validator(schema).is_valid(call['arguments']):
        return {'retry': True, 'reason': 'raw_schema', 'call': call}
    return {'retry': False, 'reason': 'valid', 'call': call}
