"""Run one dedicated server in the foreground; preserve startup and peak-memory evidence."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from . import paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('model', nargs='?')
    ap.add_argument('port', nargs='?', default='8080')
    ap.add_argument('--config', default='configs/model.qwen3-1.7b.json')
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
    with log.open('a') as stream:
        print('Server log:', log, flush=True)
        # time -l reports maximum resident set size when this foreground server exits.
        proc = subprocess.Popen(['/usr/bin/time', '-l', str(binary), '-m', str(Path(model).resolve()),
                                 *cfg['server_args'], '--host', '127.0.0.1', '--port', port], stdout=stream, stderr=stream)
        try:
            rc = proc.wait()
        except KeyboardInterrupt:
            # The foreground child already received SIGINT; avoid a second termination signal.
            rc = proc.wait()
    raise SystemExit(rc)


if __name__ == '__main__':
    main()
