"""Amendment 3 resource-only lifecycle. No model or outcome access at import time."""
import datetime
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from . import resources


class ResourceStop(RuntimeError):
    """A resource timeout/admission failure; safe to resume only after fresh admission."""


def event(directory, kind, **fields):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    with (directory/'resource-events.jsonl').open('a') as stream:
        stream.write(json.dumps(dict(fields, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), event=kind))+'\n')
        stream.flush(); os.fsync(stream.fileno())


def memory_inventory():
    raw = subprocess.check_output(['vm_stat'], text=True)
    size = int(re.search(r'page size of (\d+) bytes', raw)[1])
    components = {name: int(re.search(r'^Pages '+name+r':\s+(\d+)', raw, re.M)[1])*size
                  for name in ('free', 'inactive', 'purgeable')}
    rows = subprocess.check_output(['ps', '-axo', 'rss=,comm='], text=True)
    processes = []
    for row in rows.splitlines():
        resident, command = row.strip().split(None, 1)
        processes.append({'name': Path(command).name, 'resident_bytes': int(resident)*1024})
    return dict(components, available_bytes=sum(components.values()),
                available_definition='free + inactive + purgeable; accounting estimate, purgeable may overlap other page categories',
                largest_processes=sorted(processes,key=lambda p:p['resident_bytes'],reverse=True)[:10])


def admission(directory, *, inventory=None, pressure=None):
    report = (inventory or memory_inventory)()
    report['memory_pressure_dispatch_level'] = (pressure or resources.pressure_level)()
    event(directory, 'admission', **report)
    print(json.dumps(report, indent=2), flush=True)
    if report['memory_pressure_dispatch_level'] != 1 or report['available_bytes'] < 5*1024**3:
        raise ResourceStop('Pre-load admission needs normal pressure and at least 5 GiB free + inactive + purgeable')
    return report


def settle(directory, *, pressure=None, clock=None, sleep=None):
    pressure = pressure or resources.pressure_level; clock = clock or time.monotonic; sleep = sleep or time.sleep
    start = clock(); clean = 0
    while True:
        level = pressure(); clean = clean+1 if level == 1 else 0
        event(directory, 'settle_sample', memory_pressure_dispatch_level=level, consecutive_normal=clean)
        if clean == 3:
            event(directory, 'settled'); return
        if clock()-start >= 90:
            raise ResourceStop('Post-load settle window expired without three consecutive normal readings')
        sleep(min(5, 90-(clock()-start)))


def guard(config, state, directory, *, clock=None, sleep=None, sampler=None):
    """No new HTTP generation is issued while paused. Never inspects an output."""
    clock = clock or time.monotonic; sleep = sleep or time.sleep; sampler = sampler or resources.check
    start = clock(); paused = False; clean = 0
    while True:
        try:
            health = sampler(config, state)
        except resources.ResourceWarning as exc:
            clean = 0
            if not paused:
                paused = True; event(directory, 'pause', reason=str(exc))
            event(directory, 'pause_check', clean=False, reason=str(exc))
        else:
            if not paused: return health
            clean += 1; event(directory, 'pause_check', clean=True, consecutive_clean=clean, resource_check=health)
            if clean == 3:
                event(directory, 'continue', pause_seconds=clock()-start); return health
        if clock()-start >= 900:
            raise ResourceStop('Resource pause exceeded 15 minutes')
        sleep(min(30,900-(clock()-start)))


def unload(directory):
    """Signal only the process group registered by our dedicated campaign server."""
    path = Path(directory)/'server-session.json'
    if not path.exists():
        event(directory, 'unload_unavailable', reason='No owned server registration; no other process touched')
        return
    session = json.loads(path.read_text()); pid = session['pid']
    command = subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout
    if not command.strip(): return
    if session['binary'] not in command or session['model'] not in command or os.getpgid(pid) != pid:
        raise RuntimeError('Owned server identity changed; refusing to signal another process')
    try:
        os.killpg(pid,signal.SIGTERM)
    except ProcessLookupError:
        return
    event(directory, 'unload', pid=pid)
    deadline=time.monotonic()+30
    while True:
        snapshot=subprocess.run(['ps','-axo','pgid=,stat='],capture_output=True,text=True,check=True).stdout
        live_group=[row for row in snapshot.splitlines() if len(row.split())==2
                    and row.split()[0]==str(pid) and not row.split()[1].startswith('Z')]
        if not live_group:
            event(directory,'unloaded');return
        if time.monotonic()>=deadline:
            raise RuntimeError('Dedicated server did not exit after graceful unload; inspect before continuing')
        time.sleep(1)


def stop(directory, exc, phase):
    resumable = isinstance(exc, ResourceStop)
    record = dict(phase=phase, reason=str(exc), resumable=resumable,
                  utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    path=Path(directory)/'STOPPED.json'
    if path.exists() and json.loads(path.read_text()).get('resumable') and not resumable:
        archive=Path(directory)/'resource-stops';archive.mkdir(exist_ok=True)
        path.rename(archive/(str(time.time_ns())+'.json'))
    if not path.exists():
        with path.open('x') as stream:
            stream.write(json.dumps(record,indent=2)+'\n'); stream.flush(); os.fsync(stream.fileno())
    event(directory, 'stop', **record)
    unload(directory)


def resume(directory):
    """Call under writer lock, only after fresh admission/settling and identity checks."""
    path=Path(directory)/'STOPPED.json'
    if not path.exists(): return
    record=json.loads(path.read_text())
    if not record.get('resumable') or record.get('phase') not in ('resource_guard','server_resource','online_preflight_smoke'):
        raise ValueError('Campaign stopped for a final fault; not resumable')
    archive=Path(directory)/'resource-stops'; archive.mkdir(exist_ok=True)
    destination=archive/(str(time.time_ns())+'.json')
    path.rename(destination)
    event(directory,'resume', stopped_record=str(destination.name))


def completed(directory, filename, key_field):
    path=Path(directory)/filename
    rows=[json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    result={row[key_field]:row for row in rows}
    if len(result)!=len(rows): raise ValueError('Duplicate completed request keys')
    return result


def require_session(directory, config):
    session=json.loads((Path(directory)/'server-session.json').read_text())
    if not session.get('settled') or session['run_id'] != config['run_id']:
        raise ValueError('Fresh admitted, settled campaign server required')
    if session.get('config') != config:
        raise ValueError('Campaign server configuration changed')
    # A PID must still be alive; the runner separately verifies binary/model/props.
    os.kill(session['pid'],0)
    return session


def main():
    import argparse
    from . import e0b,paths
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/runs/e0b.json')
    parser.add_argument('--unload',action='store_true',required=True)
    args=parser.parse_args()
    config=e0b.config(args.config)
    unload(Path(paths.RUNS)/config['run_id'])


if __name__=='__main__':main()
