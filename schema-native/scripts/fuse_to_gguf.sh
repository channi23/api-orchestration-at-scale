#!/usr/bin/env bash
# Fuse a trained adapter into the base weights and convert to the same GGUF quantization as the base.
# usage: scripts/fuse_to_gguf.sh <raw|minified>   ->  models/qwen3-1.7b-lora-<rep>-Q8_0.gguf
# mlx_lm.fuse --export-gguf only supports llama/mistral/mixtral model types (checked in mlx-lm 0.32.2),
# so Qwen3 goes through llama.cpp's converter. NOT executed in the authoring environment.
set -euo pipefail
SN="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="${TOOLS_DIR:-$HOME/tools}"
REP="${1:?give raw or minified}"
source "$SN/.venv/bin/activate"
cd "$SN"
FUSED="models/fused-lora-$REP"
mlx_lm.fuse --model Qwen/Qwen3-1.7B --adapter-path "adapters/lora-$REP" --save-path "$FUSED" --dequantize
python3 "$TOOLS/llama.cpp/convert_hf_to_gguf.py" "$FUSED" --outtype f16 --outfile "models/qwen3-1.7b-lora-$REP-f16.gguf"
"$TOOLS/llama.cpp/build-metal/bin/llama-quantize" "models/qwen3-1.7b-lora-$REP-f16.gguf" "models/qwen3-1.7b-lora-$REP-Q8_0.gguf" Q8_0
rm -f "models/qwen3-1.7b-lora-$REP-f16.gguf"
shasum -a 256 "models/qwen3-1.7b-lora-$REP-Q8_0.gguf" | tee "models/qwen3-1.7b-lora-$REP-Q8_0.sha256"
