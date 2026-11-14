"""Post-hoc key-order diagnostic using the exact bundled engine, without inference.

Reorders keys of the same JSON value, never gold or model inference inputs. A rejection
is called order-only only when reordering rescues it. This is not a causal experiment.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess

from . import envelope, paths, preflight, provenance
from .native_audit import verified_build
import schema_utils as su


def audit(run_id):
    source = Path(paths.RUNS, run_id)
    manifest = json.loads((source / 'manifest.json').read_text())
    # Analysis code may evolve after inference; dataset/prompt/schema bytes must not.
    recorded_inputs = provenance.inputs()
    for name in recorded_inputs:
        if name.startswith('schema-native/sn/'):
            original = subprocess.check_output(['git', 'show', manifest['git_commit'] + ':' + name], cwd=paths.REPO)
            recorded_inputs[name] = hashlib.sha256(original).hexdigest()
    if provenance.digest(recorded_inputs) != manifest['identity']['inputs_sha256']:
        raise ValueError('Frozen inputs differ from the recorded inference run')
    rows = paths.jsonl(source / 'results.jsonl')
    requests, schemas = preflight.plan(manifest['run_config'])
    provenance.validate_rows(rows, manifest['expected_request_keys'])
    if len(rows) != len(manifest['expected_request_keys']):
        raise ValueError('Order audit requires a complete paired run')
    lookup = {preflight.request_key(*r): r for r in requests}
    binary = Path(paths.ROOT, '.tools/native-llg-audit')
    engine = Path(os.environ.get('TOOLS_DIR', str(Path(paths.ROOT, '.tools'))),
                  'llama.cpp/build-metal/llguidance/source')
    build = verified_build(binary, engine / 'target/release/libllguidance.a')
    if build['library_sha256'] != json.loads(Path(paths.ANALYSIS, 'e0-compatibility/native-clean.json').read_text())['library_sha256']:
        raise ValueError('Library differs from recorded clean-run engine audit')
    grouped = collections.defaultdict(list)
    for row in rows:
        family, arm, cat, task = lookup[row['request_key']]
        name = cat['catalog_id'] if cat else 'single:' + task['tool_id']
        grouped[name].append(row)
    details = []
    process = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        for name, group in grouped.items():
            samples, labels = [], []
            for row in group:
                if row['decoding'] == 'free' and row['eval']['e2e_success']:
                    try:
                        call = json.loads(row['raw_content'])
                    except ValueError:
                        continue
                    if not isinstance(call, dict) or set(call) != {'tool', 'arguments'}:
                        continue
                    tool = paths.pool()[row['tool_id']]
                    raw = su.load_schema(tool['schema_id'])
                    branch = envelope.tool_branch(tool['tool_name'], raw, manifest['run_config']['constraint_policy'])
                    ordered = envelope.ordered_like_schema(call, branch)
                    assert ordered == call
                    for kind, value in [('original_order', call), ('schema_order', ordered)]:
                        samples.append(envelope.dumps_compact(value))
                        labels.append((row, kind))
                elif row['decoding'] == 'constrained' and row['truncated']:
                    samples.append(row['raw_content'])
                    labels.append((row, 'truncated_prefix'))
            process.stdin.write(json.dumps({'schema': schemas[name], 'samples': samples}) + '\n')
            process.stdin.flush()
            result = json.loads(process.stdout.readline())
            if not result['compile_ok']:
                raise ValueError('Recorded envelope refused: ' + name)
            for index, (row, kind) in enumerate(labels):
                details.append({'request_key': row['request_key'], 'tool_id': row['tool_id'],
                                'kind': kind, 'accepted': result['accepts'][index],
                                'legal_prefix': result['legal_prefix'][index]})
    finally:
        process.stdin.close()
        process.wait()
    evidence = collections.defaultdict(dict)
    for item in details:
        evidence[item['request_key']][item['kind']] = item
    by_key = {r['request_key']: r for r in rows}
    split = collections.defaultdict(collections.Counter)
    for key, info in evidence.items():
        if 'original_order' not in info:
            continue
        a, b = info['original_order']['accepted'], info['schema_order']['accepted']
        category = 'accepted_original_order' if a else ('order_only_rejection' if b else 'other_rejection')
        free = by_key[key]
        cd_arm = {'A_raw_free': 'B_raw_cd', 'A2_min_free': 'B2_min_cd'}[free['arm']]
        cd_key = key.replace('|' + free['arm'] + '|', '|' + cd_arm + '|', 1)
        cd = by_key[cd_key]
        outcome = 'truncated' if cd['truncated'] else ('correct' if cd['eval']['e2e_success'] else 'wrong')
        for name in ('pooled', free['arm'], free['family'] + ':' + str(free['size'])):
            split[name][category + '|' + outcome] += 1
    return {'run': run_id, 'kind': 'post-hoc native byte-token order diagnostic; no inference',
            'source_results_sha256': provenance.file_sha(source / 'results.jsonl'),
            'engine_build': build, 'tested_free_correct': sum('original_order' in v for v in evidence.values()),
            'all_free_correct': sum(r['decoding'] == 'free' and r['eval']['e2e_success'] for r in rows),
            'truncated_prefixes': [d for d in details if d['kind'] == 'truncated_prefix'],
            'split': {k: dict(v) for k, v in split.items()}, 'details': details}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='e0-clean-v1')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = audit(args.run)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('details', 'truncated_prefixes')}, indent=2))
    print('Truncations that are legal grammar prefixes:',
          sum(d['legal_prefix'] for d in result['truncated_prefixes']), '/', len(result['truncated_prefixes']))


if __name__ == '__main__':
    main()
