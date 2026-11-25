"""Model-free v0.3 wording/policy revision; immutable v0.1/v0.2 parents.

Reuses v0.2 validation, catalogs, blind serialization and review comparison.
No training or inference entry point. Pool probes are evidence, not near-miss ratings.
"""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import re
import zipfile

from . import v2_revision as previous


BASE = previous.parent
DATA = Path(BASE.paths.DATA, "v2-authoring-v0.3")
SEED = "v2-authoring-v0.3-20261125"
PROBES = {
    "T254": r"retention|lifespan|time.?to.?live|ttl|expir|timeout",
    "T131": r"calorie|nutrition|meal|food",
    "T045": r"room|booking|moderation|reservation|slot",
    "T064": r"country|region|state|location",
    "T093": r"subtitle|caption|text.?track|audio.?track",
    "T243": r"score|leaderboard|match.?result|player",
    "T016": r"include|exclude|glob|filter|allow.?list|white.?list|ignore|log.?level",
}


def new_id(tid):
    return "V2C_" + BASE.digest((SEED + "\0" + tid).encode())[:12]


def load():
    # Derived parent bytes as well as parent inputs must still reproduce.
    for name, expected in previous.build().items():
        if (previous.DATA / name).read_text() != expected:
            raise ValueError("v0.2 parent changed: " + name)
    _, old, pool, schemas, nominations = previous.load()
    edits = BASE.read_rows(DATA / "wording.jsonl")
    by = {e["tool_id"]: e for e in edits}
    if len(by) != len(edits) or not set(by) <= {d["tool_id"] for d in old}:
        raise ValueError("Duplicate or unknown wording override")
    if any(set(e) != {"tool_id", "request", "reason"} for e in edits):
        raise ValueError("Wording overrides cannot change gold or tool descriptions")
    cats, counts = previous.catalogs(old, pool, nominations)
    clean = copy.deepcopy(old)
    for d in clean:
        tid = d["tool_id"]
        d["parent_task_id"] = d["task_id"]
        d["task_id"] = new_id(tid)
        d["parent_change_kind"] = d.pop("change_kind")
        d["change_kind"] = "wording_revision_vs_v0.2" if tid in by else "unchanged_vs_v0.2"
        if tid in by:
            if d["request"] == by[tid]["request"]:
                raise ValueError("Override makes no wording change")
            d["request"] = by[tid]["request"]
        BASE.validator(schemas[tid]).validate(d["gold_args"])
        if BASE.build_tasks.leakage(d["request"], pool[tid], schemas[tid]):
            raise ValueError("Request leakage: " + tid)
        cats[tid] = {**cats[tid], "task_id": d["task_id"]}
    policy = (previous.DATA / "SYSTEM_POLICY.txt").read_text() + (DATA / "ALIAS_POLICY.txt").read_text()
    return old, clean, pool, schemas, cats, counts, policy


def source_texts(schema, path=""):
    """Schema-position-aware text scan; never treats enum/default data as schemas."""
    if not isinstance(schema, dict):
        return
    for key in ("description", "title"):
        if isinstance(schema.get(key), str):
            yield path + "/" + key, schema[key]
    for key in BASE.su.SCHEMA_MAP_KEYS:
        if isinstance(schema.get(key), dict):
            for name, child in schema[key].items():
                escaped = name.replace("~", "~0").replace("/", "~1")
                child_path = path + "/" + key + "/" + escaped
                if key in ("properties", "patternProperties"):
                    yield child_path, name
                yield from source_texts(child, child_path)
    for key in BASE.su.SCHEMA_LIST_KEYS:
        if isinstance(schema.get(key), list):
            for i, child in enumerate(schema[key]):
                yield from source_texts(child, path + "/" + key + "/" + str(i))
    for key in BASE.su.SCHEMA_SINGLE_KEYS:
        value = schema.get(key)
        if isinstance(value, dict):
            yield from source_texts(value, path + "/" + key)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                yield from source_texts(child, path + "/" + key + "/" + str(i))


def source_probe(pool, schemas):
    searches = []
    for target, pattern in PROBES.items():
        candidates = []
        rx = re.compile(pattern, re.I)
        for tid in sorted(pool):
            if tid == target:
                continue
            texts = [("tool_description", pool[tid]["description"]), *source_texts(schemas[tid])]
            matches = [{"path": p, "text": t} for p, t in texts if rx.search(t)]
            if matches:
                candidates.append({"tool_id": tid, "tool_name": pool[tid]["tool_name"],
                                   "schema_id": pool[tid]["schema_id"],
                                   "schema_canonical_sha256": BASE.su.sha(schemas[tid]),
                                   "matched_texts": matches,
                                   "near_miss_verified": False, "units_or_api_semantics_verified": False})
        searches.append({"target_tool_id": target, "pattern": pattern, "candidates": candidates})
    return {"searched_pool_size": len(pool), "searches": searches,
            "scope": "Frozen 300-tool pool only. Text hits are not semantic peers; misses are not an absence proof in upstream or other APIs.",
            "catalogs_changed_from_probe": False}


def build():
    old, clean, pool, schemas, cats, counts, policy = load()
    old_by = {d["tool_id"]: d for d in old}
    pairs = [{"task_id": d["task_id"], "parent_task_id": d["parent_task_id"], "tool_id": d["tool_id"],
              "parent_request": old_by[d["tool_id"]]["request"], "request": d["request"],
              "gold_unchanged": BASE.argument_equal(d["gold_args"], old_by[d["tool_id"]]["gold_args"]),
              "control_catalog_tool_ids": cats[d["tool_id"]]["tool_ids"],
              "clean_catalog_tool_ids": cats[d["tool_id"]]["tool_ids"],
              "shared_policy_sha256": BASE.digest(policy.encode()),
              "old_answers_are_new_results": False, "pure_scaffolding_effect_established": False}
             for d in sorted(clean, key=lambda d: d["task_id"])]
    assert all(p["gold_unchanged"] for p in pairs)
    probe = source_probe(pool, schemas)
    summary = {"version": "v2-authoring-v0.3", "tasks": len(clean), "gold_raw_valid": len(clean),
               "gold_changes_vs_v0.2": 0, "tool_description_changes": 0, "raw_schema_changes": 0,
               "change_kinds": dict(Counter(d["change_kind"] for d in clean)),
               "catalogs_identical_to_v0.2": True, "max_distractor_appearances": max(counts.values()),
               "v0.2_reviewer_clearly_strong_catalogs": 9, "v0.3_catalogs_verified": False,
               "probe_candidate_counts": {s["target_tool_id"]: len(s["candidates"]) for s in probe["searches"]},
               "native_engine_checks": 0, "additional_model_endpoint_requests": 0, "training_runs": 0,
               "fresh_v0.3_blind_reviews": 0, "approved_test_intents": 0, "freeze_ready": False}
    files = [DATA / "wording.jsonl", DATA / "ALIAS_POLICY.txt", DATA / "FRESH_REVIEW_INSTRUCTIONS.md",
             previous.DATA / "manifest.json", previous.DATA / "catalogs.jsonl", previous.DATA / "SYSTEM_POLICY.txt",
             Path(__file__), Path(previous.__file__), Path(BASE.__file__),
             Path(BASE.paths.ANALYSIS, "v2-authoring-review-v0.2/ADJUDICATION.md")]
    manifest = {"version": summary["version"], "date": "2026-11-25", "status": "PROVISIONAL WORDING REVIEW ONLY",
                "inputs_sha256": {str(p.relative_to(BASE.REPO)): BASE.digest(p.read_bytes()) for p in files},
                "parent_drafts_and_reviews_unchanged": True, "raw_schemas_copied_to_git": False,
                "aliases": [], "string_comparison": "exact including case; enum mappings use declared labels",
                "numeric_comparison": "mathematical value; boolean distinct", "array_order": "preserved"}
    lines = lambda rows: "".join(BASE.serialized(r) + "\n" for r in rows)
    return {"drafts.clean.jsonl": lines(sorted(clean, key=lambda d: d["task_id"])),
            "pairs.jsonl": lines(pairs), "catalogs.jsonl": lines(cats[t] for t in sorted(cats)),
            "SYSTEM_POLICY.txt": policy,
            "source-pool-probe.json": json.dumps(probe, indent=2, sort_keys=True) + "\n",
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
        print("PASS: v0.3 authoring artifacts; no test approval")
        return
    if args.check or args.out is None:
        parser.error("Review commands require --out and do not support --check")
    _, clean, pool, schemas, cats, _, policy = load()
    if args.command == "export-review":
        packet = previous.packet(clean, pool, schemas, cats, policy)
        with zipfile.ZipFile(args.out, "x", compression=zipfile.ZIP_DEFLATED) as z:
            for name, text in {"tasks.jsonl": "".join(BASE.serialized(r) + "\n" for r in packet),
                               "SYSTEM_POLICY.txt": policy,
                               "REVIEW_INSTRUCTIONS.md": (DATA / "FRESH_REVIEW_INSTRUCTIONS.md").read_text()}.items():
                info = zipfile.ZipInfo(name, date_time=(2026, 11, 25, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, text)
    else:
        if args.responses is None or not args.reviewer:
            parser.error("check-review requires --responses and --reviewer")
        result = previous.compare_review(clean, pool, schemas, cats, BASE.read_rows(args.responses), args.reviewer)
        with args.out.open("x") as stream:
            stream.write(BASE.serialized(result) + "\n")
    print("Wrote " + str(args.out) + "; no model work or approval")


if __name__ == "__main__":
    main()
