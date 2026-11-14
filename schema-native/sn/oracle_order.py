"""Oracle serialization diagnostic: reorder property maps, never assertions or branches."""
import copy
import json
from .router import route


def sorted_serialization(schema):
    return json.dumps(schema, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def reorder_envelope(schema, raw_content, tools, *, truncated=False):
    result = copy.deepcopy(schema)
    decision = route(raw_content, tools, truncated=truncated)
    flags = {'oracle_not_applied': decision['retry'], 'oracle_incomplete': False,
             'reason': decision['reason'], 'array_disagreements': []}
    if decision['retry']:
        return result, flags
    call = decision['call']
    branches = result.get('anyOf', [result])
    matches = [b for b in branches if isinstance(b, dict) and
               b.get('properties', {}).get('tool', {}).get('const') == call['tool']]
    if len(matches) != 1:
        flags.update(oracle_not_applied=True, reason='named_branch_missing_or_ambiguous')
        return result, flags

    def signature(value):
        if isinstance(value, dict):
            return ('object', tuple(value), tuple((k, signature(v)) for k, v in value.items()))
        if isinstance(value, list):
            return ('array', tuple(signature(v) for v in value))
        return 'scalar'

    def walk(node, value, path):
        if not isinstance(node, dict):
            return
        props = node.get('properties')
        if isinstance(props, dict):
            observed = value if isinstance(value, dict) else {}
            keys = [k for k in observed if k in props] + [k for k in props if k not in observed]
            node['properties'] = {k: props[k] for k in keys}
            for key in keys:
                walk(node['properties'][key], observed.get(key), path + '/' + key)
        # Every branch receives the same observation; no branch is chosen or pruned.
        for keyword in ('allOf', 'anyOf', 'oneOf'):
            for branch in node.get(keyword, []):
                walk(branch, value, path)
        for keyword in ('not', 'if', 'then', 'else'):
            if keyword in node:
                walk(node[keyword], value, path)
        for keyword in ('dependentSchemas', 'dependencies'):
            for child in node.get(keyword, {}).values():
                if isinstance(child, dict):
                    walk(child, value, path)
        values = value if isinstance(value, list) else []
        # Draft-4/7 tuple items and 2020 prefixItems are reordered per position.
        tuple_items = node.get('prefixItems', node.get('items'))
        if isinstance(tuple_items, list):
            for index, item in enumerate(tuple_items):
                walk(item, values[index] if index < len(values) else None, path + '/' + str(index))
            tail = node.get('items') if 'prefixItems' in node else node.get('additionalItems')
            tail_values = values[len(tuple_items):]
            if isinstance(tail, dict):
                homogeneous(tail, tail_values, path + '/tail')
        elif isinstance(node.get('items'), dict):
            homogeneous(node['items'], values, path + '/items')

    def homogeneous(item, values, path):
        if values and any(signature(v) != signature(values[0]) for v in values[1:]):
            flags['oracle_incomplete'] = True
            flags['array_disagreements'].append(path)
        walk(item, values[0] if values else None, path)

    walk(matches[0], call, '')
    if sorted_serialization(result) != sorted_serialization(schema):
        raise ValueError('Oracle changed schema assertions')
    return result, flags
