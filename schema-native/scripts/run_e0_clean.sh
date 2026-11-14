#!/usr/bin/env bash
# First start: scripts/serve.sh --config configs/model.qwen3-1.7b.sustainable.json
set -euo pipefail
SN="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SN"
source .venv/bin/activate
RUN_ID="${1:-e0-clean-v1}"
python -m sn.preflight --config configs/runs/e0_clean_smoke.json --output "runs/${RUN_ID}-smoke-preflight.json"
python -m sn.run --config configs/runs/e0_clean_smoke.json --preflight "runs/${RUN_ID}-smoke-preflight.json" --run-id "${RUN_ID}-smoke"
python -m sn.report --run "${RUN_ID}-smoke"
python -m sn.preflight --config configs/runs/e0_clean.json --output "runs/${RUN_ID}-preflight.json"
python -m sn.run --config configs/runs/e0_clean.json --preflight "runs/${RUN_ID}-preflight.json" --run-id "$RUN_ID"
python -m sn.report --run "$RUN_ID"
