"""Locked E0b planning and a fail-closed, budgeted runner. Never starts a server.

Preparing/validating a plan is model-free. Execution requires a separate online receipt,
30 exact determinism matches and explicit invocation; imports do no network work.
"""
import argparse
import copy
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from . import paths, provenance, preflight, envelope, resources
from .constraint_options import apply, FIXED
from .oracle_order import reorder_envelope
from .router import route
from .lookalike import key_flags, failure_class
import prompts
import schema_utils as su
from evaluate import evaluate


def ordered_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def config(path='configs/runs/e0b.json'):
    return json.loads(Path(paths.ROOT, path).read_text())


def tools_for(cat, task):
    pool = paths.pool()
    ids = cat['presentation_order'] if cat else [task['tool_id']]
    return {pool[i]['tool_name']: su.load_schema(pool[i]['schema_id']) for i in ids}


def prepare(rc):
    expected_cap = {'benchmark':1000,'path-smoke':0}.get(rc['result_kind'])
    if rc['protocol'] != 'e0b-locked-v1' or expected_cap is None or rc['benchmark_request_cap'] != expected_cap:
        raise ValueError('Not a locked E0b configuration')
    if rc['result_kind']=='benchmark' and (rc['determinism']['requests']!=30 or rc['determinism']['per_arm']!=15):
        raise ValueError('Locked determinism check requires 15 F0 plus 15 C0 requests')
    if rc['preflight_smoke_request_cap'] != 60 or rc['retry_cap'] != 70:
        raise ValueError('Locked E0b budget changed')
    raw = gzip.decompress(Path(paths.ANALYSIS, rc['source_run'], 'results.jsonl.gz').read_bytes())
    if hashlib.sha256(raw).hexdigest() != rc['source_results_sha256']:
        raise ValueError('Source E0 results changed')
    manifest = json.loads(Path(paths.ANALYSIS, rc['source_run'], 'manifest.public.json').read_text())
    recorded = provenance.inputs()
    for name in recorded:
        if name.startswith('schema-native/sn/'):
            original = subprocess.check_output(['git', 'show', manifest['git_commit'] + ':' + name], cwd=paths.REPO)
            recorded[name] = hashlib.sha256(original).hexdigest()
    if provenance.digest(recorded) != manifest['identity']['inputs_sha256']:
        raise ValueError('Frozen dataset/prompts/schema inputs changed')
    model = json.loads(Path(paths.ROOT, rc['model_config']).read_text())
    if model != manifest['model_config']:
        raise ValueError('E0b must retain the recorded E0 model profile')
    baseline = {r['request_key']: r for r in map(json.loads, raw.splitlines())}
    requests, _ = preflight.plan(rc)
    units = []
    for family, arm, cat, task in requests:
        if arm != 'F0':
            continue
        old_key = preflight.request_key(family, 'A_raw_free', cat, task)
        free = baseline[old_key]
        cd = baseline[old_key.replace('|A_raw_free|', '|B_raw_cd|')]
        tools = tools_for(cat, task)
        base = envelope.envelope(list(tools.items()), rc['constraint_policy'])
        oracle, flags = reorder_envelope(base, free['raw_content'], tools, truncated=free['truncated'])
        msgs = prompts.messages_select('raw', cat['presentation_order'], task) if cat else prompts.messages_arggen('raw', task)
        if prompts.sha(msgs[0]['content']) != free['system_prompt_sha256'] or msgs[1]['content'] != free['user_message']:
            raise ValueError('Original E0 messages differ')
        units.append({'key': preflight.request_key(family, 'UNIT', cat, task), 'family': family,
                      'cat': cat, 'task': task, 'tools': tools, 'messages': msgs,
                      'F0': free, 'C0': cd, 'C1_schema': apply(base, FIXED),
                      'C2_schema': apply(oracle, FIXED), 'C3_schema': base,
                      'oracle_flags': flags,
                      'router': route(free['raw_content'], tools, truncated=free['truncated'])})
    if sum(u['router']['retry'] for u in units) > rc['retry_cap']:
        raise ValueError('Frozen strict router exceeds 70-retry cap; stop, do not drop units')
    samples = []
    for arm in (('F0', 'C0') if rc['result_kind'] == 'benchmark' else ()):
        ranked = sorted(units, key=lambda u: hashlib.sha256((rc['determinism']['seed'] + '\0' + u[arm]['request_key']).encode()).hexdigest())
        samples += [{'arm': arm, 'unit_key': u['key'], 'source_key': u[arm]['request_key'],
                     'expected_content_sha256': hashlib.sha256(u[arm]['raw_content'].encode()).hexdigest()}
                    for u in ranked[:15]]
    return {'config': rc, 'model': model, 'units': units, 'determinism': samples,
            'new_benchmark_requests': 3*len(units) + len(samples) + sum(u['router']['retry'] for u in units) if rc['result_kind'] == 'benchmark' else 0,
            'source_results_sha256': rc['source_results_sha256']}


class Budget:
    """Durable before-send reservations. Crashed/failed requests still consume the cap."""
    def __init__(self, path, benchmark_cap=1000, readiness_cap=60):
        self.path = Path(path)
        self.caps = {'benchmark': benchmark_cap, 'readiness': readiness_cap}
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def reserve(self, category, key):
        with self.path.open('a+') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.seek(0)
            rows = [json.loads(s) for s in stream if s.strip()]
            if any(r['key'] == key for r in rows):
                raise ValueError('Attempt already reserved: inspect uncertain/failed request; no automatic retry')
            if sum(r['category'] == category for r in rows) >= self.caps[category]:
                raise ValueError(category + ' request cap reached')
            stream.seek(0, os.SEEK_END)
            stream.write(json.dumps({'category': category, 'key': key}) + '\n')
            stream.flush()
            os.fsync(stream.fileno())


def payload_for(plan, unit, arm):
    from .run import constraint_payload
    payload = dict(plan['model']['request_params'], cache_prompt=plan['config']['cache_prompt'], messages=unit['messages'])
    if arm != 'F0':
        definition = plan['config']['arm_defs'][arm]
        schema = unit['C1_schema'] if arm == 'V' else unit.get(arm + '_schema')
        if arm == 'C0':
            schema = unit['C3_schema']
        payload.update(constraint_payload(schema, definition['transport']))
    return payload


def identity_for(plan):
    return {'plan_sha256': ordered_hash(plan),
            'source_hashes': {str(p.relative_to(paths.ROOT)): provenance.file_sha(p)
                              for p in Path(paths.HERE).glob('*.py') if ' ' not in p.name},
            'environment': provenance.environment()}


def aggregate_retry(free, retry):
    return dict(retry, wall_latency_ms=retry['wall_latency_ms']+free['wall_latency_ms'],
                retry_wall_latency_ms=retry['wall_latency_ms'],
                usage={k:free['usage'].get(k,0)+retry['usage'].get(k,0)
                       for k in ('prompt_tokens','completion_tokens','total_tokens')},
                cost_note='Free attempt reused; retry fresh. Summed recorded times, not fresh end-to-end wall time.')


def truncation_location(text):
    in_string = False; escaped = False
    for char in text:
        if in_string:
            if escaped: escaped = False
            elif char == '\\': escaped = True
            elif char == '"': in_string = False
        elif char == '"': in_string = True
    return 'in_string' if in_string else 'between_tokens'


def reused_diagnostics(unit, arm, row):
    """Flags on a copy; use the recorded evaluator result, never re-score the baseline."""
    decision=route(row['raw_content'],unit['tools'],truncated=row['truncated'])
    call=decision['call']
    lookalikes=key_flags(call['arguments'],envelope.argument_schema(unit['tools'][call['tool']])) if call and call['tool'] in unit['tools'] else []
    flags={'engine_refusal':bool(row.get('engine_error') or row.get('request_error')),
           'cd_truncated':arm=='C0' and row['truncated'],'invalid':decision['retry'],
           'wrong_tool':not row['eval']['tool_correct'],'lookalike_key':bool(lookalikes),
           'oracle_not_applied':False,'oracle_incomplete':False,
           'truncation_location':truncation_location(row['raw_content']) if row['truncated'] else None}
    label=failure_class(engine_refusal=flags['engine_refusal'],truncated=flags['cd_truncated'],
                        invalid=flags['invalid'],wrong_tool=flags['wrong_tool'],
                        lookalike_key=flags['lookalike_key'],correct=row['eval']['e2e_success'])
    return {'diagnostic_flags':flags,'failure_class':label,'retry_performed':False}


def score_response(unit, arm, response, status, errors):
    malformed = False
    try:
        choice = response['choices'][0]
        content = choice['message']['content']
        if not isinstance(content, str): raise ValueError('Non-text response')
    except (KeyError, IndexError, TypeError, ValueError):
        choice = {}; content = ''; malformed = True
    truncated = choice.get('finish_reason') == 'length'
    routed = route(content, unit['tools'], truncated=truncated)
    call = routed['call']
    lookalikes = key_flags(call['arguments'], envelope.argument_schema(unit['tools'][call['tool']])) if call and call['tool'] in unit['tools'] else []
    task = unit['task']
    target = paths.pool()[task['tool_id']]
    ev = evaluate(content, task, su.load_schema(target['schema_id']), set(unit['tools']))
    engine_fault = malformed or status != 200 or bool(errors) or (arm != 'F0' and not truncated and routed['retry'])
    if engine_fault:
        ev['e2e_success'] = ev['e2e_strict'] = False
    flags = {'engine_refusal': engine_fault, 'cd_truncated': truncated and arm != 'F0',
             'invalid': routed['retry'], 'wrong_tool': not ev['tool_correct'],
             'lookalike_key': bool(lookalikes), 'oracle_not_applied': arm == 'C2' and unit['oracle_flags']['oracle_not_applied'],
             'oracle_incomplete': arm == 'C2' and unit['oracle_flags']['oracle_incomplete'],
             'truncation_location': truncation_location(content) if truncated else None}
    return {'raw_content': content, 'finish_reason': choice.get('finish_reason'), 'truncated': truncated,
            'http_status': status, 'engine_error': engine_fault, 'engine_log_errors': errors,
            'request_error': 'engine_or_request_fault' if engine_fault else None,
            'usage': response.get('usage', {}), 'eval': ev, 'diagnostic_flags': flags,
            'failure_class': failure_class(engine_refusal=engine_fault, truncated=flags['cd_truncated'],
                                            invalid=flags['invalid'], wrong_tool=flags['wrong_tool'],
                                            lookalike_key=flags['lookalike_key'], correct=ev['e2e_success'])}


def execute(rc, args):
    from .run import http_json
    if rc['result_kind'] != 'benchmark':
        raise ValueError('Use E0b readiness smoke phase with its shared campaign ledger')
    plan = prepare(rc)
    if len(plan['determinism']) != 30:
        raise ValueError('Determinism requires exactly 30 requests')
    readiness = json.loads(Path(args.preflight).read_text()) if args.preflight else {}
    identity = identity_for(plan)
    if not readiness.get('online_ok') or readiness.get('identity') != identity or readiness.get('server') != args.server:
        raise ValueError('Fresh matching E0b online readiness receipt required; no request sent')
    from .e0b_preflight import validate_native
    native_path = readiness['native_evidence_path']
    if provenance.file_sha(native_path) != readiness['native_evidence_sha256']:
        raise ValueError('Native readiness evidence changed')
    validate_native(plan, json.loads(Path(native_path).read_text()))
    run_id = args.run_id
    if not run_id or not run_id.startswith('e0b-') or Path(run_id).name != run_id:
        raise ValueError('Use a new e0b- run ID')
    directory = Path(paths.RUNS, run_id)
    if readiness.get('run_id') != run_id:
        raise ValueError('Preflight/smoke budget must belong to this same campaign')
    directory.mkdir(exist_ok=True)
    with (directory / '.writer.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest_path = directory / 'manifest.json'
        if manifest_path.exists() and json.loads(manifest_path.read_text()) != identity:
            raise ValueError('E0b resume identity changed')
        manifest_path.write_text(json.dumps(identity, indent=2) + '\n')
        if (directory / 'STOPPED.json').exists():
            raise ValueError('Campaign stopped; inspect failure. No automatic baseline rerun.')
        budget = Budget(directory / 'request-budget.jsonl')
        output = directory / 'results.jsonl'
        saved = paths.jsonl(output) if output.exists() else []
        expected = {arm+'|'+u['key'] for u in plan['units'] for arm in rc['arms']}
        expected |= {'retry|V|'+u['key'] for u in plan['units'] if u['router']['retry']}
        expected |= {'determinism|'+s['arm']+'|'+s['unit_key'] for s in plan['determinism']}
        provenance.validate_rows(saved, expected)
        done = {r['request_key']: r for r in saved}
        health_state = {}
        units = {u['key']: u for u in plan['units']}
        log = Path(readiness['server_log'])
        st, props = http_json(args.server + '/props')
        if st != 200 or props != readiness['server_props']:
            raise ValueError('Server identity changed after preflight')

        def request(unit, arm, key, category='benchmark'):
            if key in done:
                return done[key]
            health = resources.check(rc, health_state)
            offset = log.stat().st_size
            budget.reserve(category, key)
            started = time.monotonic()
            status, response = http_json(args.server + '/v1/chat/completions', payload_for(plan, unit, arm))
            errors = provenance.engine_log_errors(log, offset)
            result = score_response(unit, arm, response, status, errors)
            result.update(request_key=key, arm=arm, unit_key=unit['key'], family=unit['family'],
                          size=unit['F0']['size'], catalog_id=unit['F0']['catalog_id'],
                          replicate=unit['F0']['replicate'], task_id=unit['task']['task_id'],
                          intent_id=unit['task']['intent_id'], tool_id=unit['task']['tool_id'],
                          representation='raw', decoding='free' if arm == 'F0' else 'constrained',
                          wall_latency_ms=1000*(time.monotonic()-started), resource_check=health,
                          constraint_option=rc['arm_defs'][arm].get('constraint_option'),
                          constraint_transport=rc['arm_defs'][arm].get('transport'), evidence_kind='fresh')
            with output.open('a') as stream:
                stream.write(json.dumps(result) + '\n'); stream.flush(); os.fsync(stream.fileno())
            done[key] = result
            if result['engine_error']:
                (directory / 'STOPPED.json').write_text(json.dumps({'reason': 'engine_or_request_fault', 'key': key}))
                raise RuntimeError('Engine/request fault saved; stop')
            time.sleep(rc['request_cooldown_seconds'])
            return result

        for sample in plan['determinism']:
            unit = units[sample['unit_key']]
            arm = sample['arm']
            result = request(unit, arm, 'determinism|' + arm + '|' + unit['key'])
            if result['raw_content'].encode() != unit[arm]['raw_content'].encode():
                (directory / 'STOPPED.json').write_text(json.dumps({'reason': 'determinism_failed', 'key': result['request_key']}))
                raise RuntimeError('Determinism failed; STOP. F0/C0 will not be rerun.')
        # Baselines are explicitly reused only after all 30 exact checks pass.
        for unit in plan['units']:
            for arm in ('F0', 'C0', 'C1', 'C2', 'C3', 'V'):
                key = arm + '|' + unit['key']
                if key in done:
                    continue
                if arm in ('F0', 'C0') or (arm == 'V' and not unit['router']['retry']):
                    base = unit[arm] if arm != 'V' else unit['F0']
                    result = dict(base, request_key=key, arm=arm, evidence_kind='reused',
                                  source_request_key=base['request_key'], unit_key=unit['key'],
                                  **reused_diagnostics(unit,arm,base))
                else:
                    result = request(unit, arm, 'retry|' + key if arm == 'V' else key)
                    if arm != 'V':
                        continue
                    result = aggregate_retry(unit['F0'], result)
                    result['retry_performed'] = True
                    # An aggregate V row has a different key from its charged retry attempt.
                    result['request_key'] = key
                with output.open('a') as stream:
                    stream.write(json.dumps(result) + '\n'); stream.flush(); os.fsync(stream.fileno())
                done[result['request_key']] = result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/runs/e0b.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    plan = prepare(config(args.config))
    destination = Path(args.output)
    if destination.exists():
        raise ValueError('Never overwrite a frozen plan; use a fresh path')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(plan, indent=2) + '\n')
    print('Prepared', len(plan['units']), 'units;', plan['new_benchmark_requests'], 'projected new requests; no inference')


if __name__ == '__main__':
    main()
