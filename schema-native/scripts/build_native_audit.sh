#!/usr/bin/env bash
set -euo pipefail
SN="$(cd "$(dirname "$0")/.." && pwd)"
LLAMA="${TOOLS_DIR:-$SN/.tools}/llama.cpp"
ENGINE="$LLAMA/build-metal/llguidance/source/target/release"
mkdir -p "$SN/.tools"
LIBRARY_SHA_BEFORE="$(shasum -a 256 "$ENGINE/libllguidance.a" | awk '{print $1}')"
clang++ -std=c++17 -O2 -I"$ENGINE" -I"$LLAMA/vendor" "$SN/scripts/native_llg_audit.cpp" "$ENGINE/libllguidance.a" -framework Security -framework CoreFoundation -framework SystemConfiguration -liconv -o "$SN/.tools/native-llg-audit"
python3 - "$ENGINE/libllguidance.a" "$SN/.tools/native-llg-audit" "$LIBRARY_SHA_BEFORE" <<'PY'
import hashlib, json, sys
from pathlib import Path
library, helper = map(Path, sys.argv[1:3])
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
if sha(library) != sys.argv[3]:
    raise SystemExit('Library changed while linking; rebuild the helper')
helper.with_suffix('.build.json').write_text(json.dumps({
    'library_sha256': sys.argv[3], 'helper_sha256': sha(helper)}, indent=2) + '\n')
PY
