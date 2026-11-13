#!/usr/bin/env bash
set -euo pipefail
SN="$(cd "$(dirname "$0")/.." && pwd)"
LLAMA="${TOOLS_DIR:-$SN/.tools}/llama.cpp"
ENGINE="$LLAMA/build-metal/llguidance/source/target/release"
clang++ -std=c++17 -O2 -I"$ENGINE" -I"$LLAMA/vendor" "$SN/scripts/native_llg_audit.cpp" "$ENGINE/libllguidance.a" -framework Security -framework CoreFoundation -framework SystemConfiguration -liconv -o "$SN/.tools/native-llg-audit"
