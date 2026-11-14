#!/usr/bin/env bash
set -euo pipefail
SN="$(cd "$(dirname "$0")/.." && pwd)"
LLAMA="${TOOLS_DIR:-$SN/.tools}/llama.cpp"
mkdir -p "$SN/.tools"
clang++ -std=c++17 -O2 -I"$LLAMA/common" -I"$LLAMA/src" -I"$LLAMA/include" -I"$LLAMA/ggml/include" -I"$LLAMA/vendor" "$SN/scripts/native_gbnf_audit.cpp" -L"$LLAMA/build-metal/bin" -lllama-common -lllama -Wl,-rpath,"$LLAMA/build-metal/bin" -o "$SN/.tools/native-gbnf-audit"
python3 - "$LLAMA/build-metal/bin" "$SN/.tools/native-gbnf-audit" <<'PY'
import hashlib, json, sys
from pathlib import Path
root, helper = map(Path, sys.argv[1:])
files = [root/'libllama-common.dylib', root/'libllama.dylib', helper]
helper.with_suffix('.build.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, indent=2)+'\n')
PY
