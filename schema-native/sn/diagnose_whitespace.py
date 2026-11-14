"""Small, outcome-selected diagnostics; never an independent accuracy benchmark.

Replays six first truncations (family/size/representation strata) and three first
successful raw controls. Keeps the completed source run immutable. Output plans
freeze every payload; interrupted probes resume only an identical plan.
"""
import argparse
import copy
import gzip
import json
from pathlib import Path
import time

import jsonschema
from . import envelope, paths, preflight, provenance, resources
from .run import constraint_payload, http_json
from evaluate import evaluate, schema_errors
import schema_utils as su


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-run', default='e0-clean-v1')
    parser.add_argument('--output', required=True)
    parser.add_argument('--server', default='http://127.0.0.1:8080')
    args = parser.parse_args()
    source = Path(paths.RUNS, args.source_run)
    manifest = json.loads((source / 'manifest.json').read_text())
    rows = paths.jsonl(source / 'results.jsonl')
    rc = manifest['run_config']
    requests, schemas = preflight.plan(rc)
    lookup = {preflight.request_key(*r): r for r in requests}
    chosen = []
    for size in (5, 20, 1):
        for representation in ('raw', 'minified'):
            chosen.append(next(r for r in rows if r['decoding'] == 'constrained'
                               and r['size'] == size and r['representation'] == representation
                               and r['truncated']))
    for size in (5, 20, 1):
        chosen.append(next(r for r in rows if r['decoding'] == 'constrained'
                           and r['size'] == size and r['representation'] == 'raw'
                           and r['eval']['e2e_success']))
    plan = []
    for row in chosen:
        fam, arm, cat, task = lookup[row['request_key']]
        schema = schemas[cat['catalog_id'] if cat else 'single:' + task['tool_id']]
        system = gzip.open(source / 'prompts' / (row['system_prompt_sha256'][:16] + '.txt.gz'), 'rt').read()
        assert provenance.file_sha(source / 'results.jsonl')
        for variant in ('llguidance_flexible', 'llguidance_compact', 'gbnf_response_format'):
            constraint = copy.deepcopy(schema)
            if variant == 'llguidance_compact':
                constraint['x-guidance'] = {'whitespace_flexible': False}
            payload = dict(manifest['model_config']['request_params'])
            payload.update(cache_prompt=rc['cache_prompt'], messages=[
                {'role': 'system', 'content': system}, {'role': 'user', 'content': row['user_message']}])
            payload.update(constraint_payload(constraint, 'response_format' if variant == 'gbnf_response_format'
                                              else 'llguidance_grammar'))
            plan.append({'key': row['request_key'] + '|' + variant, 'variant': variant,
                         'source_key': row['request_key'], 'source_truncated': row['truncated'],
                         'payload': payload, 'schema': constraint})
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    st, props = http_json(args.server + '/props', timeout=30)
    if st != 200:
        raise RuntimeError('Dedicated server unavailable')
    identity = {'source_results_sha256': provenance.file_sha(source / 'results.jsonl'),
                'source_manifest_sha256': provenance.file_sha(source / 'manifest.json'),
                'plan': plan, 'server_props': props,
                'diagnostic_source_sha256': provenance.file_sha(__file__)}
    frozen = output / 'plan.json'
    if frozen.exists():
        if json.loads(frozen.read_text()) != identity:
            raise ValueError('Diagnostic identity changed; use a separate output directory')
    else:
        frozen.write_text(json.dumps(identity, indent=2) + '\n')
    result_path = output / 'results.jsonl'
    saved = paths.jsonl(result_path) if result_path.exists() else []
    provenance.validate_rows(saved, [p['key'] for p in plan])
    done = {r['request_key'] for r in saved}
    log = Path(paths.RUNS, 'server.8080.log')
    state = {}
    pool = paths.pool()
    with result_path.open('a') as stream:
        for p in plan:
            if p['key'] in done:
                continue
            health = resources.check(rc, state)
            offset = log.stat().st_size
            start = time.monotonic()
            status, response = http_json(args.server + '/v1/chat/completions', p['payload'])
            elapsed = time.monotonic() - start
            errors = provenance.engine_log_errors(log, offset)
            ch = (response.get('choices') or [{}])[0]
            text = ch.get('message', {}).get('content') or ''
            fam, arm, cat, task = lookup[p['source_key']]
            ids = cat['presentation_order'] if cat else [task['tool_id']]
            raw = su.load_schema(pool[task['tool_id']]['schema_id'])
            ev = evaluate(text, task, raw, {pool[i]['tool_name'] for i in ids})
            violation = None
            if status == 200 and not errors and ch.get('finish_reason') != 'length':
                try:
                    call = json.loads(text)
                    jsonschema.Draft7Validator(p['schema']).validate(call)
                    selected = next(i for i in ids if pool[i]['tool_name'] == call['tool'])
                    raw_errors = schema_errors(call['arguments'], su.load_schema(pool[selected]['schema_id']))
                    if raw_errors:
                        violation = str(raw_errors)
                except (ValueError, KeyError, StopIteration, jsonschema.ValidationError) as exc:
                    violation = str(exc)
            result = {'request_key': p['key'], 'variant': p['variant'],
                      'source_truncated': p['source_truncated'], 'http_status': status,
                      'response': response, 'engine_log_errors': errors,
                      'constraint_violation': violation, 'resource_check': health,
                      'elapsed_seconds': elapsed, 'eval': ev}
            stream.write(json.dumps(result) + '\n')
            stream.flush()
            print(p['variant'], p['source_key'], status, ch.get('finish_reason'),
                  'E2E', ev['e2e_success'], 'engine_errors', len(errors), flush=True)
            if status == 0 or status >= 500 or violation:
                raise RuntimeError('Diagnostic fault saved; inspect before continuing')
            time.sleep(rc['request_cooldown_seconds'])


if __name__ == '__main__':
    main()
