#!/usr/bin/env bash
# Run after setup_mac.sh and serve.sh. Measured only if real preflight succeeds.
set -euo pipefail
SN="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SN"
source .venv/bin/activate
RUN_ID="${1:-e0-v1}"
python -m sn.preflight --config configs/runs/e0_smoke.json --output runs/e0-smoke-preflight.json
python -m sn.run --config configs/runs/e0_smoke.json --preflight runs/e0-smoke-preflight.json --run-id "${RUN_ID}-smoke"
python -m sn.report --run "${RUN_ID}-smoke"
python -m sn.preflight --config configs/runs/e0_decoding.json --output runs/e0-preflight.json
python -m sn.run --config configs/runs/e0_decoding.json --preflight runs/e0-preflight.json --run-id "$RUN_ID"
python -m sn.report --run "$RUN_ID"
