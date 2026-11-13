"""Model-free byte-tokenizer reachability of the actual E0 envelopes.

This uses the standalone Python llguidance package, not llama.cpp or Qwen tokens.
"""
import argparse
import json
from pathlib import Path
from . import envelope, paths, preflight
from .engine_audit import LLGuidance, time_limit
import schema_utils as su


def audit(rc):
    requests, schemas = preflight.plan(rc)
    engine = LLGuidance()
    compiled, refused, unreachable = {}, {}, []
    for name, schema in schemas.items():
        try:
            with time_limit(20):
                compiled[name] = engine.compile(schema)[0]
        except Exception as e:
            refused[name] = str(e)
    checked, seen = 0, set()
    for family, arm, cat, task in requests:
        if rc['arm_defs'][arm]['decoding'] != 'constrained':
            continue
        name = cat['catalog_id'] if cat else 'single:' + task['tool_id']
        pair = (name, task['task_id'])
        if name not in compiled or pair in seen:
            continue
        seen.add(pair)
        raw = su.load_schema(paths.pool()[task['tool_id']]['schema_id'])
        call = envelope.gold_call(task, raw)
        with time_limit(20):
            ok = (engine.accepts(compiled[name], envelope.dumps_compact(call)) or
                  engine.accepts(compiled[name], envelope.dumps_spaced(call)))
        if not ok:
            unreachable.append(pair)
        checked += 1
    return {'kind': 'model-free byte-tokenizer audit; not inference', 'engine_version': engine.version,
            'envelopes': len(schemas), 'compiled': len(compiled), 'refused': refused,
            'checked_gold_pairs': checked, 'unreachable': unreachable}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/runs/e0_decoding.json')
    ap.add_argument('--output', default='runs/e0-envelope-byte-audit.json')
    args = ap.parse_args()
    result = audit(json.loads(Path(args.config).read_text()))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
