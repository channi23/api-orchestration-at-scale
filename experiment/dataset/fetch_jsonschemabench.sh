#!/usr/bin/env bash
# Fetch JSONSchemaBench at the pinned commit used for this experiment.
set -euo pipefail
COMMIT=9a94995b9279ae3af3aed4b2629172790b968d14
DEST="$(cd "$(dirname "$0")" && pwd)/upstream/jsonschemabench"
if [ ! -d "$DEST/.git" ]; then
  git clone https://github.com/guidance-ai/jsonschemabench.git "$DEST"
fi
git -C "$DEST" fetch -q origin "$COMMIT" || true
git -C "$DEST" checkout -q "$COMMIT"
echo "JSONSchemaBench at $(git -C "$DEST" rev-parse HEAD)"
