import copy
import inspect
import json
from pathlib import Path

import jsonschema
import pytest
from sn import envelope, paths
from sn.constraint_options import apply, FIXED
from sn.e0b import Budget, config, prepare, payload_for, ordered_hash
from sn.oracle_order import reorder_envelope, sorted_serialization
from sn.router import route, strict_loads
from sn.lookalike import key_flags, failure_class
from sn.e0b_readiness import replay


@pytest.fixture(scope='module')
def locked_plan():
    return prepare(config())


@pytest.mark.parametrize('text', ['```json\n{}\n```', '{"x":1,"x":2}',
                                 '{"x":{"a":1,"a":2}}', '{"x":NaN}',
                                 '{"x":Infinity}', '{"x":-Infinity}', '{"x":1e999}'])
def test_strict_parser_rejects_wrappers_duplicates_and_nonfinite(text):
    with pytest.raises((ValueError, TypeError)):
        strict_loads(text)


def test_router_cannot_read_gold_or_eval_and_never_selects_gold_tool():
    assert list(inspect.signature(route).parameters) == ['raw_content', 'tools', 'truncated']
    class PublicOnly(dict):
        def __getitem__(self, key):
            if key != 'raw_content':
                raise AssertionError('Attempt to access private evaluation metadata')
            return super().__getitem__(key)
    row = PublicOnly(raw_content='{"tool":"other","arguments":{}}', gold_tool='target',
                     gold_args={'secret': 'never read'}, eval={'e2e_success': False})
    tools = {'target': {'type': 'object'}, 'other': {'type': 'object'}}
    assert not route(row['raw_content'], tools)['retry']
    row.update(gold_tool='different', gold_args=None, eval=object())
    assert not route(row['raw_content'], tools)['retry']
    assert route(row['raw_content'], {'target': {'type': 'object'}})['retry']


def test_oracle_only_named_tool_and_all_branches_are_retained():
    argument = {'type': 'object', 'properties': {'a': {}, 'b': {}}, 'required': ['a'],
                'allOf': [{'properties': {'a': {}, 'b': {}}}],
                'anyOf': [{'properties': {'a': {}, 'b': {}}}, {'type': 'object'}],
                'oneOf': [{'properties': {'a': {}, 'b': {}}}],
                'if': {'properties': {'a': {}, 'b': {}}},
                'then': {'properties': {'a': {}, 'b': {}}},
                'not': {'required': ['impossible']}}
    tools = {'selected': argument, 'untouched': argument}
    base = envelope.envelope(list(tools.items()))
    before = copy.deepcopy(base)
    result, flags = reorder_envelope(base, '{"tool":"selected","arguments":{"b":2,"a":1}}', tools)
    assert not flags['oracle_not_applied']
    assert sorted_serialization(result) == sorted_serialization(base)
    assert base == before and result['anyOf'][1] == base['anyOf'][1]
    args = result['anyOf'][0]['properties']['arguments']
    assert list(args['properties']) == ['b', 'a']
    for keyword in ('allOf', 'anyOf', 'oneOf'):
        assert list(args[keyword][0]['properties']) == ['b', 'a']
    assert args['required'] == ['a']


def test_array_first_element_disagreement_and_tuple_positions():
    item = {'type': 'object', 'properties': {'a': {}, 'b': {}}}
    raw = {'type': 'object', 'properties': {'array': {'type': 'array', 'items': item},
           'tuple': {'type': 'array', 'items': [item, item]}}}
    tools = {'x': raw}; base = envelope.envelope(list(tools.items()))
    content = '{"tool":"x","arguments":{"array":[{"b":1,"a":2},{"a":3,"b":4}],"tuple":[{"b":1,"a":2},{"a":3,"b":4}]}}'
    result, flags = reorder_envelope(base, content, tools)
    props = result['properties']['arguments']['properties']
    assert flags['oracle_incomplete']
    assert list(props['array']['items']['properties']) == ['b', 'a']
    assert list(props['tuple']['items'][0]['properties']) == ['b', 'a']
    assert list(props['tuple']['items'][1]['properties']) == ['a', 'b']
    assert sorted_serialization(base) == sorted_serialization(result)


@pytest.mark.parametrize('text,truncated', [('bad', False), ('```json\n{}\n```', False),
                                         ('{"tool":"x","arguments":{}}', True),
                                         ('{"tool":"absent","arguments":{}}', False)])
def test_oracle_invalid_wrapped_or_truncated_fallback(text, truncated):
    tools = {'x': {'type': 'object'}}; base = envelope.envelope(list(tools.items()))
    result, flags = reorder_envelope(base, text, tools, truncated=truncated)
    assert flags['oracle_not_applied']
    assert json.dumps(result) == json.dumps(base)


def test_frozen_units_gold_and_F0_validator_verdicts_unchanged(locked_plan):
    assert len(locked_plan['units']) == 300
    for unit in locked_plan['units']:
        a, b = unit['C1_schema'], unit['C2_schema']
        assert sorted_serialization(a) == sorted_serialization(b)
        validators = [jsonschema.Draft7Validator(s) for s in (a, b)]
        gold = {'tool': unit['task']['tool_name'], 'arguments': unit['task']['gold_args']}
        assert all(v.is_valid(gold) for v in validators)
        try:
            free = strict_loads(unit['F0']['raw_content'])
        except ValueError:
            continue
        assert validators[0].is_valid(free) == validators[1].is_valid(free)
        if isinstance(free, dict) and free.get('tool') in unit['tools'] and 'arguments' in free:
            raw = unit['tools'][free['tool']]
            branches = b.get('anyOf', [b])
            sub = next(x['properties']['arguments'] for x in branches if x['properties']['tool']['const'] == free['tool'])
            V = jsonschema.validators.validator_for(raw)
            assert V(raw).is_valid(free['arguments']) == jsonschema.Draft7Validator(sub).is_valid(free['arguments'])


def test_plan_determinism_selection_reused_arms_and_replay(locked_plan):
    samples = locked_plan['determinism']
    assert len(samples) == 30 and len({s['source_key'] for s in samples}) == 30
    assert [s['arm'] for s in samples].count('F0') == 15
    assert [s['arm'] for s in samples].count('C0') == 15
    assert samples == prepare(config())['determinism']
    assert locked_plan['new_benchmark_requests'] == 962
    assert replay(locked_plan['units'])['select']['routed'] == 18
    assert replay(locked_plan['units'])['arggen']['routed'] == 14
    assert config()['arm_defs']['F0']['status'] == config()['arm_defs']['C0']['status'] == 'reused'
    assert 'response_format' in payload_for(locked_plan, locked_plan['units'][0], 'C3')
    assert 'grammar' in payload_for(locked_plan, locked_plan['units'][0], 'C1')


def test_budget_reserves_before_send_and_failed_attempts_cannot_be_retried(tmp_path):
    ledger = tmp_path / 'budget.jsonl'
    ledger.write_text(''.join(json.dumps({'category': 'benchmark', 'key': str(i)}) + '\n' for i in range(999)))
    budget = Budget(ledger)
    budget.reserve('benchmark', 'last')
    with pytest.raises(ValueError, match='cap reached'): budget.reserve('benchmark', 'overflow')
    with pytest.raises(ValueError, match='already reserved'): budget.reserve('benchmark', 'last')
    for i in range(60): budget.reserve('readiness', 'preflight:' + str(i))
    with pytest.raises(ValueError, match='cap reached'): budget.reserve('readiness', 'smoke:overflow')
    assert len(ledger.read_text().splitlines()) == 1060


def test_named_fixed_option_and_lookalike_flags_do_not_mutate_values():
    schema = {'type': 'object', 'properties': {'con_date': {'type': 'string'}}}
    prepared = apply(schema, FIXED)
    assert 'x-guidance' not in schema
    assert prepared['x-guidance']['key_separator'] == ': '
    assert prepared['x-guidance']['item_separator'] == ', '
    value = {'con_date ': 'x', 'other”': 'y'}; original = copy.deepcopy(value)
    assert len(key_flags(value, schema)) == 2 and value == original
    assert key_flags({'con_date': 'x'}, schema) == []
    assert failure_class(engine_refusal=True, truncated=True, invalid=True, wrong_tool=True,
                         lookalike_key=True, correct=False) == 'engine_refusal'
    assert failure_class(engine_refusal=False, truncated=False, invalid=False, wrong_tool=True,
                         lookalike_key=True, correct=False) == 'wrong_tool'


def test_determinism_failure_stops_after_one_request_without_rerunning_baselines(tmp_path, monkeypatch, locked_plan):
    from types import SimpleNamespace
    from sn import e0b, e0b_preflight, run
    from sn.provenance import file_sha
    monkeypatch.setattr(e0b, 'prepare', lambda rc: locked_plan)
    monkeypatch.setattr(e0b_preflight, 'validate_native', lambda *a: None)
    monkeypatch.setattr(paths, 'RUNS', str(tmp_path))
    monkeypatch.setattr(e0b.resources, 'check', lambda *a: {})
    native = tmp_path/'native.json'; native.write_text('{}')
    log = tmp_path/'server.log'; log.write_text('')
    receipt = tmp_path/'receipt.json'
    receipt.write_text(json.dumps({'online_ok':True,'identity':e0b.identity_for(locked_plan),
        'run_id':'e0b-test','server':'http://fake','server_props':{},'server_log':str(log),
        'native_evidence_path':str(native),'native_evidence_sha256':file_sha(native)}))
    first = locked_plan['determinism'][0]
    unit = next(u for u in locked_plan['units'] if u['key']==first['unit_key'])
    calls = []
    def fake(url, payload=None, **kw):
        if url.endswith('/props'): return 200, {}
        calls.append(payload)
        return 200, {'choices':[{'message':{'content':unit['F0']['raw_content']+' '},'finish_reason':'stop'}]}
    monkeypatch.setattr(run,'http_json',fake)
    args=SimpleNamespace(preflight=str(receipt),server='http://fake',run_id='e0b-test')
    with pytest.raises(RuntimeError,match='Determinism failed'):
        e0b.execute(locked_plan['config'],args)
    assert len(calls)==1
    assert json.loads((tmp_path/'e0b-test/STOPPED.json').read_text())['reason']=='determinism_failed'
    with pytest.raises(ValueError,match='Campaign stopped'):
        e0b.execute(locked_plan['config'],args)
    assert len(calls)==1


def test_failed_native_coverage_blocks_before_network_or_model_access(monkeypatch, tmp_path, locked_plan):
    from sn import e0b_preflight
    native={'config_sha256':ordered_hash(locked_plan['config']),
            'plan_sha256':ordered_hash(locked_plan),
            'C3_unsupported':{'catalog':'enforcement failure'}}
    f=tmp_path/'native.json';f.write_text(json.dumps(native))
    monkeypatch.setattr(e0b_preflight,'prepare',lambda rc:locked_plan)
    monkeypatch.setattr(e0b_preflight,'http_json',lambda *a,**k:pytest.fail('Network contacted despite failed native gate'))
    monkeypatch.setattr(e0b_preflight.preflight,'runtime',lambda *a,**k:pytest.fail('Model file accessed despite failed native gate'))
    with pytest.raises(ValueError,match='C3 unsupported'):
        e0b_preflight.online(locked_plan['config'],run_id='e0b-test',server='http://fake',
                            output=tmp_path/'receipt',native_path=f)


def test_two_primary_tests_and_secondary_tests_use_separate_holm_families(monkeypatch):
    from sn import e0b_report
    values=iter([.04,.01,.02,.03,.04])
    monkeypatch.setattr(e0b_report.statistics,'paired',lambda *a,**k:{'mcnemar_exact_p':next(values),
                        'diff_pp':8,'ci95_diff_pp':[1,12]})
    result=e0b_report.comparisons([],config())
    assert [r['p_holm'] for r in result['comparisons'][:2]]==[.04,.02]
    assert [r['p_holm'] for r in result['comparisons'][2:]]==[.06,.06,.06]
    assert result['order_effect_rule_met']


def test_retry_costs_sum_both_attempts_and_lexical_truncation_location():
    from sn.e0b import aggregate_retry, truncation_location
    free={'wall_latency_ms':3,'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120}}
    retry={'wall_latency_ms':7,'usage':{'prompt_tokens':50,'completion_tokens':10,'total_tokens':60}}
    result=aggregate_retry(free,retry)
    assert result['wall_latency_ms']==10 and result['retry_wall_latency_ms']==7
    assert result['usage']=={'prompt_tokens':150,'completion_tokens':30,'total_tokens':180}
    assert free['usage']['total_tokens']==120 and retry['usage']['total_tokens']==60
    assert truncation_location('{"a":"look-alike ”     ')== 'in_string'
    assert truncation_location('{"a":"escaped \\" quote",   ')== 'between_tokens'


def test_locked_failure_precedence_for_every_class():
    names=['engine_refusal','truncated','invalid','wrong_tool','lookalike_key']
    labels=['engine_refusal','cd_truncated','invalid','wrong_tool','lookalike_key']
    for index,label in enumerate(labels):
        flags={name:i>=index for i,name in enumerate(names)}
        assert failure_class(**flags,correct=False)==label
    flags={name:False for name in names}
    assert failure_class(**flags,correct=False)=='valid_wrong_value'
    assert failure_class(**flags,correct=True)=='correct'


def test_2020_tuple_prefix_items_reordered_per_position():
    raw={'$schema':'https://json-schema.org/draft/2020-12/schema','type':'array',
         'prefixItems':[{'type':'object','properties':{'a':{},'b':{}}},
                        {'type':'object','properties':{'a':{},'b':{}}}]}
    tools={'x':raw};base=envelope.envelope(list(tools.items()))
    reordered,flags=reorder_envelope(base,'{"tool":"x","arguments":[{"b":1,"a":2},{"a":3,"b":4}]}',tools)
    assert not flags['oracle_not_applied']
    items=reordered['properties']['arguments']['prefixItems']
    assert list(items[0]['properties'])==['b','a'] and list(items[1]['properties'])==['a','b']
    assert sorted_serialization(base)==sorted_serialization(reordered)


def test_generic_preflight_cannot_bypass_shared_readiness_budget(monkeypatch):
    import sys
    from sn import preflight,run
    monkeypatch.setattr(sys,'argv',['preflight','--config','configs/runs/e0b.json'])
    monkeypatch.setattr(run,'http_json',lambda *a,**k:pytest.fail('Unbudgeted E0b request'))
    with pytest.raises(ValueError,match='budgeted sn.e0b_preflight'):
        preflight.main()


def test_reused_flags_preserve_original_evaluator_and_raw_bytes(locked_plan):
    from sn.e0b import reused_diagnostics
    unit=locked_plan['units'][0];row=unit['C0'];before=json.dumps(row)
    flags=reused_diagnostics(unit,'C0',row)
    assert 'lookalike_key' in flags['diagnostic_flags']
    assert json.dumps(row)==before
