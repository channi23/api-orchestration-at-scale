"""Proof focused on the two E0 compatibility mismatches, not general schema compilation."""
import copy
import itertools
import json
import jsonschema
import pytest
from sn import constraint_policy as cp, envelope, paths
import schema_utils as su


def test_original_policy_is_an_unchanged_copy_and_unknown_policy_fails():
    schema={'type':'string','format':'uri'}
    assert cp.prepare(schema)==schema and cp.prepare(schema) is not schema
    with pytest.raises(ValueError, match='Unknown'):
        cp.prepare(schema,'silent-lenient-fallback')


def test_annotation_removal_preserves_literal_data_and_property_names():
    schema={'type':'object','properties':{'format':{'type':'string','format':'uri'},
            'x':{'const':{'format':'do not change'},'examples':[{'format':'example'}]}}}
    before=copy.deepcopy(schema);prepared=cp.prepare(schema,cp.COMPATIBLE)
    assert 'format' in prepared['properties']
    assert 'format' not in prepared['properties']['format']
    assert prepared['properties']['x']==schema['properties']['x']
    assert schema==before


def test_dependencies_preserve_presence_semantics_on_exhaustive_subset():
    schema={'properties':{k:{} for k in ('a','b','c')},'dependencies':{'a':['b'],'b':['c']},
            'allOf':[{'maxProperties':3}]}
    prepared=cp.prepare(schema,cp.COMPATIBLE)
    original=jsonschema.Draft7Validator(schema);updated=jsonschema.Draft7Validator(prepared)
    cases=[None,7,'x',[],False]
    for bits in itertools.product((False,True),repeat=3):
        cases.append({k:None for k,present in zip(('a','b','c'),bits) if present})
    for value in cases:
        assert original.is_valid(value)==updated.is_valid(value),value
    assert len(prepared['allOf'])==3


def test_schema_dependencies_apply_to_entire_object_and_preserve_false():
    schema={'dependencies':{'a':{'required':['b'],'properties':{'b':{'const':'yes'}}},'c':False}}
    prepared=cp.prepare(schema,cp.COMPATIBLE)
    original=jsonschema.Draft7Validator(schema);updated=jsonschema.Draft7Validator(prepared)
    for value in ({},{'a':0},{'b':'yes'},{'a':None,'b':'yes'},{'a':0,'b':'no'},{'c':None},None,5):
        assert original.is_valid(value)==updated.is_valid(value),value


def test_frozen_legacy_dependency_all_property_subsets_and_nonobjects():
    tool=paths.pool()['T139'];raw=su.load_schema(tool['schema_id'])
    prepared=cp.prepare(envelope.argument_schema(raw),cp.COMPATIBLE)
    original=jsonschema.validators.validator_for(raw)(raw);updated=jsonschema.Draft7Validator(prepared)
    keys=list(raw['properties']['orders']['items']['properties'])
    for bits in itertools.product((False,True),repeat=len(keys)):
        value={'orders':[{k:'value' for k,present in zip(keys,bits) if present}]}
        assert original.is_valid(value)==updated.is_valid(value),value
    for value in ({},{'orders':[]},{'orders':[None,1,False,'x']},{'orders':None}):
        assert original.is_valid(value)==updated.is_valid(value),value


def test_clean_plan_preserves_all_raw_and_minified_messages():
    from sn import preflight
    import prompts
    from pathlib import Path
    legacy=json.loads(Path(paths.ROOT,'configs/runs/e0_sustainable.json').read_text())
    clean=json.loads(Path(paths.ROOT,'configs/runs/e0_clean.json').read_text())
    old_requests,_=preflight.plan(legacy);new_requests,schemas=preflight.plan(clean)
    assert old_requests==new_requests and len(schemas)==70
    allowed_changes={'run_prefix','purpose','constraint_policy','requires_zero_engine_refusals'}
    assert {k:v for k,v in legacy.items() if k not in allowed_changes} == {k:v for k,v in clean.items() if k not in allowed_changes}
    for tid,tool in paths.pool().items():
        schema=cp.prepare(envelope.argument_schema(su.load_schema(tool['schema_id'])),cp.COMPATIBLE)
        assert not (envelope.keywords_used(schema)&{'format','dependencies'}),tid
