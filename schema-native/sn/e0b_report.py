"""E0b readout: all units, two co-primary Holm tests, separate secondary family."""
import argparse
import json
from pathlib import Path
from . import paths
from .e0b import config, prepare, identity_for
import analyze as statistics


def comparisons(rows, rc):
    results = []
    for name, a, b in rc['comparisons']:
        ra = [r for r in rows if r['arm'] == a and r['family'] == 'select']
        rb = [r for r in rows if r['arm'] == b and r['family'] == 'select']
        result = statistics.paired(ra, rb, lambda r: r['eval']['e2e_success'])
        results.append(dict(name=name, a=a, b=b, family='select', size='pooled',
                            multiplicity_family='co_primary' if name in rc['analysis']['co_primary_holm'] else 'secondary',
                            **result))
    for family in ('co_primary', 'secondary'):
        group = [r for r in results if r['multiplicity_family'] == family]
        for row, adjusted in zip(group, statistics.holm([r['mcnemar_exact_p'] for r in group])):
            row['p_holm'] = adjusted
    p1 = results[0]
    return {'comparisons': results,
            'order_effect_rule_met': p1['diff_pp'] >= 8 and p1['ci95_diff_pp'][0] > 0,
            'independent_intents_approx': 50,
            'note': 'Intervals are replicate-bootstrap intervals; only approximately 50 independent intents. Primary outcomes include all units.'}


def report(run_id, rc):
    directory = Path(paths.RUNS, run_id)
    plan = prepare(rc)
    if json.loads((directory/'manifest.json').read_text()) != identity_for(plan):
        raise ValueError('Report config/source identity differs from campaign')
    expected = {arm+'|'+u['key'] for u in plan['units'] for arm in rc['arms']}
    saved = paths.jsonl(directory/'results.jsonl')
    rows = [r for r in saved if r['request_key'] in expected]
    keys = [r['request_key'] for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate final result keys')
    missing = sorted(expected-set(keys))
    result = {'run':run_id, 'complete':not missing, 'missing_n':len(missing),
              'n':len(rows), 'note':'Reused baseline/free-attempt timings are labeled; V sums both attempts. No independent-inference claim from stored-row replays.'}
    if not missing:
        result.update(comparisons(rows, rc))
    out = Path(paths.ANALYSIS,run_id);out.mkdir(exist_ok=True)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True)
    args=parser.parse_args();print(json.dumps(report(args.run,config()),indent=2))


if __name__=='__main__':main()
