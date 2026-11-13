#!/usr/bin/env bash
# Train one LoRA adapter with MLX-LM.  usage: scripts/train_lora.sh <raw|minified>
# Writes adapters/lora-<representation>/ and a training log with wall time and peak memory.
# NOT executed in the authoring environment.
set -euo pipefail
SN="$(cd "$(dirname "$0")/.." && pwd)"
REP="${1:?give raw or minified}"
source "$SN/.venv/bin/activate"
cd "$SN"
echo "E1 is deferred: requires a reviewed real E0 readout and unseen-schema datasets." >&2
exit 1
python3 -m sn.preflight_template --model Qwen/Qwen3-1.7B
mkdir -p adapters logs
# /usr/bin/time -l prints "maximum resident set size" (bytes) on macOS: that is the peak-memory measurement to report.
/usr/bin/time -l mlx_lm.lora --config configs/lora.qwen3-1.7b.yaml \
  --data "data/mlx/$REP" --adapter-path "adapters/lora-$REP" 2>&1 | tee "logs/train-$REP.log"
