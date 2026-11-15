"""Append-only offline prefix resolutions; never sends or re-scores a model request."""
import hashlib
import json
import os
from pathlib import Path
from .native_prefix import verify_prefix, PrefixCheckUnavailable
from . import e0b_resources as lifecycle


def fingerprint(row):
    return hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def effective_rows(directory,filename,key_field):
    """Overlay proof-only corrections without rewriting any durable response bytes."""
    path=Path(directory)/filename
    rows=[json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    originals={r[key_field]:r for r in rows}
    if len(originals)!=len(rows):raise ValueError('Duplicate durable response keys')
    log=Path(directory)/'prefix-resolutions.jsonl';patches={}
    for line in log.read_text().splitlines() if log.exists() else []:
        item=json.loads(line)
        if item['stream']!=filename:continue
        key=item['key'];original=originals.get(key)
        if key in patches or original is None or original.get('prefix_check')!='pending' or fingerprint(original)!=item['source_sha256']:
            raise ValueError('Prefix resolution does not match its original pending response')
        if type(item['proof'].get('legal_prefix')) is not bool:raise ValueError('Malformed saved prefix proof')
        patches[key]=item['proof']
    result=[]
    for original in rows:
        row=dict(original);proof=patches.get(row[key_field])
        if proof is not None:
            legal=proof['legal_prefix']
            row.update(prefix_check='verified' if legal else 'illegal',native_prefix=proof,prefix_check_error=None)
            if filename=='readiness-results.jsonl':
                row['smoke_gate']={'passed':legal,'outcome':'cd_truncated' if legal else 'illegal_prefix',
                                   'native_prefix':proof}
            else:
                row.update(engine_error=not legal,request_error=None if legal else 'engine_or_request_fault',
                           constraint_violation=None if legal else 'Truncated output is not a legal grammar prefix',
                           failure_class='cd_truncated' if legal else 'engine_refusal')
                row['diagnostic_flags']=dict(row['diagnostic_flags'],engine_refusal=not legal)
        result.append(row)
    return result


def resolve_pending(directory,*,prefix_checker=None):
    """Must run offline, under the campaign writer lock, before server startup/resume."""
    directory=Path(directory);resolved=0
    for filename,key_field in [('readiness-results.jsonl','key'),('results.jsonl','request_key')]:
        for row in effective_rows(directory,filename,key_field):
            if row.get('prefix_check')=='illegal':raise RuntimeError('Confirmed illegal prefix: '+row[key_field])
            if row.get('prefix_check')!='pending':continue
            request=row['prefix_request']
            if filename=='readiness-results.jsonl':
                choice=row['response']['choices'][0]
                if row['status']!=200 or row['engine_log_errors'] or choice['finish_reason']!='length':
                    raise RuntimeError('Pending readiness row has an engine/request fault')
                text=choice['message']['content']
            else:
                if row['http_status']!=200 or row['engine_log_errors'] or not row['truncated']:
                    raise RuntimeError('Pending benchmark row has an engine/request fault')
                text=row['raw_content']
            proof=verify_prefix(request['schema'],text,grammar=request['grammar'],prefix_checker=prefix_checker)
            # The original response stays immutable. Only the native verdict is appended.
            record=dict(stream=filename,key=row[key_field],source_sha256=fingerprint(row),proof=proof)
            with (directory/'prefix-resolutions.jsonl').open('a') as stream:
                stream.write(json.dumps(record)+'\n');stream.flush();os.fsync(stream.fileno())
            resolved+=1
            lifecycle.event(directory,'prefix_check_resolved',stream=filename,key=row[key_field],legal_prefix=proof['legal_prefix'])
            if not proof['legal_prefix']:raise RuntimeError('Confirmed illegal prefix: '+row[key_field])
    return resolved
