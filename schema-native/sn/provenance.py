"""Content identity for frozen inputs and safe append-only run resumption."""
from __future__ import annotations
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
from . import paths
import schema_utils as su


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inputs():
    files = [os.path.join(paths.EXP, p) for p in (
        "tasks/tasks.v1.jsonl", "catalogs/catalogs.v1.json", "dataset/tool_pool.v1.jsonl")]
    files += [os.path.join(paths.EXP_SRC, p) for p in ("prompts.py", "render.py", "evaluate.py", "schema_utils.py")]
    files += [os.path.join(paths.HERE, p) for p in ("run.py", "envelope.py", "provenance.py", "preflight.py")]
    out = {os.path.relpath(p, paths.REPO): file_sha(p) for p in files}
    for tool in paths.pool().values():
        sid = tool["schema_id"]
        out["schema:" + sid] = digest(su.load_schema(sid))
    return out


def identity(rc, model):
    return {"run_config": rc, "model_config": model, "inputs_sha256": digest(inputs())}


def environment():
    names = ("jsonschema", "numpy", "scipy", "pytest", "llguidance", "xgrammar", "outlines_core")
    versions = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {"python": platform.python_version(), "platform": platform.platform(), "packages": versions}


def validate_rows(rows, expected):
    keys = [r["request_key"] for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate request keys; refusing ambiguous results")
    if set(keys) - set(expected):
        raise ValueError("Unexpected request keys; configuration or results changed")
