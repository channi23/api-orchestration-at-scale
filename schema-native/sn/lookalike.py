"""Diagnostic flags only: never rename keys or change evaluator scores."""
import unicodedata

QUOTES = set('“”‘’„‟«»')


def normalized(key):
    return unicodedata.normalize('NFKC', key).strip().casefold()


def key_flags(value, schema, path=''):
    if not isinstance(schema, dict):
        return []
    flags = []
    props = dict(schema.get('properties', {}))
    for keyword in ('allOf', 'anyOf', 'oneOf'):
        for branch in schema.get(keyword, []):
            if isinstance(branch, dict):
                props.update(branch.get('properties', {}))
                flags.extend(key_flags(value, branch, path))
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in props:
                candidate = next((name for name in props if normalized(name) == normalized(key)), None)
                if candidate is None:
                    candidate = next((name for name in props if name and key.startswith(name)
                                      and len(key) > len(name) and not key[len(name)].isalnum()), None)
                if candidate is not None or any(char in QUOTES for char in key):
                    flags.append((child_path, candidate))
            child_schema = props.get(key, schema.get('additionalProperties', {}))
            flags.extend(key_flags(child, child_schema, child_path))
    elif isinstance(value, list):
        items = schema.get('items', {})
        prefix = schema.get('prefixItems', items if isinstance(items, list) else [])
        for index, child in enumerate(value):
            sub = prefix[index] if index < len(prefix) else (items if isinstance(items, dict) else schema.get('additionalItems', {}))
            flags.extend(key_flags(child, sub, path + '/' + str(index)))
    return sorted(set(flags), key=lambda item: item[0])


def failure_class(*, engine_refusal, truncated, invalid, wrong_tool, lookalike_key, correct):
    for name, present in [('engine_refusal', engine_refusal), ('cd_truncated', truncated),
                          ('invalid', invalid), ('wrong_tool', wrong_tool),
                          ('lookalike_key', lookalike_key), ('valid_wrong_value', not correct)]:
        if present:
            return name
    return 'correct'
