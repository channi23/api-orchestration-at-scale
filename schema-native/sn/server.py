"""Run one dedicated server in the foreground; preserve startup and peak-memory evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
from . import paths


def main():
    cfg = json.loads(Path(paths.ROOT, 'configs/model.qwen3-1.7b.json').read_text())
    model = sys.argv[1] if len(sys.argv) > 1 else str(Path(paths.ROOT, 'models', cfg['gguf_file']))
    port = sys.argv[2] if len(sys.argv) > 2 else '8080'
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
            proc.terminate()
            rc = proc.wait()
    raise SystemExit(rc)


if __name__ == '__main__':
    main()
