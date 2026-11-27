"""Measure prompt lengths on private candidates using tokenizer assets only."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
from zipfile import ZipFile

from . import v2_dev_pilot as pilot


TOKENIZER_SHA256 = "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"
CALIBRATIONS = ("v2-keyword-control-v0.1", "v2-keyword-repairs-v0.1")


def payloads(bundle):
    m = json.loads((bundle / "sealed/manifest.json").read_text())
    packet, = (bundle / "review").glob("*.zip")
    pilot.checked(packet, m["review_zip_sha256"])
    with ZipFile(packet) as archive:
        visible = archive.read("tasks.jsonl")
    rows = pilot.rows_by_id(visible)
    if "tasks_c5_sha256" not in m:
        # Earlier packets carry only a five-tool view, pinned by the review ZIP.
        if any(len(task["tools"]) != 5 for task in rows.values()):
            raise ValueError("Expected the legacy five-tool packet")
        return {5: rows, 20: {}}, m
    c5 = pilot.checked(bundle / "sealed/tasks.c5.jsonl", m["tasks_c5_sha256"])
    if pilot.base.digest(visible) != m["visible_tasks_sha256"]:
        raise ValueError("Visible task bytes changed")
    return {5: pilot.rows_by_id(c5), 20: rows}, m


def calibrated_counter(tokenizer_path):
    from jinja2 import Environment
    from tokenizers import Tokenizer

    pilot.checked(tokenizer_path, TOKENIZER_SHA256)
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    template = json.loads(pilot.SOURCE_TEMPLATE.read_text())["server_props"]["chat_template"]
    jinja = Environment(trim_blocks=True, lstrip_blocks=True).from_string(template)

    def count(task, compact_catalog=False):
        visible = {**task, "catalog_serialization": "compact"} if compact_catalog else task
        prompt = jinja.render(messages=pilot.messages(visible), add_generation_prompt=True, enable_thinking=False)
        return len(tokenizer.encode(prompt, add_special_tokens=False).ids)

    calibrated = 0
    for name in CALIBRATIONS:
        run = Path(pilot.paths.RUNS) / name
        manifest = json.loads((run / "manifest.json").read_text())
        preflight = json.loads((run / "preflight.json").read_text())
        if manifest["template_sha256"] != pilot.provenance.digest(template):
            raise ValueError("Calibration run used a different chat template")
        if {u["task_id"]: count(u["visible"]) for u in manifest["units"]} != preflight["prompt_tokens"]:
            raise ValueError("Tokenizer reproducer disagrees with the saved online preflight")
        calibrated += len(preflight["prompt_tokens"])
    return count, calibrated, pilot.provenance.digest(template)


def prompt_token_budget(bundle, tokenizer_path, follow_up=None, *, compact=False, profile_path=None):
    count, calibrated, template_sha256 = calibrated_counter(tokenizer_path)
    rows, _ = payloads(bundle)
    if follow_up is not None:
        revised, changes = payloads(follow_up)
        if pilot.provenance.file_sha(bundle / "sealed/manifest.json") != changes["parent_manifest_sha256"]:
            raise ValueError("Follow-up does not match the supplied parent bundle")
        for change in changes["changes"]:
            parent_id, new_id = change["parent_task_id"], change["task_id"]
            catalogs = [size for size in rows if parent_id in rows[size]]
            if not catalogs or any(new_id not in revised[size] for size in catalogs):
                raise ValueError("Follow-up revision must cover every original catalog view")
            for size in catalogs:
                rows[size][parent_id] = revised[size][new_id]
    grouped = defaultdict(list)
    for catalog, tasks in rows.items():
        for task in tasks.values():
            if catalog == 5 and len(task["tools"]) == 1:
                continue
            grouped[len(task["tools"])].append(count(task, compact_catalog=compact))

    profile = json.loads((profile_path or pilot.PROFILE).read_text())
    size = int(profile["server_args"][profile["server_args"].index("-c") + 1])
    reserve = profile["request_params"]["max_tokens"]
    return {
        "online_calibration_counts_matched": calibrated,
        "catalog_serialization": "compact" if compact else "readable",
        "tokenizer_sha256": TOKENIZER_SHA256,
        "template_sha256": template_sha256,
        "context_tokens": size,
        "output_reserve_tokens": reserve,
        "by_catalog_size": {str(n): {"rows": len(values), "prompt_min": min(values), "prompt_max": max(values),
                                    "overflow": sum(value + reserve > size for value in values)}
                            for n, values in sorted(grouped.items())},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--follow-up", type=Path)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--profile", type=Path, help="Profile used to calculate the offline prompt limit")
    args = parser.parse_args()
    result = prompt_token_budget(args.bundle, args.tokenizer, args.follow_up,
                                 compact=args.compact, profile_path=args.profile)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
