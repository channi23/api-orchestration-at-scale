"""Named serialization policies, separate from JSON value constraints."""
import copy

FLEXIBLE = 'json-flexible-v1'
FIXED = 'json-fixed-readable-v1'


def apply(schema, option=FLEXIBLE):
    result = copy.deepcopy(schema)
    if option == FIXED:
        result['x-guidance'] = {**result.get('x-guidance', {}), 'whitespace_flexible': False,
                                'item_separator': ', ', 'key_separator': ': '}
    elif option != FLEXIBLE:
        raise ValueError('Unknown constraint option: ' + option)
    return result
