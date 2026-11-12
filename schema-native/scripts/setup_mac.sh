#!/usr/bin/env bash
# One-time setup on an Apple Silicon Mac (16 GB). Idempotent. NOT executed in the authoring environment.
# Needs: Xcode command line tools, cmake, Rust (for llguidance inside llama.cpp), Python 3.11-3.13.
#   brew install cmake rustup && rustup-init -y
set -euo pipefail
SN="$(cd "$(dirname "$0")/.." && pwd)"
EXP="$SN/../experiment"
TOOLS="${TOOLS_DIR:-$HOME/tools}"
[ "$(uname -sm)" = "Darwin arm64" ] || { echo "this script is for Apple Silicon macOS"; exit 1; }

python3 -m venv "$SN/.venv"
source "$SN/.venv/bin/activate"
pip install -q -r "$SN/requirements.txt" -r "$SN/requirements-mac.txt"

# 1. dataset at the commit pinned by the finished experiment
"$EXP/dataset/fetch_jsonschemabench.sh"

# 2. llama.cpp at the commit the finished experiment used, now with Metal and llguidance
COMMIT=$(python3 -c "import json;print(json.load(open('$SN/configs/model.qwen3-1.7b.json'))['llama_cpp_commit'])")
FLAGS=$(python3 -c "import json;print(' '.join(json.load(open('$SN/configs/model.qwen3-1.7b.json'))['llama_cpp_cmake_flags']))")
mkdir -p "$TOOLS"
[ -d "$TOOLS/llama.cpp/.git" ] || git clone https://github.com/ggml-org/llama.cpp.git "$TOOLS/llama.cpp"
git -C "$TOOLS/llama.cpp" fetch -q origin "$COMMIT" || true
git -C "$TOOLS/llama.cpp" checkout -q "$COMMIT"
cmake -S "$TOOLS/llama.cpp" -B "$TOOLS/llama.cpp/build-metal" -DCMAKE_BUILD_TYPE=Release $FLAGS >/dev/null
cmake --build "$TOOLS/llama.cpp/build-metal" -j"$(sysctl -n hw.ncpu)" --target llama-server llama-quantize >/dev/null
pip install -q -r "$TOOLS/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt"

# 3. base model: the same official GGUF file and revision as the finished experiment
python3 - <<PY
import json, hashlib, os
from huggingface_hub import hf_hub_download
m = json.load(open("$SN/configs/model.qwen3-1.7b.json"))
os.makedirs("$SN/models", exist_ok=True)
p = hf_hub_download(m["hf_repo_gguf"], m["gguf_file"], revision=m["hf_revision_gguf"], local_dir="$SN/models")
h = hashlib.sha256(open(p, "rb").read()).hexdigest()
assert h == m["gguf_sha256"], f"sha256 mismatch: {h}"
print("base GGUF ok:", p)
PY

# 4. checks that need no model
python3 -m pytest -q "$SN/tests"
python3 -m sn.preflight_template --model Qwen/Qwen3-1.7B
echo "setup complete"
