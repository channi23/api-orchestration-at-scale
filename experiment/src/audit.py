"""Full JSONSchemaBench audit + eligibility filter for tool conversion.

Outputs (experiment/dataset/):
  audit_schemas.jsonl.gz   one record per schema: features, eligibility, exclusion reasons
  audit_summary.json       aggregate counts (machine readable)
  AUDIT.md                 human-readable summary
"""
from __future__ import annotations

import collections
import gzip
import json
import os
import sys

import jsonschema

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_utils as su  # noqa: E402

CFG = json.load(open(os.path.join(su.EXP, "config", "experiment.json")))
SEL = CFG["schema_selection"]


def validator_cls(s):
    try:
        return jsonschema.validators.validator_for(s, default=jsonschema.Draft7Validator)
    except Exception:
        return jsonschema.Draft7Validator


def audit_one(sid: str, s) -> dict:
    subset = sid.split("/")[0]
    rec = {"schema_id": sid, "subset": subset, "exclusion_reasons": []}
    ex = rec["exclusion_reasons"]
    rec["chars_pretty"] = len(json.dumps(s, indent=2, ensure_ascii=False))
    rec["chars_min"] = len(json.dumps(s, separators=(",", ":"), ensure_ascii=False))
    rec.update(su.features(s))
    is_obj = isinstance(s, dict) and isinstance(s.get("properties"), dict) and len(s["properties"]) > 0 \
        and s.get("type", "object") in ("object", ["object"])
    rec["root_object_with_properties"] = bool(is_obj)
    if isinstance(s, dict):
        rec.update(su.top_level_info(s))
    # reference status
    refs = list(su.iter_refs(s))
    rec["n_refs"] = len(refs)
    rec["ref_status"] = "none"
    if refs:
        try:
            su.dereference(s)
            rec["ref_status"] = "local_ok"
        except su.CyclicRef:
            rec["ref_status"] = "cyclic"
        except su.RefError:
            rec["ref_status"] = "nonlocal_or_unresolvable"
        except RecursionError:
            rec["ref_status"] = "cyclic"
    # metaschema validity
    try:
        validator_cls(s).check_schema(s)
        rec["metaschema_valid"] = True
    except Exception:
        rec["metaschema_valid"] = False
    rec["glaive_unsat_pattern"] = su.tscg_glaive_unsat_pattern(s)

    # ---- eligibility (order of reasons is informative, all reasons are recorded)
    if subset not in SEL["included_subsets"]:
        ex.append("subset_excluded_config_documents")
    if not is_obj:
        ex.append("root_not_object_with_properties")
    else:
        n = rec["n_top_props"]
        if n < SEL["min_top_props"] or n > SEL["max_top_props"]:
            ex.append("top_level_property_count_out_of_range")
    if rec["ref_status"] in ("cyclic",):
        ex.append("cyclic_ref")
    if rec["ref_status"] == "nonlocal_or_unresolvable":
        ex.append("nonlocal_or_unresolvable_ref")
    if not rec["metaschema_valid"]:
        ex.append("metaschema_invalid")
    if rec["glaive_unsat_pattern"]:
        ex.append("known_unsatisfiable_pattern")
    if rec["has_patternProperties"] and is_obj and not s.get("properties"):
        ex.append("only_pattern_properties")
    if rec["chars_pretty"] > SEL["max_chars_pretty"]:
        ex.append("too_large_for_100_tool_context")
    return rec


def main():
    records = []
    norm_hash_first = {}
    for sid, s in su.load_all():
        rec = audit_one(sid, s)
        # exact-duplicate detection on the normalized form (only meaningful if eligible so far)
        if not rec["exclusion_reasons"]:
            h = su.sha(su.normalize(s))
            rec["normalized_sha256"] = h
            if h in norm_hash_first:
                rec["exclusion_reasons"].append("exact_duplicate_of:" + norm_hash_first[h])
            else:
                norm_hash_first[h] = sid
        rec["eligible"] = not rec["exclusion_reasons"]
        records.append(rec)

    out_dir = os.path.join(su.EXP, "dataset")
    with gzip.open(os.path.join(out_dir, "audit_schemas.jsonl.gz"), "wt") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")

    feat_cols = ["has_ref", "has_nested_object", "has_array", "has_array_of_objects", "has_enum",
                 "has_oneOf", "has_anyOf", "has_allOf", "has_conditional", "has_not",
                 "has_patternProperties", "has_constraints", "has_format", "has_pattern",
                 "has_const", "has_default", "has_additionalProperties_false"]
    summ = {"dataset": "JSONSchemaBench", "source": "https://github.com/guidance-ai/jsonschemabench",
            "commit": CFG["dataset"]["commit"], "total": len(records), "by_subset": {},
            "selection_config": SEL}
    reason_counts = collections.Counter()
    first_reason = collections.Counter()
    for r in records:
        b = summ["by_subset"].setdefault(r["subset"], collections.Counter())
        b["n"] += 1
        for c in feat_cols:
            b[c] += int(bool(r.get(c)))
        b["root_object_with_properties"] += int(r["root_object_with_properties"])
        b["has_title_or_description"] += int(bool(r.get("has_title_or_description")))
        b["ref_" + r["ref_status"]] += 1
        b["metaschema_invalid"] += int(not r["metaschema_valid"])
        b["eligible"] += int(r["eligible"])
        if r["eligible"]:
            b["eligible_" + r.get("stratum", "na")] += 1
        for x in r["exclusion_reasons"]:
            reason_counts[x.split(":")[0]] += 1
        if r["exclusion_reasons"]:
            first_reason[r["exclusion_reasons"][0].split(":")[0]] += 1
    summ["by_subset"] = {k: dict(v) for k, v in summ["by_subset"].items()}
    tot = collections.Counter()
    for v in summ["by_subset"].values():
        tot.update(v)
    summ["totals"] = dict(tot)
    summ["exclusion_reason_counts_all"] = dict(reason_counts)
    summ["exclusion_reason_counts_primary"] = dict(first_reason)
    json.dump(summ, open(os.path.join(out_dir, "audit_summary.json"), "w"), indent=2, sort_keys=True)

    # markdown
    cols = ["n", "root_object_with_properties", "has_title_or_description", "has_ref", "ref_cyclic",
            "has_nested_object", "has_array", "has_array_of_objects", "has_enum", "has_oneOf",
            "has_anyOf", "has_allOf", "has_conditional", "has_not", "has_patternProperties",
            "has_constraints", "has_format", "has_pattern", "metaschema_invalid", "eligible",
            "eligible_flat", "eligible_structured"]
    lines = ["# JSONSchemaBench audit", "",
             f"Source: {summ['source']} @ `{summ['commit']}`  ",
             f"Total schemas observed: **{summ['total']}**", "",
             "Counts are numbers of schemas containing the feature anywhere in the schema "
             "(`has_nested_object` = an object with `properties` at depth >= 1; "
             "`has_conditional` = if/then/else, dependencies, dependentSchemas/Required; "
             "`has_constraints` = any of min/max/length/pattern/format/items-count/uniqueItems/multipleOf).",
             "", "| subset | " + " | ".join(c.replace("has_", "") for c in cols) + " |",
             "|---|" + "---:|" * len(cols)]
    for k in su.SUBSETS:
        v = summ["by_subset"].get(k, {})
        lines.append(f"| {k} | " + " | ".join(str(v.get(c, 0)) for c in cols) + " |")
    lines.append("| **TOTAL** | " + " | ".join(str(tot.get(c, 0)) for c in cols) + " |")
    lines += ["", "## Eligibility criteria (tool-convertible)", ""]
    lines += [f"- included subsets: {', '.join(SEL['included_subsets'])} "
              "(Kubernetes, Github_hard, Github_ultra, JsonSchemaStore excluded: predominantly whole "
              "configuration documents, not plausible tool inputs, and too large for 100-tool catalogs)",
              f"- root is an object with {SEL['min_top_props']}..{SEL['max_top_props']} top-level properties",
              "- metaschema-valid under its declared draft (default draft-7)",
              "- no cyclic, non-local or unresolvable `$ref` (needed for the NORMALIZED condition)",
              "- not matching the documented GlaiveAI unsatisfiable `oneOf` pattern (upstream issue #16)",
              f"- pretty-printed size <= {SEL['max_chars_pretty']} chars (context budget for 100 raw tools)",
              "- not an exact duplicate (sha256 of canonical normalized schema) of an earlier schema", "",
              "## Exclusion reasons (all reasons, a schema can have several)", "",
              "| reason | count |", "|---|---:|"]
    for k, v in sorted(reason_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Primary (first) exclusion reason", "", "| reason | count |", "|---|---:|"]
    for k, v in sorted(first_reason.items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {v} |")
    lines += ["", f"Eligible schemas: **{tot.get('eligible', 0)}** "
              f"(flat {tot.get('eligible_flat', 0)}, structured {tot.get('eligible_structured', 0)}). "
              "`flat` = no top-level property is an object/array/$ref/combinator (TSCG keeps all "
              "top-level structure); `structured` = at least one is (TSCG drops sub-structure).", ""]
    open(os.path.join(out_dir, "AUDIT.md"), "w").write("\n".join(lines))
    print("\n".join(lines[-40:]))


if __name__ == "__main__":
    main()
