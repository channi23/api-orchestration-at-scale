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
    c5 = pilot.checked(bundle / "sealed/tasks.c5.jsonl", m["tasks_c5_sha256"])
    if pilot.base.digest(visible) != m["visible_tasks_sha256"]:
        raise ValueError("Visible task bytes changed")
    return {5: pilot.rows_by_id(c5), 20: pilot.rows_by_id(visible)}, m


def prompt_token_budget(bundle, tokenizer_path, follow_up=None, *, compact=False):
    from jinja2 import Environment
    from tokenizers import Tokenizer

    pilot.checked(tokenizer_path, TOKENIZER_SHA256)
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    template = json.loads(pilot.SOURCE_TEMPLATE.read_text())["server_props"]["chat_template"]
    jinja = Environment(trim_blocks=True, lstrip_blocks=True).from_string(template)

    def count(task, compact_catalog=False):
        messages = pilot.messages(task)
        if compact_catalog:
            serialized = json.dumps(task["tools"], ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False)
            messages[0]["content"] = task["system_policy"] + "\n\nAvailable tools (JSON):\n" + serialized
        prompt = jinja.render(messages=messages, add_generation_prompt=True, enable_thinking=False)
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

    rows, _ = payloads(bundle)
    if follow_up is not None:
        revised, changes = payloads(follow_up)
        if pilot.provenance.file_sha(bundle / "sealed/manifest.json") != changes["parent_manifest_sha256"]:
            raise ValueError("Follow-up does not match the supplied parent bundle")
        for catalog in rows:
            for change in changes["changes"]:
                rows[catalog][change["parent_task_id"]] = revised[catalog][change["task_id"]]
    grouped = defaultdict(list)
    for catalog, tasks in rows.items():
        for task in tasks.values():
            if catalog == 5 and len(task["tools"]) == 1:
                continue
            grouped[len(task["tools"])].append(count(task, compact_catalog=compact))

    profile = json.loads(pilot.PROFILE.read_text())
    size = int(profile["server_args"][profile["server_args"].index("-c") + 1])
    reserve = profile["request_params"]["max_tokens"]
    return {
        "online_calibration_counts_matched": calibrated,
        "catalog_serialization": "compact" if compact else "readable",
        "tokenizer_sha256": TOKENIZER_SHA256,
        "template_sha256": pilot.provenance.digest(template),
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
    args = parser.parse_args()
    result = prompt_token_budget(args.bundle, args.tokenizer, args.follow_up, compact=args.compact)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
