"""E0 integrity checks; all outputs here are synthetic, never model measurements."""
import copy
import json
import sys
from pathlib import Path
import pytest
from sn import paths, preflight, provenance, report, run


def config(name='e0_decoding'):
    return json.loads(Path(paths.ROOT, f'configs/runs/{name}.json').read_text())


def test_frozen_e0_pairing_and_smoke_coverage():
    rc = config()
    reqs, schemas = preflight.plan(rc)
    assert len(reqs) == 1200 and len(schemas) == 70
    arms = {a: {(f, c['catalog_id'] if c else None, t['task_id'])
                for f, arm, c, t in reqs if arm == a} for a in rc['arms']}
    assert all(v == next(iter(arms.values())) for v in arms.values())
    smoke, _ = preflight.plan(config('e0_smoke'))
    assert len(smoke) == 12
    assert {c['size'] if c else 1 for _, _, c, _ in smoke} == {1, 5, 20}
    rc['expected_requests'] = 1199
    with pytest.raises(ValueError, match='Expected'):
        preflight.plan(rc)


def test_duplicate_and_unknown_results_rejected():
    with pytest.raises(ValueError, match='Duplicate'):
        provenance.validate_rows([{'request_key': 'x'}] * 2, ['x'])
    with pytest.raises(ValueError, match='Unexpected'):
        provenance.validate_rows([{'request_key': 'y'}], ['x'])


def test_online_preflight_detects_ignored_schema(monkeypatch):
    def fake(url, payload=None, **kw):
        if url.endswith('/props'):
            return 200, {'model_path': '/checked.gguf'}
        return 200, {'choices': [{'message': {'content': '{"answer":"FORBIDDEN","n":0,"extra":true}'}, 'finish_reason': 'stop'}]}
    monkeypatch.setattr(run, 'http_json', fake)
    model = {'request_params': {}}
    import jsonschema
    with pytest.raises(jsonschema.ValidationError):
        preflight.online('http://fake', model, {})


def test_preflight_keeps_explicit_engine_refusals(monkeypatch):
    def fake(url, payload=None, **kw):
        if url.endswith('/props'):
            return 200, {'model_path': '/checked.gguf'}
        schema = payload['response_format']['json_schema']['schema']
        if payload['max_tokens'] == 1:
            return 400, {'error': 'grammar schema refused'}
        obj = {'answer': 'SCHEMA_ONLY_739'} if 'answer' in schema['properties'] else {'n': 7}
        return 200, {'choices': [{'message': {'content': json.dumps(obj)}, 'finish_reason': 'stop'}]}
    monkeypatch.setattr(run, 'http_json', fake)
    checks = preflight.online('http://fake', {'request_params': {}}, {'catalog': {}})
    assert checks['envelopes_accepted'] == 0 and 'catalog' in checks['envelope_refusals']


def test_context_overflow_is_detected(monkeypatch):
    monkeypatch.setattr(run, 'http_json', lambda url, *a, **kw:
                        (200, {'prompt': 'text'}) if url.endswith('/apply-template') else (200, {'tokens': list(range(20))}))
    reqs, _ = preflight.plan(config('e0_smoke'))
    model = {'request_params': {'max_tokens': 512, 'chat_template_kwargs': {'enable_thinking': False}}}
    with pytest.raises(ValueError, match='Context overflow'):
        preflight.context_checks('http://fake', model, config('e0_smoke'), reqs, {'default_generation_settings': {'n_ctx': 30}})


def test_changed_config_refuses_resume_and_partial_report(tmp_path, monkeypatch):
    from test_pipeline_smoke import Recording, _serve
    srv, url = _serve(Recording)
    monkeypatch.setattr(paths, 'RUNS', str(tmp_path / 'runs'))
    monkeypatch.setattr(paths, 'ANALYSIS', str(tmp_path / 'analysis'))
    rc = config('smoke')
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps(rc))
    args = ['run', '--config', str(cfg), '--run-id', 'partial', '--server', url, '--limit', '2']
    monkeypatch.setattr(sys, 'argv', args)
    try:
        run.main()
        results = tmp_path / 'runs/partial/results.jsonl'
        before = results.read_bytes()
        res = report.run('partial')
        assert not res['complete'] and not res['comparisons'] and res['missing_n'] == 18
        rc['cache_prompt'] = False
        cfg.write_text(json.dumps(rc))
        with pytest.raises(ValueError, match='Resume identity mismatch'):
            run.main()
        assert results.read_bytes() == before
    finally:
        srv.shutdown()
        srv.server_close()


def test_offline_receipt_cannot_authorize_real_run(tmp_path, monkeypatch):
    receipt = tmp_path / 'offline.json'
    receipt.write_text(json.dumps({'online_ok': False}))
    monkeypatch.setattr(sys, 'argv', ['run', '--config', 'configs/runs/e0_decoding.json', '--preflight', str(receipt)])
    with pytest.raises(ValueError, match='Preflight is offline'):
        run.main()


def test_engine_only_cells_render_valid_json(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'RUNS', str(tmp_path / 'runs'))
    monkeypatch.setattr(paths, 'ANALYSIS', str(tmp_path / 'analysis'))
    def fake(url, payload=None, **kwargs):
        if url.endswith('/props'):
            return 404, {}
        if 'response_format' in payload:
            return 400, {'error': 'grammar schema refused'}
        return 200, {'choices': [{'message': {'content': 'not JSON'}, 'finish_reason': 'stop'}]}
    monkeypatch.setattr(run, 'http_json', fake)
    monkeypatch.setattr(sys, 'argv', ['run', '--config', 'configs/runs/smoke.json', '--run-id', 'errors'])
    run.main()
    res = report.run('errors')
    assert res['complete'] and not res['inference_ready']
    assert res['infrastructure_failures'] == 10
    assert sum(sum(c['classes'].values()) for c in res['cells']) == 10
    assert 'NaN' not in (tmp_path / 'analysis/errors/report.json').read_text()
    assert 'NA' in (tmp_path / 'analysis/errors/REPORT.md').read_text()


def test_transport_failure_is_saved_before_stopping(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'RUNS', str(tmp_path / 'runs'))
    monkeypatch.setattr(run, 'http_json', lambda url, *a, **kw: (404, {}) if url.endswith('/props') else (0, {'error': 'offline'}))
    monkeypatch.setattr(sys, 'argv', ['run', '--config', 'configs/runs/smoke.json', '--run-id', 'offline'])
    with pytest.raises(RuntimeError, match='transport_error'):
        run.main()
    rows = paths.jsonl(tmp_path / 'runs/offline/results.jsonl')
    assert len(rows) == 1 and rows[0]['request_error'] == 'transport_error'


def test_silent_llguidance_fallback_is_detected(tmp_path, monkeypatch):
    log = tmp_path / 'server.log'
    log.write_text('old llg error: ignore this old request\n')
    offset = log.stat().st_size
    assert provenance.engine_log_errors(log, offset) == []
    with log.open('a') as f:
        f.write('llg error: Unimplemented keys: [dependencies]\n')
    assert provenance.engine_log_errors(log, offset)
    log.write_text('')
    with pytest.raises(ValueError, match='truncated'):
        provenance.engine_log_errors(log, offset)


def test_http_200_silent_fallback_is_not_accepted_by_preflight(tmp_path, monkeypatch):
    log = tmp_path / 'server.log'
    log.write_text('')
    def fake(url, payload=None, **kw):
        if url.endswith('/props'):
            return 200, {}
        if payload['max_tokens'] == 1:
            with log.open('a') as f:
                f.write('llg error: unsupported schema\n')
            obj = {}
        else:
            schema = payload['response_format']['json_schema']['schema']
            obj = {'answer': 'SCHEMA_ONLY_739'} if 'answer' in schema['properties'] else {'n': 7}
        return 200, {'choices': [{'message': {'content': json.dumps(obj)}, 'finish_reason': 'stop'}]}
    monkeypatch.setattr(run, 'http_json', fake)
    checks = preflight.online('http://fake', {'request_params': {}}, {'catalog': {}}, server_log=str(log))
    assert checks['envelopes_accepted'] == 0
    assert checks['envelope_refusals']['catalog']['http_status'] == 200


def test_explicit_llguidance_transport_bypasses_jinja_schema_lowering():
    schema = {"type": "object", "properties": {"a": {"const": 1}}}
    payload = run.constraint_payload(schema, "llguidance_grammar")
    assert set(payload) == {"grammar"}
    assert payload["grammar"].startswith("%llguidance {}\nstart: %json ")
    assert json.loads(payload["grammar"].split("%json ", 1)[1]) == schema
