#!/usr/bin/env bash
# Rebuild every analysis output from the validated run artifacts (no model calls).
set -euo pipefail
cd "$(dirname "$0")/.."
A=analysis/full-v2
python3 src/analyze.py --run runs/full-v2 --latency-run runs/latency-v2 --out $A
python3 src/render_text.py $A $A/REPORT.template.md $A/REPORT.md
python3 src/render_text.py $A $A/SUMMARY_STE.template.md $A/SUMMARY_STE.md
python3 src/make_diagram.py $A
python3 src/make_explainer.py --analysis $A --run runs/full-v2 --latency-run runs/latency-v2
