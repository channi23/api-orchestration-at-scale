"""No-server native engine coverage and strict-router replay for locked E0b."""
import argparse
import copy
import gzip
import json
from pathlib import Path
import subprocess

import jsonschema
from . import paths, provenance, envelope, preflight
from .e0b import config, prepare, ordered_hash, tools_for
from .oracle_order import reorder_envelope
from .constraint_options import apply, FIXED
from .native_audit import verified_build
from .router import route, strict_loads
from .report import lookalike_key_flag
import schema_utils as su


class Native:
    def __init__(self, binary, template=None):
        self.proc = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True)
        self.template = template

    def check(self, schema, samples):
        request = {'schema': schema, 'samples': samples}
        if self.template is not None:
            request['chat_template'] = self.template
        self.proc.stdin.write(json.dumps(request) + '\n'); self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('Native matcher exited before returning evidence')
        result = json.loads(line)
        result.pop('grammar', None)
        return result

    def close(self):
        self.proc.stdin.close()
        if self.proc.wait() != 0:
            raise RuntimeError('Native helper failed')


def invalid_calls(gold, tools):
    """Finite mutation witnesses, filtered using the strict raw-schema router."""
    candidates = []
    def walk(node, path):
        if isinstance(node, dict):
            for key, child in node.items():
                altered = copy.deepcopy(gold); parent = altered
                for part in path: parent = parent[part]
                del parent[key]; candidates.append(altered)
                walk(child, path + [key])
        elif isinstance(node, list):
            for index, child in enumerate(node): walk(child, path + [index])
        else:
            for replacement in (None, '__INVALID__', -999999999, {}, []):
                altered = copy.deepcopy(gold); parent = altered
                for part in path[:-1]: parent = parent[part]
                parent[path[-1]] = replacement; candidates.append(altered)
    walk(gold['arguments'], ['arguments'])
    candidates += [dict(gold, tool='__NOT_IN_CATALOG__'), {'tool': gold['tool']}, dict(gold, extra=True)]
    seen = set(); result = []
    for value in candidates:
        text = envelope.dumps_spaced(value)
        if text not in seen and route(text, tools)['retry']:
            result.append(text); seen.add(text)
    return result


def replay(units):
    result = {}
    for family in ('select', 'arggen'):
        group = [u for u in units if u['family'] == family]
        routed = [u for u in group if u['router']['retry']]
        tokens = lambda r: r['usage'].get('total_tokens', 0)
        result[family] = {'n': len(group), 'routed': len(routed),
            'routed_keys': [u['key'] for u in routed],
            'free_e2e_pct': 100 * sum(u['F0']['eval']['e2e_success'] for u in group) / len(group),
            'projected_e2e_pct': 100 * sum(u['C0' if u['router']['retry'] else 'F0']['eval']['e2e_success'] for u in group) / len(group),
            'token_ratio': 1 + sum(tokens(u['C0']) for u in routed) / sum(tokens(u['F0']) for u in group),
            'recorded_latency_ratio': 1 + sum(u['C0']['wall_latency_ms'] for u in routed) / sum(u['F0']['wall_latency_ms'] for u in group)}
    return result


def audit(rc):
    plan = prepare(rc)
    root = Path(paths.ROOT)
    engine = root / '.tools/llama.cpp'
    llg = root / '.tools/native-llg-audit'
    build = verified_build(llg, engine / 'build-metal/llguidance/source/target/release/libllguidance.a')
    bundled = engine/'build-metal/llguidance/source'
    if subprocess.check_output(['git','-C',str(bundled),'rev-parse','HEAD'],text=True).strip() != plan['model']['llguidance_commit']:
        raise ValueError('Bundled llguidance commit differs from pinned model profile')
    original_library = json.loads((root/'analysis/e0-compatibility/native-clean.json').read_text())['library_sha256']
    if build['library_sha256'] != original_library:
        raise ValueError('Native library differs from the recorded E0 bundled binary')
    for checkout in (engine,bundled):
        if subprocess.check_output(['git','-C',str(checkout),'status','--porcelain','--untracked-files=no'],text=True).strip():
            raise ValueError('Native engine has tracked source changes')
    gbnf = root / '.tools/native-gbnf-audit'
    gbnf_build = json.loads(gbnf.with_suffix('.build.json').read_text())
    for name in gbnf_build:
        p = gbnf if name == gbnf.name else engine / 'build-metal/bin' / name
        if provenance.file_sha(p) != gbnf_build[name]:
            raise ValueError('GBNF helper/shared library changed; rebuild audit helper')
    if subprocess.check_output(['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True).strip() != rc['c3']['llama_cpp_commit']:
        raise ValueError('C3 backend is not pinned commit')
    manifest = json.loads((root / 'analysis/e0-clean-v1/manifest.public.json').read_text())
    template = manifest['server_props']['chat_template']
    native = Native(llg)
    other = Native(gbnf, template)
    c1 = {}; c3 = {}; c2 = []; tuple_paths = []; gold_count = 0
    def tuples(node, path):
        if not isinstance(node, dict): return
        if isinstance(node.get('items'), list) or isinstance(node.get('prefixItems'), list): tuple_paths.append(path)
        # use known schema positions, not literal const/enum data
        for key in su.SCHEMA_MAP_KEYS:
            for name, child in node.get(key, {}).items(): tuples(child, path + '/' + key + '/' + name)
        for key in su.SCHEMA_LIST_KEYS:
            for index, child in enumerate(node.get(key, [])): tuples(child, path + '/' + key + '/' + str(index))
        for key in su.SCHEMA_SINGLE_KEYS:
            child = node.get(key)
            if isinstance(child, list):
                for index, value in enumerate(child): tuples(value, path + '/' + key + '/' + str(index))
            else: tuples(child, path + '/' + key)
    grouped = {}
    for unit in plan['units']:
        name = unit['cat']['catalog_id'] if unit['cat'] else 'single:' + unit['task']['tool_id']
        grouped.setdefault(name, []).append(unit)
    def summarize(result, n_gold, n_free, labels, samples):
        accepts = result.get('accepts', [])
        return {'compile_ok': result['compile_ok'], 'error': result.get('error'),
                'conversion_diagnostics': result.get('conversion_diagnostics',''),
                'gold_checked': n_gold, 'gold_accepted': sum(accepts[:n_gold]),
                'gold_rejected': [labels[i] for i in range(n_gold) if i >= len(accepts) or not accepts[i]],
                'original_F0_order_checked': n_free,
                'original_F0_order_accepted': sum(accepts[n_gold:n_gold+n_free]),
                'original_F0_order_rejected': [labels[i] for i in range(n_gold,n_gold+n_free) if i >= len(accepts) or not accepts[i]],
                'invalid_checked': len(labels) - n_gold - n_free,
                'invalid_accepted': [labels[i] for i in range(n_gold+n_free, len(labels)) if i < len(accepts) and accepts[i]],
                'invalid_accepted_witnesses': [{'key': labels[i], 'text': samples[i]} for i in range(n_gold+n_free, len(labels)) if i < len(accepts) and accepts[i]]}
    try:
        for name, group in grouped.items():
            schema = group[0]['C1_schema']
            tuples(schema, name)
            samples = []; labels = []
            for unit in group:
                gold = envelope.gold_call(unit['task'], unit['tools'][unit['task']['tool_name']])
                samples.append(envelope.dumps_spaced(gold)); labels.append(unit['key'] + '|gold')
            n_gold = len(samples); gold_count += n_gold
            for unit in group:
                if not unit['router']['retry']:
                    samples.append(envelope.dumps_spaced(unit['router']['call']))
                    labels.append(unit['key'] + '|original_F0_order')
            n_free = len(samples) - n_gold
            for unit in group:
                gold = envelope.gold_call(unit['task'], unit['tools'][unit['task']['tool_name']])
                for i, text in enumerate(invalid_calls(gold, unit['tools'])):
                    samples.append(text); labels.append(unit['key'] + '|invalid:' + str(i))
            c1[name] = summarize(native.check(schema, samples), n_gold, n_free, labels, samples)
            c3[name] = summarize(other.check(group[0]['C3_schema'], samples), n_gold, n_free, labels, samples)
        for unit in plan['units']:
            free = unit['F0']; decision = unit['router']
            text = envelope.dumps_spaced(decision['call']) if not decision['retry'] else ''
            gold = envelope.gold_call(unit['task'], unit['tools'][unit['task']['tool_name']])
            branches = unit['C2_schema'].get('anyOf', [unit['C2_schema']])
            branch = next(b for b in branches if b['properties']['tool']['const'] == gold['tool'])
            ordered_gold = envelope.ordered_like_schema(gold, branch)
            negatives = invalid_calls(ordered_gold, unit['tools'])
            checked = native.check(unit['C2_schema'], ([text] if text else []) + negatives)
            negative_offset = int(bool(text))
            c2.append({'unit': unit['key'], 'compile_ok': checked['compile_ok'],
                       'error': checked.get('error'), 'strict_F0': not decision['retry'],
                       'free_correct': free['eval']['e2e_success'],
                       'F0_accepted': checked.get('accepts', [False])[0] if text else None,
                       'invalid_checked': len(negatives),
                       'invalid_accepted': [negatives[i] for i, ok in enumerate(checked.get('accepts', [])[negative_offset:]) if ok],
                       **unit['oracle_flags']})
        # Compatibility with the earlier all-representation 252-case diagnostic is separate
        # from E0b's raw-only 300 units. Never conflate these denominators.
        all_rows = [json.loads(s) for s in gzip.decompress((root / 'analysis/e0-clean-v1/results.jsonl.gz').read_bytes()).splitlines()]
        old_audit = json.loads((root / 'analysis/e0-clean-v1/key-order-audit.json').read_text())
        order_rejected = {d['request_key'] for d in old_audit['details'] if d['kind'] == 'original_order' and not d['accepted']}
        tasks = {t['task_id']: t for t in paths.tasks()}; cats = paths.catalogs()
        compatibility = []
        for row in all_rows:
            if row['decoding'] != 'free' or not row['eval']['e2e_success']: continue
            task = tasks[row['task_id']]; cat = cats[row['catalog_id']] if row['catalog_id'] else None
            tools = tools_for(cat, task)
            decision = route(row['raw_content'], tools, truncated=row['truncated'])
            if decision['retry']: continue
            base = envelope.envelope(list(tools.items()), rc['constraint_policy'])
            reordered, flags = reorder_envelope(base, row['raw_content'], tools)
            result = native.check(apply(reordered, FIXED), [envelope.dumps_spaced(decision['call'])])
            compatibility.append({'source_key': row['request_key'], 'tool_id': row['tool_id'],
                                  'order_rejected_before': row['request_key'] in order_rejected,
                                  'accepted': result['compile_ok'] and result['accepts'][0]})
    finally:
        native.close(); other.close()
    unsupported = {name: value for name, value in c3.items() if not value['compile_ok'] or value['gold_accepted'] != value['gold_checked'] or value['invalid_accepted'] or 'conversion was incomplete' in value['conversion_diagnostics']}
    return {'kind': 'MODEL-FREE: native matcher checks, not inference', 'config_sha256': ordered_hash(rc),
            'plan_sha256': ordered_hash(plan), 'llguidance_build': build, 'gbnf_build': gbnf_build,
            'tuple_array_paths': sorted(set(tuple_paths)), 'C1': c1, 'C2': c2, 'C3': c3,
            'C3_unsupported': unsupported, 'gold_units': gold_count, 'router_replay': replay(plan['units']),
            'all_representation_compatibility': compatibility,
            'lookalike_flags_by_arm': {arm: sum(bool(lookalike_key_flag(r)) for r in all_rows if r['arm'] == arm) for arm in rc_source_arms()},
            'determinism_selection': plan['determinism'],
            'verification_source_sha256': {name: provenance.file_sha(root/name) for name in
                ['sn/e0b.py','sn/e0b_readiness.py','sn/router.py','sn/oracle_order.py','sn/constraint_options.py',
                 'scripts/native_gbnf_audit.cpp','scripts/native_llg_audit.cpp']},
            'online_ok': False, 'launch_clear': False,
            'not_verified': ['model-tokenizer enforcement', '30-request byte-identical determinism', 'live smoke', 'inference accuracy/latency', 'exhaustive schema enforcement']}


def rc_source_arms():
    return ('A_raw_free', 'B_raw_cd', 'A2_min_free', 'B2_min_cd')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--config', default='configs/runs/e0b.json')
    parser.add_argument('--output', default='analysis/e0b-readiness/native.json')
    args = parser.parse_args(); result = audit(config(args.config))
    output = Path(paths.ROOT, args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print('C1', len(result['C1']), 'C2', len(result['C2']), 'C3 unsupported', len(result['C3_unsupported']))


if __name__ == '__main__': main()
