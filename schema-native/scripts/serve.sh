#!/usr/bin/env bash
# Start llama-server (Metal) for one model.  usage: scripts/serve.sh [path/to/model.gguf] [port]
# Default model is the base Qwen3-1.7B Q8_0. Logs to runs/server.log.
set -euo pipefail
SN="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="${TOOLS_DIR:-$HOME/tools}"
CFG="$SN/configs/model.qwen3-1.7b.json"
MODEL="${1:-$SN/models/$(python3 -c "import json;print(json.load(open('$CFG'))['gguf_file'])")}"
PORT="${2:-8080}"
ARGS=$(python3 -c "import json;print(' '.join(json.load(open('$CFG'))['server_args']))")
mkdir -p "$SN/runs"
if [ -f "$SN/runs/server.$PORT.pid" ]; then kill "$(cat "$SN/runs/server.$PORT.pid")" 2>/dev/null || true; sleep 1; fi
nohup "$TOOLS/llama.cpp/build-metal/bin/llama-server" -m "$MODEL" $ARGS --host 127.0.0.1 --port "$PORT" > "$SN/runs/server.$PORT.log" 2>&1 &
echo $! > "$SN/runs/server.$PORT.pid"
for i in $(seq 1 120); do
  if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null; then echo "server up on :$PORT with $MODEL"; exit 0; fi
  sleep 1
done
echo "server failed to start; see runs/server.$PORT.log"; exit 1
