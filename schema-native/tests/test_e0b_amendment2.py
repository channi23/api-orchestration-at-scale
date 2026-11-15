import copy
import json
import subprocess
from pathlib import Path
import pytest
from sn import envelope,paths,resources
from sn.e0b import config,prepare,campaign_budget,score_response
from sn.e0b_preflight import smoke_gate


def response(text,finish='stop'):
    return {'choices':[{'message':{'content':text},'finish_reason':finish}]}


def fixture():
    tools={'x':{'type':'object','properties':{'n':{'const':7}},'required':['n'],'additionalProperties':False}}
    return tools,envelope.envelope(list(tools.items()))


def test_legal_prefix_truncation_passes_without_parsing_incomplete_JSON(monkeypatch):
    tools,schema=fixture();seen=[]
    monkeypatch.setattr('sn.e0b_preflight.strict_loads',lambda *a:pytest.fail('Incomplete JSON parsed'))
    def checker(actual,text,*,grammar):
        assert actual==schema and text=='{"tool":"x","arguments":' and grammar=='exact-request-grammar'
        seen.append(text);return {'legal_prefix':True,'accepting':False}
    result=smoke_gate(200,response('{"tool":"x","arguments":','length'),[],schema,tools,
                      grammar='exact-request-grammar',prefix_checker=checker)
    assert result['passed'] and result['outcome']=='cd_truncated' and len(seen)==1


def test_illegal_prefix_truncation_stops():
    tools,schema=fixture()
    with pytest.raises(ValueError,match='not a legal grammar prefix'):
        smoke_gate(200,response('illegal','length'),[],schema,tools,grammar='g',
                   prefix_checker=lambda *a,**k:{'legal_prefix':False})


@pytest.mark.parametrize('status,errors',[(200,['llg error: matcher failed']),(500,[])])
def test_engine_or_http_error_stops_before_prefix_check(status,errors):
    tools,schema=fixture()
    with pytest.raises(ValueError,match='engine/request fault'):
        smoke_gate(status,response('{','length'),errors,schema,tools,grammar='g',
                   prefix_checker=lambda *a,**k:pytest.fail('Fault accepted through prefix path'))


def test_finished_constraint_copy_violation_stops():
    tools,schema=fixture()
    with pytest.raises(ValueError,match='constraint copy'):
        smoke_gate(200,response('{"tool":"x","arguments":{"n":8}}'),[],schema,tools,grammar='g')


def test_finished_named_raw_schema_violation_stops_even_with_weak_constraint():
    tools,_=fixture()
    with pytest.raises(ValueError,match='named-tool raw schema'):
        smoke_gate(200,response('{"tool":"x","arguments":{"n":8}}'),[],{},tools,grammar='g')


@pytest.mark.parametrize('text',['```json\n{}\n```','{"tool":"x","arguments":{"n":7,"n":7}}'])
def test_finished_non_strict_JSON_stops(text):
    tools,schema=fixture()
    with pytest.raises(ValueError,match='strict JSON'):
        smoke_gate(200,response(text),[],schema,tools,grammar='g')


def test_finished_valid_response_passes():
    tools,schema=fixture()
    assert smoke_gate(200,response('{"tool":"x","arguments":{"n":7}}'),[],schema,tools,grammar='g')['outcome']=='finished_valid'


def test_benchmark_truncation_is_scored_not_an_engine_fault():
    unit=prepare(config())['units'][0]
    row=score_response(unit,'C1',response('{"tool":','length'),200,[])
    assert row['failure_class']=='cd_truncated' and not row['engine_error']
    assert not row['eval']['e2e_success']


def test_cumulative_budget_imports_eleven_spent_and_leaves_49(tmp_path):
    rc=config();budget=campaign_budget(tmp_path,rc)
    original=Path(paths.ROOT,rc['budget_carryover']['ledger']).read_bytes()
    assert len(budget.path.read_text().splitlines())==11
    # New attempts may repeat old probe names, but never erase the old charges.
    for index in range(49):budget.reserve('readiness','new:'+str(index))
    with pytest.raises(ValueError,match='cap reached'):budget.reserve('readiness','over-budget')
    assert len(campaign_budget(tmp_path,rc).path.read_text().splitlines())==60
    assert Path(paths.ROOT,rc['budget_carryover']['ledger']).read_bytes()==original


def test_existing_ledger_cannot_omit_prior_charges(tmp_path):
    (tmp_path/'request-budget.jsonl').write_text('')
    with pytest.raises(ValueError,match='missing or has changed'):
        campaign_budget(tmp_path,config())


def test_amendment2_history_and_stopped_campaign_are_preserved():
    base='f2e6b580584642237de656d227d6d2cdfc067dc5'
    original=subprocess.check_output(['git','show',base+':schema-native/E0B_PLAN.md'],cwd=paths.REPO,text=True)
    assert Path(paths.ROOT,'E0B_PLAN.md').read_text().startswith(original)
    for name in ('e0b','e0b_smoke'):
        old=subprocess.check_output(['git','show',base+':schema-native/configs/runs/'+name+'.json'],cwd=paths.REPO,text=True)
        rc=config('configs/runs/'+name+'.json');assert rc['amendment1_locked_text']==old
        assert json.loads(rc['amendment2_locked_text'])['amendment']==2
        assert rc['amendment']==3 and rc['run_id']=='e0b-amendment3-v1'
    subprocess.run(['git','diff','--exit-code',base,'--','schema-native/analysis/e0b-amendment1-v1'],cwd=paths.REPO,check=True,capture_output=True)


def test_swap_growth_threshold_and_boot_identity(tmp_path):
    rc={'run_id':'test','system_swapout_baseline_file':str(tmp_path/'swap.json'),
        'max_system_swapout_growth_bytes':1073741824}
    baseline={'run_id':'test','boot':'boot-1','system_swapout_bytes':1234}
    Path(rc['system_swapout_baseline_file']).write_text(json.dumps(baseline))
    assert resources.check_swap_growth(rc,1234+1073741824,boot='boot-1')==1073741824
    with pytest.raises(RuntimeError,match='more than 1 GiB'):
        resources.check_swap_growth(rc,1234+1073741825,boot='boot-1')
    with pytest.raises(RuntimeError,match='identity changed'):
        resources.check_swap_growth(rc,1234,boot='boot-2')


def test_missing_swap_baseline_stops_before_generation(tmp_path):
    rc={'run_id':'test','system_swapout_baseline_file':str(tmp_path/'absent.json'),
        'max_system_swapout_growth_bytes':1073741824}
    with pytest.raises(RuntimeError,match='before loading Qwen'):
        resources.check_swap_growth(rc,0)


def test_benchmark_illegal_prefix_is_an_engine_fault(monkeypatch):
    monkeypatch.setattr('sn.e0b.check_prefix',lambda *a,**k:{'legal_prefix':False})
    unit=prepare(config())['units'][0]
    row=score_response(unit,'C1',response('illegal','length'),200,[])
    assert row['engine_error'] and row['constraint_violation']


def test_benchmark_finished_constraint_violation_is_an_engine_fault():
    unit=copy.deepcopy(prepare(config())['units'][0]);unit['C1_schema']=False
    text=json.dumps({'tool':unit['task']['tool_name'],'arguments':unit['task']['gold_args']})
    row=score_response(unit,'C1',response(text),200,[])
    assert row['engine_error'] and row['constraint_violation']


def test_e0b_fair_thermal_state_is_a_stop(monkeypatch):
    monkeypatch.setattr(resources.subprocess,'check_output',lambda *a,**k:'1')
    monkeypatch.setattr(resources,'thermal_state',lambda:1)
    monkeypatch.setattr(resources,'swap_snapshot',lambda:(16384,0))
    with pytest.raises(RuntimeError,match='Thermal state 1'):
        resources.check({'protocol':'e0b-locked-v1-amendment2','require_normal_memory_pressure':True,
                         'require_acceptable_thermal_state':True},{})
