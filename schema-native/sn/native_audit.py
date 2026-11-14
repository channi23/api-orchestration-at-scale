"""Audit E0 with the exact C library linked into the pinned server, using a byte tokenizer.

Build with scripts/build_native_audit.sh first. No model or GPU is used. Model-tokenizer probes
remain mandatory before measured inference.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from . import paths, preflight, envelope, provenance
import schema_utils as su


def verified_build(binary, library):
    metadata = json.loads(Path(binary).with_suffix('.build.json').read_text())
    if (metadata['library_sha256'] != provenance.file_sha(library)
            or metadata['helper_sha256'] != provenance.file_sha(binary)):
        raise ValueError('Native audit build mismatch; rebuild the helper before auditing')
    return metadata


def audit(config, binary=None):
    requests, schemas=preflight.plan(config)
    cases={name:{} for name in schemas}
    pool=paths.pool()
    for family,arm,cat,task in requests:
        name=cat['catalog_id'] if cat else 'single:'+task['tool_id']
        raw=su.load_schema(pool[task['tool_id']]['schema_id'])
        cases[name][task['task_id']]=envelope.gold_call(task,raw)
    binary=binary or str(Path(paths.ROOT,'.tools/native-llg-audit'))
    root=Path(os.environ.get('TOOLS_DIR',str(Path(paths.ROOT,'.tools'))),'llama.cpp/build-metal/llguidance/source')
    build=verified_build(binary,root/'target/release/libllguidance.a')
    proc=subprocess.Popen([binary],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    refused={};unreachable=[];checked=0
    try:
        for name,schema in schemas.items():
            ids=list(cases[name]);samples=[]
            for task_id in ids:
                call=cases[name][task_id]
                samples += [envelope.dumps_compact(call),envelope.dumps_spaced(call)]
            proc.stdin.write(json.dumps({'schema':schema,'samples':samples})+'\n');proc.stdin.flush()
            line=proc.stdout.readline()
            if not line: raise RuntimeError('Native audit process exited before returning evidence')
            result=json.loads(line)
            if not result['compile_ok']:
                refused[name]=result.get('error','unknown error').splitlines()[0];continue
            for i,task_id in enumerate(ids):
                if not any(result['accepts'][2*i:2*i+2]):unreachable.append([name,task_id])
                checked+=1
    finally:
        proc.stdin.close();proc.wait()
    return {'kind':'exact bundled C engine, byte tokenizer; not model inference',
            'engine_commit':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),
            'library_sha256':build['library_sha256'],
            'helper_sha256':provenance.file_sha(binary),
            'constraint_policy':config.get('constraint_policy','original-v0'),
            'envelopes':len(schemas),'compiled':len(schemas)-len(refused),'refused':refused,
            'gold_pairs_checked':checked,'unreachable':unreachable}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/runs/e0_clean.json')
    parser.add_argument('--output',default='runs/e0-native-audit.json')
    args=parser.parse_args();result=audit(json.loads(Path(args.config).read_text()))
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
