"""Version reviewed wording and expected calls without changing original schemas."""

import argparse
import json
from pathlib import Path
from zipfile import ZipFile

from . import v2_authoring as common, v2_holdout_batch as batch


STEM = "v2-holdout-candidate-b-v0.2"


def replace(tasks, small, answers, edits, intents):
    changed, small_changed, gold, evidence = [], [], [], []
    edited = {}
    for edit in edits:
        if set(edit) != {"parent_task_id", "request", "arguments", "reason"}:
            raise ValueError("A revision can change the request and expected arguments only")
        key = edit["parent_task_id"]
        original, original_small, expected = tasks[key], small[key], answers[key]
        if key in edited or original["request"] == edit["request"]:
            raise ValueError("Repeated task or unchanged request")
        edited[key] = edit["request"]
        selected, = (tool for tool in original["tools"] if tool["name"] == expected["tool"])
        common.validator(selected["parameters"]).validate(edit["arguments"])
        revised_id = "V2HCBR_" + common.digest(f"{STEM}\0{key}".encode())[:16]
        changed.append({**original, "task_id": revised_id, "request": edit["request"]})
        small_changed.append({**original_small, "task_id": revised_id, "request": edit["request"]})
        gold.append({**expected, "task_id": revised_id, "arguments": edit["arguments"]})
        evidence.append({"parent_task_id": key, "task_id": revised_id, "reason": edit["reason"],
                         "arguments_changed": not common.argument_equal(expected["arguments"], edit["arguments"])})
    updated = dict(zip((row["parent_task_id"] for row in evidence), gold, strict=True))
    for group in intents:
        keys = group["task_ids"]
        requests = {edited.get(key, tasks[key]["request"]) for key in keys}
        if len(requests) != 1:
            raise ValueError("A revised schema pair must share one request")
        if len(keys) == 2 and any(key in edited for key in keys):
            original_validators = [common.validator(tasks[key]["tools"][0]["parameters"]) for key in keys]
            matrix = [validator.is_valid(updated[key]["arguments"])
                      for key in keys for validator in original_validators]
            if matrix != group["cross_validity"]:
                raise ValueError("Revised schema pair must preserve its cross-validity matrix")
    return changed, small_changed, gold, evidence


def build(parent, expected_hash, revisions):
    manifest_bytes = (parent / "sealed/manifest.json").read_bytes()
    if common.digest(manifest_bytes) != expected_hash:
        raise ValueError("Parent manifest SHA-256 mismatch")
    m = json.loads(manifest_bytes)
    packet = parent / "review" / f"{batch.RUN}-blind-review.zip"
    gold = parent / "sealed/gold.jsonl"
    small = parent / "sealed/tasks.c5.jsonl"
    for path, key in ((packet, "review_zip_sha256"), (gold, "gold_sha256"), (small, "tasks_c5_sha256")):
        if common.digest(path.read_bytes()) != m[key]:
            raise ValueError(f"Parent artifact SHA-256 mismatch: {path.name}")
    with ZipFile(packet) as archive:
        rows = [common.strict_loads(line) for line in archive.read("tasks.jsonl").decode().splitlines()]
        notices = {source["notice"]["file"]: archive.read(source["notice"]["file"]) for source in m["sources"]}
    tasks = {row["task_id"]: row for row in rows}
    changed, reduced, answers, edits = replace(
        tasks, {row["task_id"]: row for row in common.read_rows(small)},
        {row["task_id"]: row for row in common.read_rows(gold)}, common.read_rows(revisions), m["intents"]
    )
    summary = {"approved_test_intents": 0, "new_candidate_intents": 0, "revised_rows": len(edits),
               "gold_changes": sum(row["arguments_changed"] for row in edits),
               "status": "private follow-up review candidate"}
    sealed = {"summary": summary, "sources": m["sources"], "parent_manifest_sha256": expected_hash,
              "revision_input_sha256": common.digest(revisions.read_bytes()), "changes": edits}
    return changed, reduced, answers, notices, sealed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--parent-sha256", required=True)
    parser.add_argument("--revisions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(batch.emit(args.out, *build(args.parent, args.parent_sha256, args.revisions),
                                stem=STEM), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
