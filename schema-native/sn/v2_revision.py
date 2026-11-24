"""Versioned, model-free v0.2 authoring. v0.1 code/data are read-only parents.

No model/server/training entry point. A five-tool review catalog is not a final
experiment catalog; nominated near misses still require independent judgement.
"""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import re
import zipfile

from . import v2_authoring as parent


DATA = Path(parent.paths.DATA, "v2-authoring-v0.2")
SEED = "v2-authoring-v0.2-20261125"


def task_id(tool_id):
    return "V2B_" + parent.digest((SEED + "\0" + tool_id).encode())[:12]


def load():
    parent_manifest = parent.strict_loads((parent.DATA / "manifest.json").read_text())
    for name, sha in parent_manifest["inputs_sha256"].items():
        if parent.digest((parent.REPO / name).read_bytes()) != sha:
            raise ValueError("v0.1 parent input changed: " + name)
    old, pool, schemas, _, _ = parent.load_inputs()
    revisions = parent.read_rows(DATA / "revisions.jsonl")
    by = {r["tool_id"]: r for r in revisions}
    if len(by) != len(revisions) or set(by) != {d["tool_id"] for d in old}:
        raise ValueError("Each parent task needs exactly one revision record")
    clean = []
    allowed = {"wording_revision", "unchanged", "ambiguity_repair", "answer_contract_revision", "request_contract_revision"}
    for draft in old:
        r = by[draft["tool_id"]]
        if r["change_kind"] not in allowed:
            raise ValueError("Unknown change kind")
        item = copy.deepcopy(draft)
        item["request"] = r["request"]
        item["gold_args"] = copy.deepcopy(r.get("gold_args", draft["gold_args"]))
        item["labels"] = [x for x in item["labels"] if x not in r.get("drop_labels", [])]
        changed_gold = not parent.argument_equal(item["gold_args"], draft["gold_args"])
        if changed_gold != (r["change_kind"] == "answer_contract_revision"):
            raise ValueError("Gold change and revision type disagree")
        if (item["request"] == draft["request"]) != (r["change_kind"] == "unchanged"):
            raise ValueError("Unchanged revision label disagrees with request")
        parent.validator(schemas[item["tool_id"]]).validate(item["gold_args"])
        leaks = parent.build_tasks.leakage(item["request"], pool[item["tool_id"]], schemas[item["tool_id"]])
        if leaks:
            raise ValueError(item["tool_id"] + " request leakage: " + str(leaks))
        item["task_id"] = task_id(item["tool_id"])
        item["change_kind"] = r["change_kind"]
        clean.append(item)
    nominations = parent.strict_loads((DATA / "catalog-nominations.json").read_text())
    if set(nominations["tools"]) != set(by):
        raise ValueError("Missing catalog nomination")
    for tid, row in nominations["tools"].items():
        ids = row["near"] + row["adjacent"]
        if tid in ids or len(ids) != len(set(ids)) or not set(ids) <= pool.keys():
            raise ValueError("Invalid catalog nomination")
    return old, clean, pool, schemas, nominations


def catalogs(clean, pool, nominations):
    """Reserve scarce nominated neighbors before filling, with a hard global cap.

    This deterministic heuristic does not prove catalog feasibility or semantic
    closeness. Shortfalls are disclosed and block the proposed readiness gate.
    """
    cap = nominations["max_distractor_appearances"]
    minimum = nominations["minimum_nominated_near_misses"]
    if type(cap) is not int or cap < 1 or type(minimum) is not int or not 0 <= minimum <= 4:
        raise ValueError("Invalid catalog limits")
    counts = Counter()
    selected = {d["tool_id"]: [] for d in clean}
    order = sorted(clean, key=lambda d: (len(nominations["tools"][d["tool_id"]]["near"]), task_id(d["tool_id"])))
    for draft in order:
        tid = draft["tool_id"]
        for other in nominations["tools"][tid]["near"]:
            if len(selected[tid]) >= minimum:
                break
            if counts[other] < cap:
                selected[tid].append(other)
                counts[other] += 1
    for draft in sorted(clean, key=lambda d: d["task_id"]):
        tid = draft["tool_id"]
        nom = nominations["tools"][tid]
        words = set(re.findall(r"[a-z]{3,}", draft["request"].lower()))
        def rank(other):
            category = 0 if other in nom["near"] else 1 if other in nom["adjacent"] else 2
            overlap = len(words & set(re.findall(r"[a-z]{3,}", pool[other]["description"].lower())))
            return category, -overlap, parent.digest((SEED + tid + other).encode())
        for other in sorted(pool, key=rank):
            if len(selected[tid]) == 4:
                break
            if other != tid and other not in selected[tid] and counts[other] < cap:
                selected[tid].append(other)
                counts[other] += 1
        if len(selected[tid]) != 4:
            raise ValueError("Cannot fill catalog within cap; do not relax it")
    result = {}
    for tid, distractors in selected.items():
        ids = sorted([tid, *distractors], key=lambda x: parent.digest((SEED + tid + "order" + x).encode()))
        near = sorted(set(distractors) & set(nominations["tools"][tid]["near"]))
        result[tid] = {"task_id": task_id(tid), "tool_id": tid, "tool_ids": ids,
                       "nominated_near_tool_ids": near, "nominated_minimum_met": len(near) >= minimum,
                       "independently_verified_near_misses": False}
    return result, counts


def packet(clean, pool, schemas, cats, policy):
    # Explicit whitelist: neither gold nor parent IDs, pair labels or nominations.
    return [{"task_id": d["task_id"], "request": d["request"], "system_policy": policy,
             "tools": [{"name": pool[t]["tool_name"], "description": pool[t]["description"],
                        "parameters": schemas[t]} for t in cats[d["tool_id"]]["tool_ids"]]}
            for d in sorted(clean, key=lambda d: d["task_id"])]


def diagnose(answer, expected_tool, gold, schema):
    """Prospective review diagnostic, not a change to frozen E0/E0b taxonomy.

    Default recognition covers directly declared root properties in this tranche.
    It makes no unsupported claims about defaults behind refs/combinators.
    """
    valid = parent.validator(schema).is_valid(answer["arguments"])
    same_tool = answer["tool"] == expected_tool
    args = answer["arguments"]
    extras = []
    if valid and same_tool and isinstance(args, dict) and isinstance(gold, dict):
        for key in sorted(args.keys() - gold.keys()):
            sub = schema.get("properties", {}).get(key)
            if isinstance(sub, dict) and "default" in sub and parent.argument_equal(args[key], sub["default"]):
                extras.append(key)
    trimmed = {k: v for k, v in args.items() if k not in extras} if isinstance(args, dict) else args
    equal = same_tool and parent.argument_equal(args, gold)
    only_defaults = bool(extras) and parent.argument_equal(trimmed, gold)
    kind = ("invalid" if not valid else "wrong_tool" if not same_tool else "correct" if equal
            else "valid_extra_default_fields" if only_defaults else "valid_wrong_value")
    return {"raw_valid": valid, "tool_matches": same_tool, "arguments_match": equal,
            "extra_default_paths": ["/" + k.replace("~", "~0").replace("/", "~1") for k in extras],
            "has_extra_default_fields": bool(extras), "only_extra_defaults": only_defaults,
            "review_error_kind": kind, "default_diagnostic_scope": "direct_root_properties"}


def compare_review(clean, pool, schemas, cats, answers, reviewer):
    if not reviewer or reviewer == parent.AUTHOR:
        raise ValueError("A separately identified reviewer is required")
    by = {d["task_id"]: d for d in clean}
    if len(answers) != len(by) or {a["task_id"] for a in answers} != by.keys():
        raise ValueError("Each v0.2 task must be answered exactly once")
    rows = []
    for answer in sorted(answers, key=lambda a: a["task_id"]):
        if set(answer) != {"task_id", "tool", "arguments"}:
            raise ValueError("Unexpected answer fields")
        d = by[answer["task_id"]]
        visible = {pool[t]["tool_name"]: schemas[t] for t in cats[d["tool_id"]]["tool_ids"]}
        if answer["tool"] not in visible:
            rows.append({"task_id": answer["task_id"], "review_error_kind": "tool_not_in_catalog"})
            continue
        rows.append({"task_id": answer["task_id"], **diagnose(answer, pool[d["tool_id"]]["tool_name"],
                                                            d["gold_args"], visible[answer["tool"]])})
    return {"reviewer_id": reviewer, "comparisons": rows, "independence_verified": False,
            "approved_for_test": False, "note": "Preserve a fresh first solve and context disclosure; no automatic promotion."}


def build():
    old, clean, pool, schemas, nominations = load()
    cats, counts = catalogs(clean, pool, nominations)
    policy = (DATA / "SYSTEM_POLICY.txt").read_text()
    parent_by = {d["tool_id"]: d for d in old}
    pairs = []
    for d in sorted(clean, key=lambda d: d["task_id"]):
        p = parent_by[d["tool_id"]]
        pairs.append({"task_id": d["task_id"], "parent_task_id": parent.review_id(p), "tool_id": d["tool_id"],
                      "change_kind": d["change_kind"], "original_wording_control": p["request"],
                      "clean_request": d["request"], "original_gold_args": p["gold_args"],
                      "clean_gold_args": d["gold_args"], "gold_unchanged": parent.argument_equal(p["gold_args"], d["gold_args"]),
                      "control_catalog_tool_ids": cats[d["tool_id"]]["tool_ids"],
                      "clean_catalog_tool_ids": cats[d["tool_id"]]["tool_ids"],
                      "wording_only_candidate": d["change_kind"] == "wording_revision",
                      "control_policy_sha256": parent.digest(policy.encode()), "clean_policy_sha256": parent.digest(policy.encode()),
                      "pure_scaffolding_effect_established": False,
                      "previous_blind_answers_reusable_as_new_results": False})
    summary = {"version": "v2-authoring-v0.2", "tasks": len(clean), "gold_raw_valid": len(clean),
               "gold_changed_tools": [d["tool_id"] for d in clean if not parent.argument_equal(d["gold_args"], parent_by[d["tool_id"]]["gold_args"])],
               "change_kinds": dict(Counter(d["change_kind"] for d in clean)),
               "max_distractor_appearances": max(counts.values()), "distractor_fraction_cap": nominations["max_distractor_appearances"] / len(clean),
               "nominated_near_miss_shortfalls": sorted(t for t, c in cats.items() if not c["nominated_minimum_met"]),
               "near_misses_independently_verified": False, "fresh_blind_reviews": 0, "approved_test_intents": 0,
               "target_features": {k: sum(parent.su.features(schemas[d["tool_id"]])[k] for d in clean)
                                   for k in ("has_ref", "has_allOf", "has_oneOf", "has_anyOf", "has_conditional", "has_patternProperties")},
               "native_engine_checks": 0, "additional_model_endpoint_requests": 0, "training_runs": 0,
               "freeze_ready": False}
    source_paths = [DATA / "revisions.jsonl", DATA / "catalog-nominations.json", DATA / "SYSTEM_POLICY.txt",
                    DATA / "FRESH_REVIEW_INSTRUCTIONS.md", parent.DATA / "drafts.jsonl", parent.DATA / "manifest.json",
                    Path(__file__), Path(parent.__file__), Path(parent.paths.ANALYSIS, "v2-authoring-review-v0.1/ADJUDICATION.md")]
    manifest = {"version": summary["version"], "status": "PROVISIONAL; FRESH REVIEW AND CATALOG WORK REQUIRED",
                "date": "2026-11-25", "inputs_sha256": {str(p.relative_to(parent.REPO)): parent.digest(p.read_bytes()) for p in source_paths},
                "parent_source_receipt_unchanged": True, "raw_schemas_copied_to_git": False,
                "scope": "authoring/review only; old E0/E0b rules and model profiles unchanged"}
    line_file = lambda rows: "".join(parent.serialized(r) + "\n" for r in rows)
    return {"drafts.clean.jsonl": line_file(sorted(clean, key=lambda d: d["task_id"])),
            "pairs.jsonl": line_file(pairs), "catalogs.jsonl": line_file(cats[t] for t in sorted(cats)),
            "manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            "validation.json": json.dumps(summary, indent=2, sort_keys=True) + "\n"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "export-review", "check-review"])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--reviewer")
    args = parser.parse_args()
    if args.command == "audit":
        for name, text in build().items():
            path = DATA / name
            if args.check:
                if not path.exists() or path.read_text() != text:
                    raise SystemExit("Artifact differs: " + name)
            else:
                path.write_text(text)
        print("PASS: v0.2 authoring artifacts; readiness remains false")
        return
    if args.check or args.out is None:
        parser.error("Review commands require --out and do not support --check")
    old, clean, pool, schemas, nominations = load()
    cats, _ = catalogs(clean, pool, nominations)
    if args.command == "export-review":
        visible = packet(clean, pool, schemas, cats, (DATA / "SYSTEM_POLICY.txt").read_text())
        with zipfile.ZipFile(args.out, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            payloads = {"tasks.jsonl": "".join(parent.serialized(p) + "\n" for p in visible),
                        "SYSTEM_POLICY.txt": (DATA / "SYSTEM_POLICY.txt").read_text(),
                        "REVIEW_INSTRUCTIONS.md": (DATA / "FRESH_REVIEW_INSTRUCTIONS.md").read_text()}
            for name, text in payloads.items():
                info = zipfile.ZipInfo(name, date_time=(2026, 11, 25, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, text)
    else:
        if args.responses is None or not args.reviewer:
            parser.error("check-review requires --responses and --reviewer")
        result = compare_review(clean, pool, schemas, cats, parent.read_rows(args.responses), args.reviewer)
        with args.out.open("x") as stream:
            stream.write(parent.serialized(result) + "\n")
    print("Wrote " + str(args.out) + "; no approval or model work")


if __name__ == "__main__":
    main()
