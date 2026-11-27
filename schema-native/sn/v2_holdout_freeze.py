"""Seal the reviewed exploratory dataset without loading a model."""

import argparse
from collections import Counter, defaultdict
from importlib.metadata import version
import json
from pathlib import Path

from . import v2_dev_pilot as pilot, v2_holdout_budget as budget, v2_holdout_review as review


FREEZE_ID = "v2-exploratory-freeze-v0.1"
READINESS_SHA = "d4886721ee0e8ad21f0d18a44fc11df4d4c4b5d908136a2f76358602a5cc069b"
WORDING_SHA = "e4a9279ccf6b88517c967d6c98ccccf94cc2706eaf8b7de13a12ebb74653e856"
A_ADJUDICATION_SHA = {
    "original": "f04ae5afe5db4464172ccb2c1b4f53ebffc6d28ad49d005456e2f64de2d9136e",
    "follow_up": "704c1e2699b22b50a8d4cf19e7dc20b1886c04bea8bcb0ce5a66ee5de4d83489",
}
PROFILE = pilot.ROOT / "configs/model.qwen3-1.7b.v2-context-9216.json"
ORDER_SEED = "v2-exploratory-20261127"
VISIBLE_FIELDS = {"task_id", "request", "system_policy", "tools"}


def encode_rows(rows):
    return "".join(pilot.base.serialized(row) + "\n" for row in rows).encode()


def verify_review(bundle, tranche, stage, artifact):
    if tranche == "a":
        folder = bundle / "review-receipt"
        receipt_path = folder / "adjudication-receipt.json"
        pinned = json.loads(pilot.checked(receipt_path, A_ADJUDICATION_SHA[stage]))
        hashes = pinned.get("verified_original_file_hashes", pinned)
        for name, key, expected in (
            ("answers.jsonl", "answers_sha256", hashes),
            ("REVIEW_NOTES.md", "review_notes_sha256", hashes),
            ("ADJUDICATION.md", "adjudication_sha256", pinned),
            ("comparison.json", "comparison_sha256", pinned),
        ):
            pilot.checked(folder / name, expected[key])
        result = review.compare(bundle, [folder / "answers.jsonl"], [folder / "REVIEW_NOTES.md"])
        if result["exact_calls"] != pinned["exact_matches"]:
            raise ValueError("Earlier adjudication score changed")
        adjudication = A_ADJUDICATION_SHA[stage]
    else:
        folder = bundle / "review"
        if tranche == "c" and stage == "original":
            answers = [folder / f"answers-part{i}.jsonl" for i in (1, 2)]
            notes = [folder / f"REVIEW_NOTES_PART{i}.md" for i in (1, 2)]
        else:
            answers, notes = [folder / "answers.jsonl"], [folder / "REVIEW_NOTES.md"]
        receipt_path = bundle / "sealed/first-solve-comparison.json"
        pinned = json.loads(pilot.checked(receipt_path, artifact["review_comparison_sha256"]))
        result = review.compare(bundle, answers, notes)
        if any(pinned[key] != result[key] for key in ("rows", "exact_calls", "valid_arguments", "tool_matches")):
            raise ValueError("First-solve results no longer reproduce")
        hashes = pinned.get("sha256")
        if hashes is not None and (
            hashes["first_answers"] != pilot.provenance.file_sha(answers[0])
            or hashes["first_notes"] != pilot.provenance.file_sha(notes[0])
        ):
            raise ValueError("First-solve artifacts changed")
        if "tasks" in pinned and (pinned["tasks"] != result["tasks"]
                                  or pinned["artifact_sha256"] != result["artifact_sha256"]):
            raise ValueError("Per-item review evidence changed")
        adjudication = None
    return result, {"receipt_sha256": pilot.provenance.file_sha(receipt_path),
                    "adjudication_receipt_sha256": adjudication,
                    "verified_artifacts_sha256": result["artifact_sha256"]}


def materialize_sources(outputs, readiness):
    views, golds, scores, seals, origins = defaultdict(dict), {}, {}, {}, []
    for tranche, record in readiness["tranches"].items():
        seals[tranche] = {}
        for stage, artifact in record["artifacts"].items():
            bundle = outputs / artifact["bundle"]
            pilot.checked(bundle / "sealed/manifest.json", artifact["manifest_sha256"])
            stage_views, manifest = budget.payloads(bundle)
            if manifest["review_zip_sha256"] != artifact["review_zip_sha256"]:
                raise ValueError("Review packet differs from readiness inventory")
            if stage == "original":
                origins.extend(manifest["sources"])
            result, verified = verify_review(bundle, tranche, stage, artifact)
            seals[tranche][stage] = {**artifact, **verified}
            gold = pilot.rows_by_id(pilot.checked(bundle / "sealed/gold.jsonl", artifact["gold_sha256"]))
            if golds.keys() & gold.keys():
                raise ValueError("Task ID reused across packets")
            golds.update(gold)
            scores.update({row["task_id"]: row for row in result["tasks"]})
            for catalog in stage_views.values():
                for task_id, task in catalog.items():
                    size = len(task["tools"])
                    if size in views[task_id] and views[task_id][size] != task:
                        raise ValueError("Conflicting bytes for a reused catalog view")
                    views[task_id][size] = task
    if len({source["project"] for source in origins}) != 6:
        raise ValueError("Unexpected source group roster")
    return views, golds, scores, seals, origins


def validate_intent(task_views, track):
    view_sizes = [set(views) for views in task_views]
    if track == "api":
        if len(view_sizes) != 1 or view_sizes[0] not in ({5}, {5, 20}):
            raise ValueError("Unexpected catalog sizes for API intent")
        views = task_views[0]
        if 20 in views:
            small, large = views[5], views[20]
            names = {tool["name"] for tool in small["tools"]}
            if {**large, "tools": [t for t in large["tools"] if t["name"] in names]} != small:
                raise ValueError("Five-tool view must be a nested, ordered subset")
    elif (len(view_sizes) != 2 or view_sizes != [{1}, {1}]
          or task_views[0][1]["request"] != task_views[1][1]["request"]):
        raise ValueError("Expected paired one-tool tasks with an identical request")


def build(outputs, tokenizer):
    readiness_path = outputs / "v2-holdout-freeze-readiness-v0.1/manifest.json"
    readiness = json.loads(pilot.checked(readiness_path, READINESS_SHA))
    profile = json.loads(pilot.checked(PROFILE, readiness["profile_sha256"]))
    proposal_path = outputs / "v2-holdout-candidate-a-v0.2-authoring/freeze-wording.jsonl"
    wording = pilot.base.strict_loads(pilot.checked(proposal_path, WORDING_SHA).decode().strip())
    views, golds, scores, seals, origins = materialize_sources(outputs, readiness)
    count, calibration, template_sha = budget.calibrated_counter(tokenizer)

    frozen_inputs, labels, exclusions, intents = {}, {}, [], []
    if version("jsonschema") != "4.26.0":
        raise ValueError("Freeze must use the reviewed jsonschema 4.26.0 validator")
    for item in readiness["roster"]:
        key = f"{item['tranche']}|{item['intent_id']}"
        ids = item["task_ids"]
        if item["disposition"] == "hold_for_lineage_review" or wording["parent_task_id"] in ids:
            reason = item.get("reason", "Pending independent review of exact extension-case wording.")
            exclusions.append({"intent_key": key, "task_ids": ids, "reason": reason})
            continue
        if item["disposition"] != "awaiting_freeze_review":
            raise ValueError("Unknown candidate disposition")
        if any(not scores[task_id]["exact"] or not scores[task_id]["valid"] for task_id in ids):
            raise ValueError("Selected task did not pass the reviewed exact contract")
        validate_intent([views[task_id] for task_id in ids], item["track"])
        group = item["source_group"] or item["family_id"]
        intents.append({"intent_key": key, "task_ids": ids, "track": item["track"], "family": group,
                        "split": "frozen_exploratory"})
        for task_id in ids:
            gold = golds[task_id]
            for size, row in views[task_id].items():
                if set(row) != VISIBLE_FIELDS:
                    raise ValueError("Unexpected inference fields in candidate packet")
                schemas = {tool["name"]: tool["parameters"] for tool in row["tools"]}
                if len(schemas) != size:
                    raise ValueError("Duplicate tool names in candidate catalog")
                pilot.base.validator(schemas[gold["tool"]]).validate(gold["arguments"])
                request_id = f"{task_id}|{size}"
                if request_id in frozen_inputs:
                    raise ValueError("Duplicate frozen request")
                visible = {**row, "catalog_serialization": "compact"}
                frozen_inputs[request_id] = {"request_id": request_id, **visible,
                                             "prompt_tokens": count(visible, compact_catalog=True)}
                labels[request_id] = {"request_id": request_id, "intent_key": key,
                                      "track": item["track"], "catalog_size": size,
                                      "tool": gold["tool"], "arguments": gold["arguments"]}

    order = sorted(frozen_inputs, key=lambda key: pilot.base.digest(f"{ORDER_SEED}\0{key}".encode()))
    inputs = [frozen_inputs[key] for key in order]
    answers = [labels[key] for key in order]
    prompt_max = max(row["prompt_tokens"] for row in inputs)
    args = profile["server_args"]
    context = int(args[args.index("-c") + 1])
    reserve = profile["request_params"]["max_tokens"]
    if context != 9216 or reserve != 512 or prompt_max + reserve > context:
        raise ValueError("Frozen prompt exceeds the smoke-tested context allowance")
    if len(intents) != 93 or len(inputs) != 177 or len(exclusions) != 5:
        raise ValueError("Frozen roster does not match the reviewed selection")

    artifacts = {"inference/requests.jsonl": encode_rows(inputs),
                 "scoring/expected.jsonl": encode_rows(answers),
                 "scoring/lineage.jsonl": encode_rows(intents),
                 "scoring/sources.jsonl": encode_rows(origins),
                 "scoring/exclusions.jsonl": encode_rows(exclusions)}
    manifest = {
        "freeze_id": FREEZE_ID, "date": "2026-11-27", "scope": "exploratory data freeze",
        "campaign_status": "separate campaign review pending", "confirmatory_test_intents": 0,
        "tranche_artifacts": seals, "private_readiness_sha256": READINESS_SHA,
        "wording_proposal_sha256": WORDING_SHA,
        "profile_sha256": readiness["profile_sha256"], "template_sha256": template_sha,
        "tokenizer_sha256": budget.TOKENIZER_SHA256, "online_calibration_counts_matched": calibration,
        "order_seed": ORDER_SEED, "serialization": "compact",
        "intent_counts_by_track": dict(Counter(row["track"] for row in intents)),
        "request_counts_by_catalog_size": dict(Counter(len(row["tools"]) for row in inputs)),
        "source_groups": 6, "intents": len(intents), "requests": len(inputs), "exclusions": len(exclusions),
        "min_prompt_tokens": min(row["prompt_tokens"] for row in inputs),
        "max_prompt_tokens": prompt_max, "context_tokens": context, "output_reserve_tokens": reserve,
        "jsonschema_version": version("jsonschema"),
        "format_policy": "annotations",
        "scoring_policy": "strict JSON object, exact reviewed call and raw-schema validity, per-track intent weighting",
        "tokenizer_version": version("tokenizers"),
        "jinja2_version": version("jinja2"),
        "file_sha256": {path: pilot.base.digest(data) for path, data in artifacts.items()},
        "implementation_sha256": {path.name: pilot.provenance.file_sha(path) for path in (
            Path(__file__), Path(__file__).with_name("v2_holdout_score.py"),
            *(Path(m.__file__) for m in (pilot, pilot.base, pilot.router, budget, review)),
        )},
    }
    return {**artifacts, "manifest.json": pilot.encode(manifest)}


def write(out, artifacts, verify=False):
    if verify:
        for name, data in artifacts.items():
            if (out / name).read_bytes() != data:
                raise ValueError(f"Frozen bytes changed: {name}")
        return
    out.mkdir(mode=0o700)
    for name, data in artifacts.items():
        path = out / name
        path.parent.mkdir(mode=0o700, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "check"))
    parser.add_argument("--outputs", required=True, type=Path)
    parser.add_argument("--tokenizer", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    artifacts = build(args.outputs, args.tokenizer)
    write(args.out, artifacts, verify=args.command == "check")
    manifest = json.loads(artifacts["manifest.json"])
    print(pilot.base.digest(artifacts["manifest.json"]), manifest["intents"], manifest["requests"])


if __name__ == "__main__":
    main()
