"""Locate the frozen representation experiment and import its modules read-only.

Nothing in this package writes inside ``experiment/``. New run artifacts go to
``schema-native/runs`` and new analysis to ``schema-native/analysis``.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # schema-native/
REPO = os.path.dirname(ROOT)
EXP = os.environ.get("SN_EXPERIMENT_DIR", os.path.join(REPO, "experiment"))
EXP_SRC = os.path.join(EXP, "src")
RUNS = os.path.join(ROOT, "runs")
ANALYSIS = os.path.join(ROOT, "analysis")
DATA = os.path.join(ROOT, "data")

if EXP_SRC not in sys.path:
    sys.path.insert(0, EXP_SRC)


def jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def tasks() -> list[dict]:
    return jsonl(os.path.join(EXP, "tasks", "tasks.v1.jsonl"))


def pool() -> dict[str, dict]:
    return {t["tool_id"]: t for t in jsonl(os.path.join(EXP, "dataset", "tool_pool.v1.jsonl"))}


def catalogs() -> dict[str, dict]:
    with open(os.path.join(EXP, "catalogs", "catalogs.v1.json")) as f:
        return {c["catalog_id"]: c for c in json.load(f)["catalogs"]}
