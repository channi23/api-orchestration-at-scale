"""Compare frozen first-solve artifacts with private expected answers."""

import argparse
import json
from pathlib import Path
from zipfile import ZipFile

from . import v2_authoring as common, v2_dev_pilot as pilot


def compare(bundle, answers, notes):
    manifest = json.loads((bundle / "sealed/manifest.json").read_text())
    packet, = (bundle / "review").glob("*.zip")
    pilot.checked(packet, manifest["review_zip_sha256"])
    with ZipFile(packet) as archive:
        tasks = pilot.rows_by_id(archive.read("tasks.jsonl"))
    gold = pilot.rows_by_id(pilot.checked(bundle / "sealed/gold.jsonl", manifest["gold_sha256"]))
    first = pilot.rows_by_id(b"\n".join(path.read_bytes() for path in answers))
    if tasks.keys() != first.keys() or tasks.keys() != gold.keys():
        raise ValueError("Expected one frozen answer for every reviewed row")
    details = []
    for task_id, task in tasks.items():
        actual, target = first[task_id], gold[task_id]
        if set(actual) != {"task_id", "tool", "arguments"} or not isinstance(actual["tool"], str):
            raise ValueError("Unexpected review answer fields")
        schemas = {tool["name"]: tool["parameters"] for tool in task["tools"]}
        chosen = actual["tool"]
        valid = chosen in schemas and common.validator(schemas[chosen]).is_valid(actual["arguments"])
        correct_tool = chosen == target["tool"]
        details.append({"task_id": task_id, "valid": valid, "tool_match": correct_tool,
                        "exact": correct_tool and common.argument_equal(actual["arguments"], target["arguments"])})
    return {"rows": len(details), "valid_arguments": sum(row["valid"] for row in details),
            "tool_matches": sum(row["tool_match"] for row in details), "exact_calls": sum(row["exact"] for row in details),
            "approved_test_intents": 0,
            "artifact_sha256": {p.name: pilot.provenance.file_sha(p) for p in (*answers, *notes, packet, bundle / "sealed/manifest.json")},
            "tasks": details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--answers", type=Path, action="append", required=True)
    parser.add_argument("--notes", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.bundle, args.answers, args.notes)
    with args.out.open("xb") as stream:
        stream.write(pilot.encode(report))
    print({k: report[k] for k in ("rows", "valid_arguments", "tool_matches", "exact_calls")})


if __name__ == "__main__":
    main()
