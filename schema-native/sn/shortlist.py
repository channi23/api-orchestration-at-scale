"""Deterministic lexical shortlist baseline (BM25) for tool selection.

Purpose: give the hybrid arm (F) an honest floor. A learned selector, a Laya-style decision model
or a logit-scored LLM selector has to beat this to be worth its cost. No model, no embeddings.

Each tool is one document built from text the catalog already shows: name, description, and the
names and descriptions of its parameters (schema-derived candidates). The query is the user request.

usage: python -m sn.shortlist [--sizes 20 50 100]
Output: analysis/shortlist-bm25/{SHORTLIST.md, shortlist.json}
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re

from . import paths
import schema_utils as su  # type: ignore  # noqa: E402

TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)          # camelCase -> camel Case
    return TOKEN.findall(text.lower().replace("_", " "))


def schema_text(schema, depth=0) -> str:
    """Property names and descriptions, walking nested properties and array items."""
    if not isinstance(schema, dict) or depth > 4:
        return ""
    parts = [str(schema.get("title", "")), str(schema.get("description", ""))]
    for name, sub in (schema.get("properties") or {}).items():
        parts.append(name)
        parts.append(schema_text(sub, depth + 1))
    if isinstance(schema.get("items"), dict):
        parts.append(schema_text(schema["items"], depth + 1))
    for key in ("anyOf", "oneOf", "allOf"):
        for sub in schema.get(key) or []:
            parts.append(schema_text(sub, depth + 1))
    return " ".join(p for p in parts if p)


def tool_document(tool: dict, fields: str = "all") -> list[str]:
    head = f"{tool['tool_name']} {tool['description']}"
    if fields == "card":
        return tokens(head)
    return tokens(head + " " + schema_text(su.normalize(su.load_schema(tool["schema_id"]))))


class BM25:
    def __init__(self, docs: dict[str, list[str]], k1: float = 1.2, b: float = 0.75):
        self.k1, self.b, self.docs = k1, b, docs
        self.tf = {d: collections.Counter(t) for d, t in docs.items()}
        self.len = {d: len(t) for d, t in docs.items()}
        self.avg = sum(self.len.values()) / max(1, len(docs))
        df = collections.Counter(w for t in docs.values() for w in set(t))
        n = len(docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def score(self, query: list[str], d: str) -> float:
        s = 0.0
        for w in set(query):
            f = self.tf[d].get(w, 0)
            if f:
                s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[d] / self.avg))
        return s

    def rank(self, query: list[str]) -> list[str]:
        return sorted(self.docs, key=lambda d: (-self.score(query, d), d))


def run(sizes: list[int], ks: list[int], out_dir: str) -> dict:
    pool, tasks, cats = paths.pool(), paths.tasks(), paths.catalogs()
    res = {"ks": ks, "cells": []}
    for fields in ("card", "all"):
        doc = {tid: tool_document(t, fields) for tid, t in pool.items()}
        for size in sizes:
            ranks = []
            for t in tasks:
                cat = cats[f"C{size:03d}_R{t['replicate']:02d}"]
                bm = BM25({tid: doc[tid] for tid in cat["tool_ids"]})
                ranks.append(bm.rank(tokens(t["prompt"])).index(t["tool_id"]) + 1)
            res["cells"].append({"fields": fields, "size": size, "n": len(ranks),
                                 "recall_at": {str(k): sum(r <= k for r in ranks) / len(ranks) for k in ks},
                                 "mrr": sum(1 / r for r in ranks) / len(ranks)})
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "shortlist.json"), "w") as f:
        json.dump(res, f, indent=2)
    L = ["# BM25 shortlist baseline (model-free)", "",
         "Share of the 100 frozen tasks whose gold tool is inside the top-k of a BM25 ranking of the catalog. "
         "'card' indexes tool name + description only; 'all' adds parameter names and descriptions from the schema.", "",
         "| Indexed text | Catalog size | " + " | ".join(f"recall@{k}" for k in ks) + " | MRR |",
         "|---|---:|" + "---:|" * (len(ks) + 1)]
    for c in res["cells"]:
        L.append(f"| {c['fields']} | {c['size']} | " + " | ".join(f"{100 * c['recall_at'][str(k)]:.0f}%" for k in ks) + f" | {c['mrr']:.3f} |")
    L += ["", "Reading: recall@1 is what BM25 alone would score as a selector. recall@5 is the ceiling of a "
          "'shortlist 5, then let the model choose and fill arguments' pipeline. "
          "The tool names and descriptions were written by the experimenter, so absolute values are specific to this benchmark."]
    with open(os.path.join(out_dir, "SHORTLIST.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", nargs="+", type=int, default=[20, 50, 100])
    ap.add_argument("--ks", nargs="+", type=int, default=[1, 3, 5, 10])
    ap.add_argument("--out", default=os.path.join(paths.ANALYSIS, "shortlist-bm25"))
    a = ap.parse_args()
    res = run(a.sizes, a.ks, a.out)
    for c in res["cells"]:
        print(c["fields"], c["size"], {k: round(v, 3) for k, v in c["recall_at"].items()}, "mrr", round(c["mrr"], 3))


if __name__ == "__main__":
    main()
