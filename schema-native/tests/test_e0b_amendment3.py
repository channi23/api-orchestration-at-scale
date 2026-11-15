"""Entirely model-free lifecycle and fake-transport integration proof."""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
from sn import e0b, e0b_resources as life, resources, paths, provenance


class Clock:
    def __init__(self): self.now=0;self.sleeps=[]
    def __call__(self): return self.now
    def sleep(self,seconds): self.now+=seconds;self.sleeps.append(seconds)


def events(path):
    return [json.loads(x) for x in (path/'resource-events.jsonl').read_text().splitlines()]


def test_settle_requires_three_consecutive_normal_and_no_requests(tmp_path):
    clock=Clock();samples=iter([1,2,1,1,1])
    life.settle(tmp_path,pressure=lambda:next(samples),clock=clock,sleep=clock.sleep)
    assert clock.now==20 and clock.sleeps==[5]*4
    assert events(tmp_path)[-1]['event']=='settled'


def test_settle_timeout_exactly_90_seconds(tmp_path):
    clock=Clock()
    with pytest.raises(life.ResourceStop,match='settle window'):
        life.settle(tmp_path,pressure=lambda:2,clock=clock,sleep=clock.sleep)
    assert clock.now==90 and len(events(tmp_path))==19


def test_pause_requires_three_clean_checks_after_last_warning(tmp_path):
    clock=Clock();sequence=iter([False,True,False,True,True,True]);requests=[]
    def sample(*a):
        if not next(sequence): raise resources.ResourceWarning('pressure')
        return {'clean':True}
    health=life.guard({}, {}, tmp_path,clock=clock,sleep=clock.sleep,sampler=sample)
    requests.append('only after recovery')
    assert health=={'clean':True} and clock.now==150 and clock.sleeps==[30]*5
    assert [x['event'] for x in events(tmp_path)].count('pause')==1
    assert events(tmp_path)[-1]['event']=='continue'
    assert all(x['utc'] for x in events(tmp_path))


def test_pause_timeout_and_unload(tmp_path,monkeypatch):
    clock=Clock();unloaded=[]
    def sample(*a): raise resources.ResourceWarning('thermal')
    monkeypatch.setattr(life,'unload',lambda directory:unloaded.append(directory))
    with pytest.raises(life.ResourceStop) as caught:
        life.guard({}, {}, tmp_path,clock=clock,sleep=clock.sleep,sampler=sample)
    life.stop(tmp_path,caught.value,'resource_guard')
    assert clock.now==900 and unloaded==[tmp_path]
    assert json.loads((tmp_path/'STOPPED.json').read_text())['resumable'] is True
    original=(tmp_path/'STOPPED.json').read_bytes()
    life.resume(tmp_path)
    assert not (tmp_path/'STOPPED.json').exists()
    assert next((tmp_path/'resource-stops').glob('*.json')).read_bytes()==original
    assert events(tmp_path)[-1]['event']=='resume'


@pytest.mark.parametrize('amount,pressure,allowed',[(5*1024**3,1,True),(5*1024**3-1,1,False),(9*1024**3,2,False)])
def test_preload_memory_floor(tmp_path,amount,pressure,allowed):
    inventory=lambda:dict(available_bytes=amount,free=amount,inactive=0,purgeable=0,
                          largest_processes=[dict(name='Synthetic app',resident_bytes=99)])
    if allowed: assert life.admission(tmp_path,inventory=inventory,pressure=lambda:pressure)
    else:
        with pytest.raises(life.ResourceStop): life.admission(tmp_path,inventory=inventory,pressure=lambda:pressure)
    assert events(tmp_path)[0]['available_bytes']==amount


def test_inventory_contains_only_names_and_sizes(monkeypatch):
    raw='Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages free: 100.\nPages inactive: 200.\nPages purgeable: 30.\n'
    ps='\n'.join(str(i*1024)+' /private/path/App '+str(i) for i in range(1,13))
    monkeypatch.setattr(life.subprocess,'check_output',lambda cmd,**kw:raw if cmd==['vm_stat'] else ps)
    result=life.memory_inventory()
    assert result['available_bytes']==330*16384
    assert len(result['largest_processes'])==10
    assert result['largest_processes'][0]=={'name':'App 12','resident_bytes':12*1024**2}
    assert all(set(row)=={'name','resident_bytes'} for row in result['largest_processes'])


def test_swap_hard_limit_is_not_paused_or_resumable(tmp_path,monkeypatch):
    monkeypatch.setattr(life,'unload',lambda *a:None)
    def sample(*a): raise RuntimeError('System swapout grew by more than 1 GiB')
    with pytest.raises(RuntimeError) as exc:
        life.guard({}, {}, tmp_path,sampler=sample,sleep=lambda *a:pytest.fail('Hard stop paused'))
    life.stop(tmp_path,exc.value,'resource_guard')
    with pytest.raises(ValueError,match='final fault'):life.resume(tmp_path)


@pytest.mark.parametrize('reason',['engine fault','constraint violation','illegal-prefix truncation','determinism mismatch'])
def test_final_fault_not_resumable(tmp_path,monkeypatch,reason):
    monkeypatch.setattr(life,'unload',lambda *a:None)
    life.stop(tmp_path,RuntimeError(reason),'benchmark')
    original=(tmp_path/'STOPPED.json').read_bytes()
    with pytest.raises(ValueError,match='final fault'):life.resume(tmp_path)
    assert (tmp_path/'STOPPED.json').read_bytes()==original


def test_swap_hard_limit_checked_even_with_memory_warning(monkeypatch):
    monkeypatch.setattr(resources,'swap_snapshot',lambda:(16384,100))
    monkeypatch.setattr(resources,'pressure_level',lambda:2)
    def hard(*a): raise RuntimeError('hard swap cap')
    monkeypatch.setattr(resources,'check_swap_growth',hard)
    with pytest.raises(RuntimeError,match='hard swap cap'):
        resources.check({'require_normal_memory_pressure':True,'protocol':'e0b-locked-v1-amendment3'},{})


def test_amendment3_history_and_scientific_settings_preserved():
    base='d26feb90ee9de648b3507d8f2ffd5c2168bcaddd'
    old=subprocess.check_output(['git','show',base+':schema-native/E0B_PLAN.md'],cwd=paths.REPO,text=True)
    assert Path(paths.ROOT,'E0B_PLAN.md').read_text().startswith(old)
    allowed={'amendment2_locked_text','amendment','protocol','run_id','system_swapout_baseline_file','resource_policy','amendments'}
    for name in ('e0b','e0b_smoke'):
        raw=subprocess.check_output(['git','show',base+':schema-native/configs/runs/'+name+'.json'],cwd=paths.REPO,text=True)
        rc=e0b.config('configs/runs/'+name+'.json');previous=json.loads(raw)
        assert rc['amendment2_locked_text']==raw
        assert {k:v for k,v in rc.items() if k not in allowed}=={k:v for k,v in previous.items() if k not in allowed}
        assert rc['amendments'][:-1]==previous['amendments']
    subprocess.run(['git','diff','--exit-code',base,'--','experiment','schema-native/analysis/e0-clean-v1',
                    'schema-native/analysis/e0b-amendment1-v1','schema-native/analysis/e0b-amendment2-v1'],
                   cwd=paths.REPO,check=True,capture_output=True)


def test_benchmark_resource_resume_skips_completed_keys_and_keeps_order(tmp_path,monkeypatch):
    from sn import e0b_preflight,run
    plan=e0b.prepare(e0b.config());rc=plan['config'];rid=rc['run_id'];directory=tmp_path/rid
    monkeypatch.setattr(paths,'RUNS',str(tmp_path))
    monkeypatch.setattr(e0b,'prepare',lambda *a:plan)
    monkeypatch.setattr(e0b_preflight,'validate_native',lambda *a:None)
    monkeypatch.setattr(life,'require_session',lambda *a:None)
    monkeypatch.setattr(life,'unload',lambda *a:None)
    monkeypatch.setattr(e0b.time,'sleep',lambda *a:None)
    native=tmp_path/'native.json';native.write_text('{}')
    log=tmp_path/'server.log';log.write_text('')
    receipt=tmp_path/'receipt.json'
    receipt.write_text(json.dumps(dict(online_ok=True,identity=e0b.identity_for(plan),run_id=rid,
        server='http://fake',server_props={},server_log=str(log),native_evidence_path=str(native),
        native_evidence_sha256=provenance.file_sha(native))))
    units={u['key']:u for u in plan['units']}
    frozen=['determinism|'+s['arm']+'|'+s['unit_key'] for s in plan['determinism']]
    frozen += [arm+'|'+u['key'] for arm in ('C1','C2') for u in plan['units']]
    frozen += ['retry|V|'+u['key'] for u in plan['units'] if u['router']['retry']]
    sent=[]
    def http(url,payload=None,**kw):
        if url.endswith('/props'):return 200,{}
        key=frozen[len(sent)];sent.append(key)
        if key.startswith('determinism|'):
            _,arm,unit_key=key.split('|',2);text=units[unit_key][arm]['raw_content']
        else:text='{}'
        return 200,dict(choices=[dict(message=dict(content=text),finish_reason='stop')])
    monkeypatch.setattr(run,'http_json',http)
    monkeypatch.setattr(e0b,'score_response',lambda unit,arm,response,*a:dict(
        raw_content=response['choices'][0]['message']['content'],engine_error=False,prompt_tokens=1,completion_tokens=1,
        latency_ms=1,total_tokens=2,usage=dict(prompt_tokens=1,completion_tokens=1,total_tokens=2)))
    checks=[0]
    def sample(*a):
        checks[0]+=1
        if checks[0]==62:raise life.ResourceStop('Synthetic pause timeout after first C1 was persisted')
        return {}
    monkeypatch.setattr(resources,'check',sample)
    args=SimpleNamespace(preflight=str(receipt),server='http://fake',run_id=rid)
    with pytest.raises(life.ResourceStop):e0b.execute(rc,args)
    assert len(sent)==31
    first=(directory/'results.jsonl').read_bytes()
    monkeypatch.setattr(resources,'check',lambda *a:{})
    e0b.execute(rc,args)
    assert sent==frozen and len(sent)==662 and len(set(sent))==662
    assert (directory/'results.jsonl').read_bytes().startswith(first)
    assert len([x for x in paths.jsonl(directory/'request-budget.jsonl') if x['category']=='benchmark'])==662
    assert len(list((directory/'resource-stops').glob('*.json')))==1


@pytest.mark.parametrize('settled',[True,False])
def test_dedicated_server_settle_gate_model_free(tmp_path,monkeypatch,settled):
    import sys
    from sn import server
    rc=e0b.config();model=e0b.prepare(rc)['model']
    fake_model=tmp_path/'models'/model['gguf_file'];fake_model.parent.mkdir();fake_model.write_text('test placeholder')
    monkeypatch.setattr(e0b,'config',lambda *a:rc)
    monkeypatch.setattr(paths,'ROOT',str(tmp_path))
    profile=tmp_path/'profile.json';profile.write_text(json.dumps(model))
    monkeypatch.setattr(paths,'RUNS',str(tmp_path/'runs'))
    monkeypatch.setattr(e0b,'prepare',lambda *a:dict(model=model))
    monkeypatch.setattr(e0b,'identity_for',lambda *a:{'synthetic':True})
    monkeypatch.setattr(e0b,'campaign_budget',lambda *a:None)
    monkeypatch.setattr(life,'admission',lambda *a:None)
    monkeypatch.setattr(resources,'initialize_swap_baseline',lambda *a:None)
    monkeypatch.setattr(resources,'swap_snapshot',lambda:(16384,0))
    monkeypatch.setattr(resources,'check_swap_growth',lambda *a:0)
    monkeypatch.setattr(resources,'pressure_level',lambda:1)
    connected=[0]
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*a):pass
    def connect(*a,**kw):
        connected[0]+=1
        if connected[0]==1:raise OSError('no server before launch')
        return Connection()
    monkeypatch.setattr(server.socket,'create_connection',connect)
    class Process:
        pid=999999
        def poll(self):return None
        def wait(self,**kw):return 0
    launches=[];unloads=[]
    monkeypatch.setattr(server.subprocess,'Popen',lambda *a,**kw: launches.append((a,kw)) or Process())
    monkeypatch.setattr(life,'unload',lambda *a:unloads.append(a))
    def settle(*a,**kw):
        assert len(launches)==1
        if not settled:raise life.ResourceStop('synthetic settle timeout')
    monkeypatch.setattr(life,'settle',settle)
    monkeypatch.setattr(sys,'argv',['sn.server',str(fake_model),'8080','--config',str(profile),
                                    '--campaign-config','configs/runs/e0b.json'])
    if settled:
        with pytest.raises(SystemExit) as exc: server.main()
        assert exc.value.code==0
        assert json.loads((tmp_path/'runs'/rc['run_id']/'server-session.json').read_text())['settled']
    else:
        with pytest.raises(life.ResourceStop):server.main()
        assert len(unloads)==1
        assert json.loads((tmp_path/'runs'/rc['run_id']/'STOPPED.json').read_text())['resumable']
    assert launches[0][1]['start_new_session'] is True


def test_admission_failure_never_starts_model_process(tmp_path,monkeypatch):
    import sys
    from sn import server
    rc=e0b.config();model=e0b.prepare(rc)['model']
    fake_model=tmp_path/'models'/model['gguf_file'];fake_model.parent.mkdir();fake_model.write_text('test placeholder')
    monkeypatch.setattr(e0b,'config',lambda *a:rc)
    monkeypatch.setattr(paths,'ROOT',str(tmp_path))
    profile=tmp_path/'profile.json';profile.write_text(json.dumps(model))
    monkeypatch.setattr(paths,'RUNS',str(tmp_path/'runs'))
    monkeypatch.setattr(e0b,'prepare',lambda *a:dict(model=model))
    monkeypatch.setattr(e0b,'identity_for',lambda *a:{'synthetic':True})
    monkeypatch.setattr(e0b,'campaign_budget',lambda *a:None)
    monkeypatch.setattr(server.socket,'create_connection',lambda *a,**k:(_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(life,'admission',lambda *a:(_ for _ in ()).throw(life.ResourceStop('under 5 GiB')))
    monkeypatch.setattr(life,'unload',lambda *a:None)
    monkeypatch.setattr(server.subprocess,'Popen',lambda *a,**k:pytest.fail('Model process started'))
    monkeypatch.setattr(sys,'argv',['sn.server',str(fake_model),'8080','--config',str(profile),
                                    '--campaign-config','configs/runs/e0b.json'])
    with pytest.raises(life.ResourceStop):server.main()


def test_readiness_resume_skips_saved_probe_without_extra_charge(tmp_path,monkeypatch):
    from sn import e0b_preflight as pf
    rc=e0b.config();plan=e0b.prepare(rc);smoke=e0b.prepare(e0b.config('configs/runs/e0b_smoke.json'))
    model=plan['model'];rid=rc['run_id'];directory=tmp_path/'runs'/rid;directory.mkdir(parents=True)
    monkeypatch.setattr(pf,'prepare',lambda c:smoke if c['result_kind']=='path-smoke' else plan)
    monkeypatch.setattr(pf,'validate_native',lambda *a:None)
    monkeypatch.setattr(pf,'identity_for',lambda *a:{'synthetic':True})
    monkeypatch.setattr(pf.preflight,'runtime',lambda *a:{'synthetic':True})
    monkeypatch.setattr(pf.preflight,'plan',lambda *a:([],None))
    monkeypatch.setattr(pf.preflight,'context_checks',lambda *a:{'synthetic':True})
    monkeypatch.setattr(life,'require_session',lambda *a:None)
    monkeypatch.setattr(life,'unload',lambda *a:None)
    monkeypatch.setattr(life,'guard',lambda *a:{})
    monkeypatch.setattr(pf.time,'sleep',lambda *a:None)
    monkeypatch.setattr(pf,'smoke_gate',lambda *a,**kw:dict(passed=True,outcome='synthetic'))
    source=tmp_path/'analysis/e0-clean-v1';source.mkdir(parents=True)
    (source/'manifest.public.json').write_text(json.dumps(dict(server_props=dict(chat_template='synthetic'))))
    (tmp_path/'runs/server.8080.log').write_text('offloaded 29/29')
    native=tmp_path/'native.json';native.write_text('{}')
    original_root=Path(paths.ROOT)
    original_budget=e0b.campaign_budget
    def budget(directory,c):
        # Read SHA-pinned history from the real checkout, not the temporary fixture tree.
        monkeypatch.setattr(paths,'ROOT',str(original_root))
        try:return original_budget(directory,c)
        finally:monkeypatch.setattr(paths,'ROOT',str(tmp_path))
    monkeypatch.setattr(pf,'campaign_budget',budget)
    monkeypatch.setattr(pf,'config',lambda path:smoke['config'])
    monkeypatch.setattr(paths,'ROOT',str(tmp_path));monkeypatch.setattr(paths,'RUNS',str(tmp_path/'runs'))
    props=dict(build_info=model['llama_cpp_commit'][:7],model_path=str(tmp_path/'models'/model['gguf_file']),
               chat_template='synthetic',default_generation_settings=dict(n_ctx=8192))
    def response(text):return dict(choices=[dict(message=dict(content=text),finish_reason='stop')])
    first=response('{"answer":"SCHEMA_ONLY_739"}')
    historical=dict(key='preflight|C0|0',status=200,response=first,engine_log_errors=[])
    (directory/'readiness-results.jsonl').write_text(json.dumps(historical)+'\n')
    budget(directory,rc).reserve('readiness','preflight|C0|0')
    life.stop(directory,life.ResourceStop('synthetic readiness resource timeout'),'online_preflight_smoke')
    sent=[]
    def http(url,payload=None,**kw):
        if url.endswith('/props'):return 200,props
        sent.append(payload)
        if len(sent) in (1,3):return 200,response('{"n":7}')
        if len(sent)==2:return 200,first
        return 200,response('{}')
    monkeypatch.setattr(pf,'http_json',http)
    receipt=pf.online(rc,run_id=rid,server='http://fake',output=directory/'receipt.json',native_path=native)
    assert len(sent)==18 # Four probes + 15 smoke, minus one already durable probe.
    assert receipt['readiness_spent_cumulative']==30 and receipt['readiness_remaining']==30
    rows=paths.jsonl(directory/'readiness-results.jsonl')
    assert len(rows)==19 and len({r['key'] for r in rows})==19
    assert rows[0]==historical



def test_unload_waits_for_child_even_after_launcher_exits(tmp_path,monkeypatch):
    session=dict(pid=999999,binary='/synthetic/llama-server',model='/synthetic/test.gguf')
    (tmp_path/'server-session.json').write_text(json.dumps(session))
    clock=Clock();calls=[]
    snapshots=iter(['999999 S', '999999 Z'])
    def ps(command,**kwargs):
        if 'command=' in command:return SimpleNamespace(stdout='/usr/bin/time /synthetic/llama-server -m /synthetic/test.gguf')
        return SimpleNamespace(stdout=next(snapshots))
    monkeypatch.setattr(life.subprocess,'run',ps)
    monkeypatch.setattr(life.os,'getpgid',lambda pid:pid)
    monkeypatch.setattr(life.os,'killpg',lambda *args:calls.append(args))
    monkeypatch.setattr(life.time,'monotonic',clock)
    monkeypatch.setattr(life.time,'sleep',clock.sleep)
    life.unload(tmp_path)
    assert len(calls)==1 and clock.sleeps==[1]
    assert events(tmp_path)[-1]['event']=='unloaded'
