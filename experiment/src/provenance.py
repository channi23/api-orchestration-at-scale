"""Provenance-checked number rendering for the communication artifacts.

Every number shown in the summary / diagram / explainer is resolved from a validated artifact
via a *key*; an unknown key is a hard error. Keys look like:

  main[size=100,arm=raw].e2e        -> analysis results.json main_table row, field (proportions rendered as %)
  arggen[arm=tscg].arg_em           -> analysis results.json arggen_table row
  cmp[name=PRIMARY: TSCG vs Raw, E2E, pooled sizes].diff_pp
  fail[arm=tscg|all].wrong tool     -> failures_primary
  audit[structured].with_dropped_substructure  -> representations/tscg/information_audit.v1.summary.json
  meta.n_tools / meta.n_tasks ...   -> counts computed from frozen artifacts
"""
from __future__ import annotations

import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
PCT_FIELDS = {"selection", "arg_em", "field_acc", "schema_valid", "json_valid", "e2e", "e2e_strict", "semantic_correct",
              "tool_echo_correct", "acc_a", "acc_b"}


class Prov:
    def __init__(self, analysis_dir: str):
        self.analysis_dir = analysis_dir
        self.res_path = os.path.join(analysis_dir, "results.json")
        self.res = json.load(open(self.res_path))
        self.res_sha = hashlib.sha256(open(self.res_path, "rb").read()).hexdigest()
        self.audit = json.load(open(os.path.join(EXP, "representations", "tscg", "information_audit.v1.summary.json")))
        self.tokens = json.load(open(os.path.join(EXP, "representations", "representation_metrics.v1.json")))
        pool = [json.loads(l) for l in open(os.path.join(EXP, "dataset", "tool_pool.v1.jsonl"))]
        tasks = [json.loads(l) for l in open(os.path.join(EXP, "tasks", "tasks.v1.jsonl"))]
        audit_all = json.load(open(os.path.join(EXP, "dataset", "audit_summary.json")))
        cats = json.load(open(os.path.join(EXP, "catalogs", "catalogs.v1.json")))["catalogs"]
        self.meta = {"n_schemas": audit_all["total"], "n_eligible": audit_all["totals"]["eligible"],
                     "n_tools": len(pool), "n_flat": sum(t["stratum"] == "flat" for t in pool),
                     "n_structured": sum(t["stratum"] == "structured" for t in pool),
                     "n_tasks": len(tasks), "n_intents": len({t["intent_id"] for t in tasks}),
                     "n_catalogs": len(cats), "n_replicates": len({c["replicate"] for c in cats}),
                     "n_requests": self.res["n_requests"]}
        self.used: dict[str, str] = {}

    def _row(self, table, sel):
        conds = dict(kv.split("=", 1) for kv in sel.split(","))
        alias = {"size": "tools"}
        for r in table:
            if all(str(r.get(alias.get(k, k), r.get(k))) == v for k, v in conds.items()):
                return r
        raise KeyError(f"no row matching {sel}")

    def value(self, key: str):
        m = re.fullmatch(r"(\w+)(?:\[(.+?)\])?(?:\.(.+))?", key)
        if not m:
            raise KeyError(key)
        kind, sel, field = m.groups()
        if kind == "main":
            v = self._row(self.res["main_table"], sel)[field]
        elif kind == "arggen":
            v = self._row(self.res["arggen_table"], sel)[field]
        elif kind == "cmp":
            name = sel.split("=", 1)[1]
            c = next((c for c in self.res["paired_comparisons"] if c["name"] == name), None)
            if c is None:
                raise KeyError(key)
            v = c[field]
        elif kind == "fail":
            v = self.res["failures_primary"].get(sel.split("=", 1)[1], {}).get(field, 0)
        elif kind == "inter":
            k = sel.split("=", 1)[1]
            row = next((r for r in self.res["effect_by_size_interaction"]["rows"] if str(r["size"]) == k), None)
            if row is None:
                raise KeyError(key)
            v = row[field]
        elif kind == "glm":
            v = self.res["token_covariate_glm"][field][sel]
        elif kind == "lat":
            sz, arm = [x.split("=")[1] for x in sel.split(",")]
            row = next(c for c in self.res["latency_secondary_exploratory"]["cells"] if str(c["size"]) == sz and c["arm"] == arm)
            v = row[field]
        elif kind == "deg":
            v = self.res["degradation"][sel.split("=", 1)[1]][field]
        elif kind == "audit":
            v = self.audit[sel][field]
        elif kind == "tok":
            v = self.tokens[sel][field]
        elif kind == "meta":
            v = self.meta[field]
        else:
            raise KeyError(key)
        return v, field

    def fmt(self, key: str) -> str:
        v, field = self.value(key)
        if v is None:
            s = "n/a"
        elif field in PCT_FIELDS:
            s = f"{100 * v:.1f}%"
        elif field in ("diff_pp", "did_pp", "effect_at_size_pp", "effect_at_base_pp"):
            s = f"{v:+.1f} pp"
        elif field in ("mcnemar_exact_p", "holm_p", "sign_test_p", "p"):
            s = f"{v:.2g}"
        elif field.endswith("_pct") and isinstance(v, (int, float)):
            s = f"{v:.1f}"
        elif isinstance(v, float):
            s = f"{v:,.0f}" if abs(v) >= 100 else f"{v:.2f}"
        elif isinstance(v, list):
            s = "[" + ", ".join(f"{x:+.1f}" if isinstance(x, float) else str(x) for x in v) + "]"
        else:
            s = f"{v:,}" if isinstance(v, int) else str(v)
        self.used[key] = s
        return s

    def render(self, text: str, footnotes: bool = True) -> str:
        keys: list[str] = []

        def sub(m):
            k = m.group(1).strip()
            s = self.fmt(k)
            if k not in keys:
                keys.append(k)
            return f"{s}<sup>[{keys.index(k) + 1}]</sup>" if footnotes else s

        out = re.sub(r"\{\{(.+?)\}\}", sub, text)
        if footnotes and keys:
            out += "\n\n---\n**Provenance.** Every number above is resolved automatically (`src/provenance.py`) from validated artifacts. "
            out += f"Analysis file: `{os.path.relpath(self.res_path, EXP)}` (sha256 `{self.res_sha[:16]}…`).\n\n"
            out += "\n".join(f"[{i + 1}] `{k}`" for i, k in enumerate(keys)) + "\n"
        return out
