#!/usr/bin/env bash
# Dedicated server; never kills an existing process. Log includes Metal startup diagnostics.
set -euo pipefail
SN="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SN"
source .venv/bin/activate
export TOOLS_DIR="${TOOLS_DIR:-$SN/.tools}"
exec python -m sn.server "$@"
