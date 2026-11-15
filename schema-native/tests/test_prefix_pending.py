"""Hermetic helper-failure and append-only offline resolution regression tests."""
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import pytest
from sn import e0b,paths,provenance,native_prefix as native,prefix_pending as pending,e0b_resources as life
from sn.e0b_preflight import smoke_gate


def response(text):
    return dict(choices=[dict(message=dict(content=text),finish_reason='length')],usage=dict(completion_tokens=512))


@pytest.fixture(scope='module')
def plan(): return e0b.prepare(e0b.config())


@pytest.mark.parametrize('failure',[FileNotFoundError('helper missing'),ValueError('build hash mismatch'),
                                   subprocess.TimeoutExpired('helper',60),ValueError('malformed JSON')])
def test_benchmark_unavailable_prefix_is_pending_not_engine_refusal(plan,failure):
    def checker(*a,**k):raise failure
    row=e0b.score_response(plan['units'][0],'C1',response('{"tool":'),200,[],prefix_checker=checker)
    assert row['prefix_check']=='pending' and row['failure_class'] is None
    assert not row['engine_error'] and not row['diagnostic_flags']['engine_refusal']
    assert row['constraint_violation'] is None and row['request_error'] is None
    assert row['raw_content']=='{"tool":' and row['usage']['completion_tokens']==512
    assert row['prefix_request']['grammar'].startswith('%llguidance')


@pytest.mark.parametrize('value',[None,{}, {'legal_prefix':'false'}, {'legal_prefix':0}])
def test_injected_malformed_verdict_is_unavailable(value):
    with pytest.raises(native.PrefixCheckUnavailable):
        native.verify_prefix({},'{',grammar='g',prefix_checker=lambda *a,**k:value)


def test_smoke_unavailable_prefix_is_resumable(plan):
    unit=plan['units'][0]
    def checker(*a,**k):raise subprocess.TimeoutExpired('helper',60)
    with pytest.raises(native.PrefixCheckUnavailable) as exc:
        smoke_gate(200,response('{'),[],unit['C1_schema'],unit['tools'],grammar='g',prefix_checker=checker)
    assert isinstance(exc.value,life.ResourceStop)


def seed_pending(directory,plan,stream):
    unit=plan['units'][0];text='{"tool":'
    def unavailable(*a,**kw):raise FileNotFoundError('synthetic missing helper')
    row=e0b.score_response(unit,'C1',response(text),200,[],prefix_checker=unavailable)
    if stream=='results.jsonl':
        row.update(request_key='C1|'+unit['key'],unit_key=unit['key'],arm='C1')
        key_field='request_key'
    else:
        row=dict(key='smoke|C1|'+unit['key'],status=200,response=response(text),engine_log_errors=[],
                 prefix_check='pending',prefix_request=row['prefix_request'],prefix_check_error=row['prefix_check_error'],
                 smoke_gate=dict(passed=False,outcome='prefix_check_pending'))
        key_field='key'
    (directory/stream).write_text(json.dumps(row)+'\n')
    return row,key_field


@pytest.mark.parametrize('stream',['results.jsonl','readiness-results.jsonl'])
def test_offline_legal_resolution_preserves_bytes_and_does_not_send_request(tmp_path,plan,stream,monkeypatch):
    row,key_field=seed_pending(tmp_path,plan,stream);original=(tmp_path/stream).read_bytes()
    calls=[]
    def checker(schema,text,*,grammar):
        assert text=='{"tool":' and grammar==row['prefix_request']['grammar']
        assert schema==row['prefix_request']['schema'];calls.append(text)
        return dict(legal_prefix=True,accepting=False)
    monkeypatch.setattr('sn.run.http_json',lambda *a,**kw:pytest.fail('Offline verification contacted server'))
    assert pending.resolve_pending(tmp_path,prefix_checker=checker)==1
    assert pending.resolve_pending(tmp_path,prefix_checker=checker)==0
    assert len(calls)==1 and (tmp_path/stream).read_bytes()==original
    resolved=pending.effective_rows(tmp_path,stream,key_field)[0]
    assert resolved['prefix_check']=='verified'
    if stream=='results.jsonl':assert resolved['failure_class']=='cd_truncated' and not resolved['engine_error']
    else:assert resolved['smoke_gate']['passed']


@pytest.mark.parametrize('stream',['results.jsonl','readiness-results.jsonl'])
def test_offline_confirmed_illegal_prefix_is_final(tmp_path,plan,stream,monkeypatch):
    _,key_field=seed_pending(tmp_path,plan,stream)
    monkeypatch.setattr(life,'unload',lambda *a:None)
    life.stop(tmp_path,native.PrefixCheckUnavailable('helper unavailable'),'resource_guard')
    with pytest.raises(RuntimeError,match='Confirmed illegal prefix') as exc:
        pending.resolve_pending(tmp_path,prefix_checker=lambda *a,**kw:dict(legal_prefix=False))
    life.stop(tmp_path,exc.value,'server_resource')
    assert not json.loads((tmp_path/'STOPPED.json').read_text())['resumable']
    with pytest.raises(ValueError,match='final fault'):life.resume(tmp_path)
    assert pending.effective_rows(tmp_path,stream,key_field)[0]['prefix_check']=='illegal'


def test_unavailable_offline_check_leaves_pending_without_resolution(tmp_path,plan):
    row,_=seed_pending(tmp_path,plan,'results.jsonl');original=(tmp_path/'results.jsonl').read_bytes()
    def checker(*a,**kw):raise subprocess.TimeoutExpired('helper',60)
    with pytest.raises(native.PrefixCheckUnavailable):pending.resolve_pending(tmp_path,prefix_checker=checker)
    assert not (tmp_path/'prefix-resolutions.jsonl').exists()
    assert (tmp_path/'results.jsonl').read_bytes()==original


@pytest.mark.parametrize('stdout',['not JSON','[]','{}',
    '{"compile_ok":true,"legal_prefix":["false"],"accepts":[false]}',
    '{"compile_ok":true,"legal_prefix":[true],"accepts":[]}',
    '{"compile_ok":true,"legal_prefix":[true],"accepts":[false],"extra":NaN}',
    '{"compile_ok":true,"legal_prefix":[true],"legal_prefix":[false],"accepts":[false]}'])
def test_malformed_native_helper_output_is_unavailable(monkeypatch,stdout):
    baseline=json.loads(Path(paths.ROOT,'analysis/e0-compatibility/native-clean.json').read_text())
    monkeypatch.setattr(native,'verified_build',lambda *a:dict(library_sha256=baseline['library_sha256']))
    monkeypatch.setattr(native.subprocess,'run',lambda *a,**kw:SimpleNamespace(stdout=stdout))
    with pytest.raises(native.PrefixCheckUnavailable):
        native.check_prefix({},'{',grammar='%llguidance {}\nstart: %json {}')


def test_native_hash_failure_does_not_invoke_helper(monkeypatch):
    def mismatch(*a):raise ValueError('build hash mismatch')
    monkeypatch.setattr(native,'verified_build',mismatch)
    monkeypatch.setattr(native.subprocess,'run',lambda *a,**kw:pytest.fail('Unverified helper invoked'))
    with pytest.raises(native.PrefixCheckUnavailable,match='hash mismatch'):
        native.check_prefix({},'{',grammar='%llguidance {}\nstart: %json {}')


def test_self_test_uses_one_helper_call_with_three_fixed_probes(monkeypatch):
    baseline=json.loads(Path(paths.ROOT,'analysis/e0-compatibility/native-clean.json').read_text())
    monkeypatch.setattr(native,'verified_build',lambda *a:dict(library_sha256=baseline['library_sha256']))
    calls=[]
    def helper(*a,**kw):
        calls.append(json.loads(kw['input']))
        return SimpleNamespace(stdout=json.dumps(dict(compile_ok=True,legal_prefix=[True,True,False],accepts=[True,False,False])))
    monkeypatch.setattr(native.subprocess,'run',helper)
    assert native.self_test()['passed'] and len(calls)==1 and len(calls[0]['samples'])==3


def test_failed_self_test_prevents_model_load(tmp_path,monkeypatch,plan):
    import sys
    from sn import server
    model=plan['model'];rc=plan['config'];fake=tmp_path/'models'/model['gguf_file'];fake.parent.mkdir();fake.write_text('synthetic')
    profile=tmp_path/'profile.json';profile.write_text(json.dumps(model))
    monkeypatch.setattr(paths,'ROOT',str(tmp_path));monkeypatch.setattr(paths,'RUNS',str(tmp_path/'runs'))
    monkeypatch.setattr(e0b,'config',lambda *a:rc);monkeypatch.setattr(e0b,'prepare',lambda *a:plan)
    monkeypatch.setattr(e0b,'campaign_budget',lambda *a:None)
    monkeypatch.setattr(e0b,'identity_for',lambda *a:{'synthetic':True})
    monkeypatch.setattr(server.socket,'create_connection',lambda *a,**kw:(_ for _ in ()).throw(OSError()))
    def fail():raise native.PrefixCheckUnavailable('self-test failed')
    monkeypatch.setattr(native,'self_test',fail)
    monkeypatch.setattr(server.subprocess,'Popen',lambda *a,**kw:pytest.fail('Model loaded despite helper failure'))
    monkeypatch.setattr(life,'unload',lambda *a:None)
    monkeypatch.setattr(sys,'argv',['sn.server',str(fake),'8080','--config',str(profile),'--campaign-config','configs/runs/e0b.json'])
    with pytest.raises(native.PrefixCheckUnavailable):server.main()
    stop=json.loads((tmp_path/'runs'/rc['run_id']/'STOPPED.json').read_text())
    assert stop['resumable']


def test_benchmark_pending_response_persists_then_resume_skips_it(tmp_path,monkeypatch,plan):
    from sn import e0b_preflight,run
    rc=plan['config'];rid=rc['run_id'];directory=tmp_path/rid
    monkeypatch.setattr(paths,'RUNS',str(tmp_path));monkeypatch.setattr(e0b,'prepare',lambda *a:plan)
    monkeypatch.setattr(e0b_preflight,'validate_native',lambda *a:None)
    monkeypatch.setattr(life,'require_session',lambda *a:None);monkeypatch.setattr(life,'unload',lambda *a:None)
    monkeypatch.setattr(life,'guard',lambda *a:{})
    monkeypatch.setattr(e0b.time,'sleep',lambda *a:None)
    proof=tmp_path/'native.json';proof.write_text('{}');log=tmp_path/'server.log';log.write_text('')
    receipt=tmp_path/'receipt.json';receipt.write_text(json.dumps(dict(online_ok=True,identity=e0b.identity_for(plan),run_id=rid,
        server='http://fake',server_props={},server_log=str(log),native_evidence_path=str(proof),native_evidence_sha256=provenance.file_sha(proof))))
    units={u['key']:u for u in plan['units']};sent=[]
    def http(url,payload=None,**kw):
        if url.endswith('/props'):return 200,{}
        index=len(sent);sent.append(payload)
        if index<30:
            sample=plan['determinism'][index];text=units[sample['unit_key']][sample['arm']]['raw_content']
            return 200,dict(choices=[dict(message=dict(content=text),finish_reason='stop')])
        return 200,response('{"tool":')
    monkeypatch.setattr(run,'http_json',http)
    original_score=e0b.score_response
    def score(unit,arm,res,*a):
        if arm=='C1':
            def unavailable(*a,**kw):raise FileNotFoundError('missing helper')
            return original_score(unit,arm,res,*a,prefix_checker=unavailable)
        return dict(raw_content=res['choices'][0]['message']['content'],engine_error=False,usage={})
    monkeypatch.setattr(e0b,'score_response',score)
    args=SimpleNamespace(preflight=str(receipt),server='http://fake',run_id=rid)
    with pytest.raises(native.PrefixCheckUnavailable):e0b.execute(rc,args)
    assert len(sent)==31
    rows=paths.jsonl(directory/'results.jsonl');saved=rows[-1]
    assert saved['prefix_check']=='pending' and not saved['engine_error'] and saved['failure_class'] is None
    assert json.loads((directory/'STOPPED.json').read_text())['resumable']
    original_bytes=(directory/'results.jsonl').read_bytes()
    assert pending.resolve_pending(directory,prefix_checker=lambda *a,**kw:dict(legal_prefix=True))==1
    # Stop before any subsequent generation: every previously completed key, including pending-now-verified, must be skipped.
    def next_request(url,payload=None,**kw):
        if url.endswith('/props'):return 200,{}
        assert payload==e0b.payload_for(plan,plan['units'][1],'C1')
        raise native.PrefixCheckUnavailable('Synthetic stop at next request')
    monkeypatch.setattr(run,'http_json',next_request)
    with pytest.raises(native.PrefixCheckUnavailable):e0b.execute(rc,args)
    assert (directory/'results.jsonl').read_bytes()==original_bytes
    charges=paths.jsonl(directory/'request-budget.jsonl')
    assert sum(r['category']=='benchmark' for r in charges)==32
    assert sum(r['key']=='C1|'+plan['units'][0]['key'] for r in charges)==1
