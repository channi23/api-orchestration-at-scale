"""Prepare a private three-case revision from the verified first holdout packet."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from . import v2_holdout as first


BASE = first.BASE
STEM = "v2-holdout-candidate-a-v0.2"
PARENT_MANIFEST_SHA256 = "638622cfb4461c92bda7641b5f57b0855efc32b0d78aec56c6cd87e7d14e882d"


def build(parent, revision_file):
    manifest_bytes = (parent / "sealed/manifest.json").read_bytes()
    if BASE.digest(manifest_bytes) != PARENT_MANIFEST_SHA256:
        raise ValueError("The first candidate manifest does not match the original pin")
    manifest = json.loads(manifest_bytes)
    source_review = parent / "review/v2-holdout-candidate-a-v0.1-blind-review.zip"
    source_gold = parent / "sealed/gold.jsonl"
    if BASE.digest(source_review.read_bytes()) != manifest["review_zip_sha256"]:
        raise ValueError("The original review packet has changed")
    if BASE.digest(source_gold.read_bytes()) != manifest["gold_sha256"]:
        raise ValueError("The original gold has changed")
    with ZipFile(source_review) as archive:
        rows = [BASE.strict_loads(line) for line in archive.read("tasks.jsonl").decode().splitlines()]
        notices = {item["notice"]["file"]: archive.read(item["notice"]["file"])
                   for item in manifest["sources"]}
    tasks_by_id = {task["task_id"]: task for task in rows}
    gold_by_id = {row["task_id"]: row for row in BASE.read_rows(source_gold)}
    provenance_by_id = {row["task_id"]: row for row in manifest["tasks"]}
    revisions = BASE.read_rows(revision_file)
    if len(revisions) != 3:
        raise ValueError("This tranche revises three cases")
    seen, tasks, gold, changes = set(), [], [], []
    for edit in revisions:
        if set(edit) != {"parent_task_id", "request", "arguments", "reason"}:
            raise ValueError("A revision can change the request and its expected arguments only")
        parent_id = edit["parent_task_id"]
        if parent_id in seen or parent_id not in tasks_by_id:
            raise ValueError("Unknown or repeated parent task")
        seen.add(parent_id)
        task = tasks_by_id[parent_id]
        old_gold = gold_by_id[parent_id]
        tool = next(tool for tool in task["tools"] if tool["name"] == old_gold["tool"])
        if edit["request"] == task["request"]:
            raise ValueError("The revised request must differ from the original")
        if not BASE.validator(tool["parameters"]).is_valid(edit["arguments"]):
            raise ValueError(f"The revised gold violates the supplied schema: {parent_id}")
        task_id = "V2HCR_" + BASE.digest(f"{STEM}\0{parent_id}".encode())[:12]
        tasks.append({**task, "task_id": task_id, "request": edit["request"]})
        gold.append({"task_id": task_id, "tool": old_gold["tool"], "arguments": edit["arguments"]})
        changes.append({
            **{key: provenance_by_id[parent_id][key] for key in ("project", "intent_id")},
            "parent_task_id": parent_id, "task_id": task_id, "reason": edit["reason"],
            "gold_arguments_changed": not BASE.argument_equal(old_gold["arguments"], edit["arguments"]),
        })
    return sorted(tasks, key=lambda row: row["task_id"]), sorted(gold, key=lambda row: row["task_id"]), notices, {
        "status": "private_follow_up_review_pending",
        "approved_test_intents": 0,
        "parent_manifest_sha256": PARENT_MANIFEST_SHA256,
        "revision_input_sha256": BASE.digest(revision_file.read_bytes()),
        "builder_sha256": BASE.digest(Path(__file__).read_bytes()),
        "changes": changes,
    }


def write(destination, tasks, gold, notices, manifest):
    payload = {
        "tasks.jsonl": "".join(BASE.serialized(row) + "\n" for row in tasks).encode(),
        "REVIEW_INSTRUCTIONS.md": first.REVIEW.encode(),
        **notices,
    }
    destination.mkdir(mode=0o700)
    review = destination / "review"
    sealed = destination / "sealed"
    review.mkdir(mode=0o700)
    sealed.mkdir(mode=0o700)
    zip_path = review / f"{STEM}-blind-review.zip"
    with ZipFile(zip_path, "x", compression=ZIP_DEFLATED) as output:
        for name, content in payload.items():
            info = ZipInfo(name, date_time=(2026, 11, 25, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            output.writestr(info, content)
    gold_bytes = "".join(BASE.serialized(row) + "\n" for row in gold).encode()
    (sealed / "gold.jsonl").write_bytes(gold_bytes)
    (sealed / "manifest.json").write_text(json.dumps({
        **manifest, "review_zip_sha256": BASE.digest(zip_path.read_bytes()),
        "gold_sha256": BASE.digest(gold_bytes),
    }, sort_keys=True, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--revisions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    write(args.out, *build(args.parent, args.revisions))
    print("PASS: rendered three private revisions with separate gold")


if __name__ == "__main__":
    main()
