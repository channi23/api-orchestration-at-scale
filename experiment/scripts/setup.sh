#!/usr/bin/env bash
# One-time environment setup for representation-v1 (idempotent).
# Requires network access to github.com, registry.npmjs.org, pypi.org and huggingface.co.
set -euo pipefail
EXP="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="${TOOLS_DIR:-$HOME/tools}"
LLAMA_COMMIT=$(python3 -c "import json;print(json.load(open('$EXP/config/model.json'))['llama_cpp_commit'])")

pip install -q jsonschema==4.26.0 numpy scipy statsmodels matplotlib pandas huggingface_hub

# 1. dataset at pinned commit
"$EXP/dataset/fetch_jsonschemabench.sh"

# 2. official TSCG, pinned via package-lock.json
(cd "$EXP/representations/tscg" && npm ci --no-audit --no-fund)

# 3. llama.cpp at pinned commit (CPU build)
mkdir -p "$TOOLS"
if [ ! -d "$TOOLS/llama.cpp/.git" ]; then git clone https://github.com/ggml-org/llama.cpp.git "$TOOLS/llama.cpp"; fi
git -C "$TOOLS/llama.cpp" fetch -q origin "$LLAMA_COMMIT" || true
git -C "$TOOLS/llama.cpp" checkout -q "$LLAMA_COMMIT"
cmake -S "$TOOLS/llama.cpp" -B "$TOOLS/llama.cpp/build" -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF >/dev/null
cmake --build "$TOOLS/llama.cpp/build" -j"$(nproc)" --target llama-server >/dev/null

# 4. model weights (official Qwen GGUF), revision pinned in config/model.json after first download
python3 "$EXP/scripts/download_model.py"
echo "setup complete"
