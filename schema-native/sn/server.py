"""Run one dedicated server in the foreground; preserve startup and peak-memory evidence."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import socket
import time
from . import paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('model', nargs='?')
    ap.add_argument('port', nargs='?', default='8080')
    ap.add_argument('--config', default='configs/model.qwen3-1.7b.json')
    ap.add_argument('--campaign-config', help='E0b: enforce admission and post-load settling before any inference')
    args = ap.parse_args()
    cfg = json.loads(Path(paths.ROOT, args.config).read_text())
    model = args.model or str(Path(paths.ROOT, 'models', cfg['gguf_file']))
    port = args.port
    if not Path(model).is_file():
        raise SystemExit('Model missing: run scripts/setup_mac.sh first')
    tools = Path(os.environ.get('TOOLS_DIR', str(Path(paths.ROOT, '.tools'))))
    binary = tools / 'llama.cpp/build-metal/bin/llama-server'
    Path(paths.RUNS).mkdir(exist_ok=True)
    log = Path(paths.RUNS, f'server.{port}.log')
    campaign = None
    if args.campaign_config:
        from . import e0b_resources as lifecycle, e0b, resources
        campaign = e0b.config(args.campaign_config)
        plan = e0b.prepare(campaign)
        if Path(model).resolve() != Path(paths.ROOT,'models',plan['model']['gguf_file']).resolve():
            raise ValueError('Campaign model path changed')
        if cfg != plan['model']:
            raise ValueError('Campaign model profile changed')
        directory = Path(paths.RUNS, campaign['run_id']); directory.mkdir(exist_ok=True)
        if (directory/'STOPPED.json').exists() and not json.loads((directory/'STOPPED.json').read_text()).get('resumable'):
            raise ValueError('Campaign has a final stop; cannot load for resume')
        manifest = directory/'manifest.json'; identity = e0b.identity_for(plan)
        if manifest.exists() and json.loads(manifest.read_text()) != identity:
            raise ValueError('Campaign identity changed')
        manifest.write_text(json.dumps(identity,indent=2)+'\n')
        e0b.campaign_budget(directory,campaign)
        try:
            try:
                with socket.create_connection(('127.0.0.1',int(port)),timeout=1):
                    raise RuntimeError('Server port already in use; refusing to launch another model')
            except OSError: pass
            lifecycle.admission(directory)
            baseline = Path(paths.ROOT,campaign['system_swapout_baseline_file'])
            if not baseline.exists(): resources.initialize_swap_baseline(campaign)
            # Existing baseline is NEVER reset on resume, including the cumulative 1 GiB cap.
            page, swaps = resources.swap_snapshot()
            resources.check_swap_growth(campaign,page*swaps)
        except Exception as exc:
            lifecycle.stop(directory,exc,'server_resource'); raise
    with log.open('a') as stream:
        print('Server log:', log, flush=True)
        # time -l reports maximum resident set size when this foreground server exits.
        proc = subprocess.Popen(['/usr/bin/time', '-l', str(binary), '-m', str(Path(model).resolve()),
                                 *cfg['server_args'], '--host', '127.0.0.1', '--port', port], stdout=stream, stderr=stream, start_new_session=bool(campaign))
        try:
            if campaign:
                session = dict(pid=proc.pid, binary=str(binary.resolve()), model=str(Path(model).resolve()),
                               run_id=campaign['run_id'], config=campaign, settled=False)
                session_path=directory/'server-session.json'
                session_path.write_text(json.dumps(session,indent=2)+'\n')
                # TCP readiness only; no generation or metadata HTTP before settling.
                def load_pressure():
                    page,swaps=resources.swap_snapshot()
                    resources.check_swap_growth(campaign,page*swaps)
                    return resources.pressure_level()
                deadline=time.monotonic()+180
                while True:
                    load_pressure()
                    if proc.poll() is not None: raise RuntimeError('Dedicated server exited during load')
                    try:
                        with socket.create_connection(('127.0.0.1',int(port)),timeout=1): break
                    except OSError:
                        if time.monotonic()>=deadline: raise RuntimeError('Dedicated server did not become ready')
                        time.sleep(1)
                lifecycle.settle(directory,pressure=load_pressure)
                session['settled']=True
                session_path.write_text(json.dumps(session,indent=2)+'\n')
            rc = proc.wait()
        except KeyboardInterrupt:
            if campaign: lifecycle.unload(directory)
            rc = proc.wait()
        except Exception as exc:
            if campaign:
                lifecycle.stop(directory,exc,'server_resource')
                proc.wait(timeout=30)
            raise
    raise SystemExit(rc)


if __name__ == '__main__':
    main()
