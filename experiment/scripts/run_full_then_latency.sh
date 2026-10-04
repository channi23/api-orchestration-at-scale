#!/usr/bin/env bash
# Full cached run (3,000 requests) then the secondary uncached latency sub-run (50 requests). Resumable.
cd "$(dirname "$0")/.."
python3 src/run.py --config config/runs/full.json --run-id full-v1 >> runs/full-v1.log 2>&1
echo "FULL_EXIT=$?" >> runs/full-v1.log
python3 src/run.py --config config/runs/latency.json --run-id latency-v1 >> runs/latency-v1.log 2>&1
echo "LAT_EXIT=$?" >> runs/latency-v1.log
