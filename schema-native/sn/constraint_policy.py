"""Versioned preparation for the frozen E0 evaluator (format assertions disabled).

Only constraint copies change. Prompts, raw schemas, gold values and the evaluator stay untouched.
This is not a general dialect converter or a claim of complete JSON Schema engine support.
"""
import copy
from . import paths  # makes the frozen schema walker available
import schema_utils as su

ORIGINAL = 'original-v0'
COMPATIBLE = 'annotation-dependencies-v1'


def prepare(schema, policy=ORIGINAL):
    if policy == ORIGINAL:
        return copy.deepcopy(schema)
    if policy != COMPATIBLE:
        raise ValueError('Unknown constraint preparation policy: ' + policy)

    def walk(node):
        if not isinstance(node, dict):
            return copy.deepcopy(node)
        out = {}
        for key, value in node.items():
            if key in ('format', 'dependencies'):
                continue
            if key in su.SCHEMA_MAP_KEYS and isinstance(value, dict):
                out[key] = {name: walk(child) for name, child in value.items()}
            elif key in su.SCHEMA_LIST_KEYS and isinstance(value, list):
                out[key] = [walk(child) for child in value]
            elif key in su.SCHEMA_SINGLE_KEYS:
                out[key] = [walk(child) for child in value] if isinstance(value, list) else walk(value)
            else:
                out[key] = copy.deepcopy(value)
        guards = []
        for trigger, dependency in node.get('dependencies', {}).items():
            if isinstance(dependency, list):
                if not dependency:
                    continue
                consequent = {'required': copy.deepcopy(dependency)}
            elif isinstance(dependency, (dict, bool)):
                consequent = walk(dependency)
            else:
                raise ValueError('Invalid legacy dependency')
            # properties:{p:false} means p is absent. A dependency is absent(p) OR consequent.
            # Both object-only keywords are vacuous for non-objects, as dependencies itself is.
            guards.append({'anyOf': [{'properties': {trigger: False}}, consequent]})
        if guards:
            out['allOf'] = out.get('allOf', []) + guards
        return out

    return walk(schema)
