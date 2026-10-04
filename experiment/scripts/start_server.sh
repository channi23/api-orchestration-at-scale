#!/usr/bin/env bash
# Start llama-server with the frozen configuration (config/model.json). Logs to runs/server.log.
set -euo pipefail
EXP="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="${TOOLS_DIR:-$HOME/tools}"
MODEL="$EXP/models/$(python3 -c "import json;print(json.load(open('$EXP/config/model.json'))['gguf_file'])")"
ARGS=$(python3 -c "import json;print(' '.join(json.load(open('$EXP/config/model.json'))['server_args']))")
mkdir -p "$EXP/runs"
nohup "$TOOLS/llama.cpp/build/bin/llama-server" -m "$MODEL" $ARGS --host 127.0.0.1 --port 8080 > "$EXP/runs/server.log" 2>&1 &
echo $! > "$EXP/runs/server.pid"
for i in $(seq 1 120); do
  if curl -sf http://127.0.0.1:8080/health >/dev/null; then echo "server up (pid $(cat "$EXP/runs/server.pid"))"; exit 0; fi
  sleep 1
done
echo "server failed to start; see runs/server.log"; exit 1
