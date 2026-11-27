"""Score a complete exploratory baseline offline against its frozen contracts."""

import argparse
from collections import Counter, defaultdict
from importlib.metadata import version
import json
from pathlib import Path
from statistics import mean

from . import v2_dev_pilot as pilot


def omission_flags(visible, gold, content):
    schema = next(tool["parameters"] for tool in visible["tools"] if tool["name"] == gold["tool"])
    properties = schema.get("properties", {})
    actual = pilot.router.strict_loads(content)["arguments"]
    missing = sorted(gold["arguments"].keys() - actual.keys())
    default_matches = [key for key in missing
                       if "default" in properties.get(key, {})
                       and pilot.base.argument_equal(properties[key]["default"], gold["arguments"][key])]
    return {"omitted_expected_keys": missing, "omitted_keys_matching_schema_default": default_matches}


def summarize(rows):
    return {"requests": len(rows), "right_tool": sum(row["right_tool"] for row in rows),
            "schema_valid_for_emitted_tool": sum(row["schema_valid"] for row in rows),
            "right_tool_and_schema_valid": sum(row["right_tool"] and row["schema_valid"] for row in rows),
            "exact_calls": sum(row["outcome"] == "correct" for row in rows),
            "valid_calls_omitting_expected_keys": sum(bool(row.get("omitted_expected_keys")) for row in rows),
            "valid_calls_omitting_keys_matching_schema_default": sum(
                bool(row.get("omitted_keys_matching_schema_default")) for row in rows),
            "outcomes": dict(Counter(row["outcome"] for row in rows))}


def report(inputs, answers, responses):
    ordered = [row["request_id"] for row in inputs]
    if len(ordered) != len(set(ordered)) or any(
        [row["request_id"] for row in sequence] != ordered for sequence in (answers, responses)
    ):
        raise ValueError("Scoring requires complete, unique responses in the frozen request order")

    details, tracks = [], defaultdict(lambda: defaultdict(list))
    for task, gold, response in zip(inputs, answers, responses, strict=True):
        if response["finish_reason"] not in {"stop", "length"} or not isinstance(response["content"], str):
            raise ValueError("Unexpected response envelope or finish reason")
        if gold["catalog_size"] != len(task["tools"]):
            raise ValueError("Scoring catalog does not match the inference input")
        score = pilot.score({"visible": task, "gold": gold}, response["content"], response["finish_reason"])
        row = {"request_id": task["request_id"], "track": gold["track"], "catalog_size": gold["catalog_size"],
               "outcome": score["outcome"], "right_tool": score.get("tool_matches", False),
               "schema_valid": score.get("schema_valid", False)}
        if row["outcome"] == "valid_wrong_arguments":
            row.update(omission_flags(task, gold, response["content"]))
        details.append(row)
        tracks[gold["track"]][gold["intent_key"]].append(row)

    by_track = {}
    for track, intents in tracks.items():
        result = {"intents": len(intents), "intent_weighted_exact_accuracy": mean(
            mean(row["outcome"] == "correct" for row in group) for group in intents.values())}
        if track != "api":
            if any(len(group) != 2 for group in intents.values()):
                raise ValueError("Stress intents require both paired variants")
            result["both_variants_exact"] = sum(
                all(row["outcome"] == "correct" for row in group) for group in intents.values())
        by_track[track] = result

    api = tracks.get("api", {})
    matched = [group for group in api.values() if sorted(row["catalog_size"] for row in group) == [5, 20]]
    return {
        "scope": "exploratory, descriptive",
        "by_catalog_size": {str(size): summarize([r for r in details if r["catalog_size"] == size])
                            for size in sorted({row["catalog_size"] for row in details})},
        "by_track": by_track,
        "matched_api_catalogs": {"intents": len(matched), "exact_by_size": {
            str(size): sum(row["outcome"] == "correct" for group in matched for row in group
                           if row["catalog_size"] == size) for size in (5, 20)}},
        "tasks": details,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--responses", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    m = json.loads(pilot.checked(args.freeze / "manifest.json", args.manifest_sha256))
    if version("jsonschema") != m["jsonschema_version"]:
        raise ValueError("Validator version differs from the frozen contract")
    for path in (Path(__file__), Path(pilot.__file__), Path(pilot.base.__file__), Path(pilot.router.__file__)):
        pilot.checked(path, m["implementation_sha256"][path.name])
    inputs, answers = ([pilot.base.strict_loads(line) for line in
                        pilot.checked(args.freeze / path, m["file_sha256"][path]).decode().splitlines()]
                       for path in ("inference/requests.jsonl", "scoring/expected.jsonl"))
    if len(inputs) != m["requests"]:
        raise ValueError("Frozen request count differs from the manifest")
    result = report(inputs, answers, pilot.base.read_rows(args.responses))
    with args.out.open("xb") as stream:
        stream.write(pilot.encode(result))


if __name__ == "__main__":
    main()
