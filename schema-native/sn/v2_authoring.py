"""Model-free v2 candidate audit and blind review export; no runner or training API.

The 32 assistant-authored drafts are source data, not examples produced by this module.
Audit never promotes a draft, assigns a split, or rewrites historical artifacts.
"""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import subprocess

import jsonschema
from referencing import Registry

from . import paths
from .router import strict_loads
import build_tasks
import schema_utils as su


REPO = Path(paths.REPO)
DATA = Path(paths.DATA, "v2-authoring-v0.1")
UPSTREAM = Path(su.DATA_DIR).parent
UPSTREAM_REVISION = "9a94995b9279ae3af3aed4b2629172790b968d14"
AUTHOR = "codex-authoring-20261125"
SEED = "v2-blind-review-20261125"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def serialized(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def read_rows(path):
    return [strict_loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def no_remote(uri):
    raise ValueError("Remote reference resolution is forbidden: " + uri)


def validator(schema):
    cls = jsonschema.validators.validator_for(schema, default=jsonschema.Draft7Validator)
    cls.check_schema(schema)
    # Formats are annotations in this provisional legacy-pool tranche, matching v1.
    # Unknown explicit dialects are not silently mapped to the default validator.
    if "$schema" in schema and schema["$schema"].rstrip("#") != cls.META_SCHEMA.get("id", cls.META_SCHEMA.get("$id", "")).rstrip("#"):
        raise ValueError("Unknown or unsupported explicit schema dialect")
    return cls(schema, registry=Registry(retrieve=no_remote))


def argument_equal(a, b):
    """JSON object order is ignored; arrays/strings/keys are exact; bool != number."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return Decimal(str(a)) == Decimal(str(b))
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(argument_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(argument_equal(x, y) for x, y in zip(a, b))
    return a == b


def review_id(draft):
    return "V2A_" + digest((SEED + "\0" + draft["tool_id"]).encode())[:12]


def review_packet(drafts, pool, schemas):
    """Only request-visible fields; target identity and all gold/eval fields stay out."""
    packets = []
    for draft in drafts:
        target = pool[draft["tool_id"]]
        words = set(re.findall(r"[a-z]{3,}", draft["request"].lower()))
        def rank(tool):
            overlap = len(words & set(re.findall(r"[a-z]{3,}", tool["description"].lower())))
            return (tool["family"] != target["family"], -overlap,
                    digest((SEED + target["tool_id"] + tool["tool_id"]).encode()))
        others = sorted((t for t in pool.values() if t["tool_id"] != target["tool_id"]), key=rank)[:4]
        catalog = sorted([target, *others], key=lambda t: digest((SEED + review_id(draft) + t["tool_id"]).encode()))
        if len(catalog) != 5:
            raise ValueError("Blind review requires five distinct tools")
        packets.append({"task_id": review_id(draft), "request": draft["request"],
                        "tools": [{"name": t["tool_name"], "description": t["description"],
                                   "parameters": schemas[t["tool_id"]]} for t in catalog]})
    return sorted(packets, key=lambda p: p["task_id"])


def check_review(drafts, pool, schemas, answers, reviewer):
    if not reviewer or reviewer == AUTHOR:
        raise ValueError("A separately identified reviewer is required")
    expected = {review_id(d): d for d in drafts}
    packets = {p["task_id"]: p for p in review_packet(drafts, pool, schemas)}
    if len(answers) != len(expected) or {a["task_id"] for a in answers} != expected.keys():
        raise ValueError("Review must cover each blind task exactly once")
    comparisons = []
    for answer in sorted(answers, key=lambda a: a["task_id"]):
        if set(answer) != {"task_id", "tool", "arguments"}:
            raise ValueError("Expected only task_id, tool and arguments")
        task = expected[answer["task_id"]]
        selected = next((t for t in packets[answer["task_id"]]["tools"] if t["name"] == answer["tool"]), None)
        valid = selected is not None and validator(selected["parameters"]).is_valid(answer["arguments"])
        agree = (valid and answer["tool"] == pool[task["tool_id"]]["tool_name"]
                 and argument_equal(answer["arguments"], task["gold_args"]))
        comparisons.append({"task_id": answer["task_id"], "raw_valid": valid,
                            "agrees_with_draft": agree, "requires_adjudication": not agree})
    return {"reviewer_id": reviewer, "author_id": AUTHOR, "comparisons": comparisons,
            "agreement_count": sum(r["agrees_with_draft"] for r in comparisons),
            "independence_verified": False, "approved_for_test": False,
            "note": "Agreement is not proof of independent authorship or semantic correctness. Preserve the blind-review evidence and adjudicate disagreements; this does not promote drafts."}


def load_inputs():
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=UPSTREAM, text=True).strip()
    if revision != UPSTREAM_REVISION:
        raise ValueError("Upstream schema collection revision differs")
    pool = {r["tool_id"]: r for r in read_rows(REPO / "experiment/dataset/tool_pool.v1.jsonl")}
    old = read_rows(REPO / "experiment/tasks/tasks.v1.jsonl")
    trainpool = read_rows(Path(paths.DATA, "trainpool/schemas.v1.jsonl"))
    schemas = {tid: su.load_schema(t["schema_id"]) for tid, t in pool.items()}
    for tid, schema in schemas.items():
        if su.sha(schema) != pool[tid]["schema_sha256"]:
            raise ValueError("Raw pool schema changed: " + tid)
    drafts = read_rows(DATA / "drafts.jsonl")
    if len({d["tool_id"] for d in drafts}) != len(drafts):
        raise ValueError("More than one draft for a tool")
    targets = {r["tool_id"] for r in old}
    for draft in drafts:
        if set(draft) != {"tool_id", "request", "gold_args", "reasoning_note", "labels"}:
            raise ValueError("Unexpected draft source fields")
        tid = draft["tool_id"]
        if tid not in pool or tid in targets:
            raise ValueError("Draft is not a previously untargeted pool tool: " + tid)
        validator(schemas[tid]).validate(draft["gold_args"])
        leaks = build_tasks.leakage(draft["request"], pool[tid], schemas[tid])
        if leaks:
            raise ValueError("Draft leakage " + tid + ": " + ", ".join(leaks))
    return drafts, pool, schemas, old, trainpool


def audit():
    drafts, pool, schemas, old, trainpool = load_inputs()
    targets = {r["tool_id"] for r in old}
    target_families = defaultdict(list)
    for tid in sorted(targets):
        target_families[pool[tid]["family"]].append(tid)
    catalogs = {c["catalog_id"]: c for c in json.loads((REPO / "experiment/catalogs/catalogs.v1.json").read_text())["catalogs"]}
    # Inspect only request catalog metadata, never scores or output correctness.
    history = {}
    historical_files = {
        "original_full_v2": REPO / "experiment/runs/full-v2/results.jsonl",
        "e0_clean": Path(paths.ANALYSIS, "e0-clean-v1/results.jsonl.gz"),
    }
    import gzip
    for name, path in historical_files.items():
        if not path.exists():
            raise ValueError("Historical exposure evidence is missing: " + name)
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt") as stream:
            ids = set()
            for line in stream:
                if line.strip():
                    record = json.loads(line)
                    if record["http_status"] == 200:
                        ids.add(record["catalog_id"])
        ids.discard(None)
        if not ids <= catalogs.keys():
            raise ValueError("Unknown historical catalog")
        history[name] = {tid for cid in ids for tid in catalogs[cid]["tool_ids"]}
    train_hashes = defaultdict(list)
    train_raw_hashes = {}
    for row in trainpool:
        train_hashes[su.sha(su.load_schema(row["schema_id"]))].append(row["schema_id"])
        train_raw_hashes[row["schema_id"]] = digest(Path(su.DATA_DIR, row["schema_id"] + ".json").read_bytes())
    draft_by_tool = {d["tool_id"]: d for d in drafts}
    stress = strict_loads((DATA / "stress-inventory.json").read_text())
    if stress["archive_sha256"] != "8bb8ab2ac1553bf7bc3ae068e615e23d776ddb0a8c2550d4cde82e206fad1132":
        raise ValueError("Unexpected external stress source")
    stress_schemas = defaultdict(list)
    for case in stress["cases"]:
        for sha in set(case["schema_hashes"]):
            stress_schemas[sha].append(case["case_id"])
    inventory = []
    for tid in sorted(set(pool) - targets):
        tool, schema = pool[tid], schemas[tid]
        raw_path = Path(su.DATA_DIR, tool["schema_id"] + ".json")
        matches = sorted(train_hashes.get(su.sha(schema), []))
        inventory.append({"tool_id": tid, "schema_id": tool["schema_id"], "pool_family": tool["family"],
                          "subset": tool["subset"], "stratum": tool["stratum"],
                          "schema_raw_sha256": digest(raw_path.read_bytes()), "schema_canonical_sha256": su.sha(schema),
                          "collection_revision": UPSTREAM_REVISION,
                          "declared_schema_uri": schema.get("$id", schema.get("id")),
                          "dialect": schema.get("$schema", "implicit-draft7-for-this-legacy-tranche"),
                          "source_group_id": None, "source_license_status": "unverified",
                          "source_holdout_verified": False,
                          "historical_catalog_exposure": {name: tid in ids for name, ids in history.items()},
                          "v1_target_family_siblings": target_families.get(tool["family"], []),
                          "exact_trainpool_matches": matches,
                          "exact_stress_schema_matches": sorted(stress_schemas.get(su.sha(schema), [])),
                          "candidate_status": "draft_pending_independent_review" if tid in draft_by_tool else "not_authored",
                          "split": "development_only" if tool["family"] in target_families else "unassigned",
                          "accepted_for_test": False})
    inputs = {str(p.relative_to(REPO)): digest(p.read_bytes()) for p in [
        REPO / "experiment/dataset/tool_pool.v1.jsonl", REPO / "experiment/tasks/tasks.v1.jsonl",
        REPO / "experiment/catalogs/catalogs.v1.json", Path(paths.DATA, "trainpool/schemas.v1.jsonl"),
        DATA / "drafts.jsonl", DATA / "stress-inventory.json", Path(__file__), *historical_files.values()]}
    inventory_text = "".join(serialized(r) + "\n" for r in inventory)
    manifest = {"version": "v2-authoring-v0.1", "date": "2026-11-25", "author_id": AUTHOR,
                "status": "PROVISIONAL AUTHORING; NOT A FROZEN DATASET", "inputs_sha256": inputs,
                "inventory_sha256": digest(inventory_text.encode()), "review_packet_seed": SEED,
                "trainpool_schema_bytes_sha256": digest(serialized(train_raw_hashes).encode()),
                "raw_schemas_copied_to_git": False, "validator_version": version('jsonschema'),
                "format_assertions": False, "remote_references": "forbidden",
                "authoring_method": "assistant drafting in the current chat, not human-authored or independently reviewed",
                "independent_review_received": False, "additional_model_endpoint_requests": 0, "training_runs": 0}
    validation = {"pool_tools": len(pool), "old_target_tools": len(targets), "candidate_tools": len(inventory),
                  "drafts": len(drafts), "gold_raw_valid": len(drafts), "request_leakage_findings": 0,
                  "independent_reviews": 0, "accepted_test_intents": 0, "engine_checks_run": 0,
                  "candidate_strata": dict(Counter(r["stratum"] for r in inventory)),
                  "draft_strata": dict(Counter(pool[d["tool_id"]]["stratum"] for d in drafts)),
                  "candidate_exposure_counts": {name: sum(r["historical_catalog_exposure"][name] for r in inventory) for name in history},
                  "known_v1_family_tools": [r["tool_id"] for r in inventory if r["v1_target_family_siblings"]],
                  "exact_trainpool_matches": sum(bool(r["exact_trainpool_matches"]) for r in inventory),
                  "external_stress_cases_inventoried": len(stress["cases"]),
                  "exact_stress_schema_matches": sum(bool(r["exact_stress_schema_matches"]) for r in inventory),
                  "unverified_source_licenses": len(inventory), "freeze_ready": False,
                  "limits": ["Validation does not establish semantic gold correctness or independence.",
                             "Historical inference exposure does not update weights or alone prove training leakage.",
                             "Only exact canonical training overlap is checked; semantic, renamed, structural and stress-example lineage audits remain open.",
                             "No split assignment, engine enforcement check, full dataset or cost claim is established."]}
    return {"inventory.jsonl": inventory_text, "manifest.json": serialized(manifest) + "\n",
            "validation.json": json.dumps(validation, indent=2, sort_keys=True) + "\n"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "export-review", "check-review"])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--reviewer")
    args = parser.parse_args()
    if args.command == "audit":
        outputs = audit()
        for name, text in outputs.items():
            destination = DATA / name
            if args.check:
                if not destination.exists() or destination.read_text() != text:
                    raise SystemExit("Artifact differs: " + name)
            else:
                destination.write_text(text)
        print(outputs["validation.json"])
        return
    if args.check or args.out is None:
        parser.error("Review commands require --out and do not support --check")
    # Exclusive creation: never overwrite a review packet or a previous review record.
    if args.out.exists():
        raise SystemExit("Refusing to overwrite review evidence: " + str(args.out))
    drafts, pool, schemas, _, _ = load_inputs()
    if args.command == "export-review":
        result = "".join(serialized(r) + "\n" for r in review_packet(drafts, pool, schemas))
    else:
        if args.responses is None or not args.reviewer:
            parser.error("check-review requires --responses and --reviewer")
        result = serialized(check_review(drafts, pool, schemas, read_rows(args.responses), args.reviewer)) + "\n"
    with args.out.open("x") as stream:
        stream.write(result)
    print("Wrote " + str(args.out) + "; drafts remain unapproved")


if __name__ == "__main__":
    main()
