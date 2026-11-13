#!/usr/bin/env bash
# E0 only: Python, frozen dataset, Metal + llguidance server and pinned Q8_0 weights.
set -euo pipefail
SN="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="${TOOLS_DIR:-$SN/.tools}"
[ "$(uname -sm)" = "Darwin arm64" ] || { echo 'Requires Apple Silicon macOS'; exit 1; }
PYTHON="${SN_PYTHON:-python3.13}"
for tool in "$PYTHON" git cmake cargo; do command -v "$tool" >/dev/null || { echo "Install missing prerequisite: $tool"; exit 1; }; done
cd "$SN"
[ -d .venv ] || "$PYTHON" -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-e0.txt
../experiment/dataset/fetch_jsonschemabench.sh
mkdir -p "$TOOLS"
[ -d "$TOOLS/llama.cpp/.git" ] || git clone https://github.com/ggml-org/llama.cpp.git "$TOOLS/llama.cpp"
[ -z "$(git -C "$TOOLS/llama.cpp" status --porcelain --untracked-files=no)" ] || { echo 'llama.cpp has tracked edits; preserve them and use another TOOLS_DIR'; exit 1; }
COMMIT=$(python -c 'import json; print(json.load(open("configs/model.qwen3-1.7b.json"))["llama_cpp_commit"])')
git -C "$TOOLS/llama.cpp" fetch origin "$COMMIT"
git -C "$TOOLS/llama.cpp" checkout --detach "$COMMIT"
cmake -S "$TOOLS/llama.cpp" -B "$TOOLS/llama.cpp/build-metal" -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=ON -DLLAMA_LLGUIDANCE=ON -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF
cmake --build "$TOOLS/llama.cpp/build-metal" -j4 --target llama-server llama-quantize
python - <<'PY'
import json
from huggingface_hub import hf_hub_download
from sn.provenance import file_sha
m = json.load(open('configs/model.qwen3-1.7b.json'))
p = hf_hub_download(m['hf_repo_gguf'], m['gguf_file'], revision=m['hf_revision_gguf'], local_dir='models')
if file_sha(p) != m['gguf_sha256']:
    raise SystemExit('Pinned GGUF checksum mismatch')
print('Verified GGUF:', p)
PY
python -m pytest -q
python -m sn.preflight --offline --output runs/e0-offline.json
printf '%s\n' 'Setup complete. Start scripts/serve.sh in a second terminal, then scripts/run_e0.sh e0-v1.'
