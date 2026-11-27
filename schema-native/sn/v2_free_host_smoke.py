"""Export the three synthetic context-smoke prompts for a separate free CPU host."""

import argparse
import json
from pathlib import Path

from . import v2_dev_pilot as pilot, v2_exploratory_export as export


SMOKE_PLAN_SHA256 = "c1c39caf261032567c1038357b949f3e8767abf7b60760f4d09e21f51e5eb600"


def build(source):
    smoke = json.loads(pilot.checked(source, SMOKE_PLAN_SHA256))
    pilot.checked(Path(pilot.__file__), smoke["implementation_sha256"]["sn/v2_dev_pilot.py"])
    profile = smoke["profile"]
    args = profile["server_args"].copy()
    args[args.index("-ngl") + 1] = "0"
    args.extend(["-t", "2", "-tb", "2"])
    counts = smoke["expected_prompt_tokens"]
    if len(smoke["units"]) != 3 or len(counts) != 3:
        raise ValueError("Unexpected synthetic smoke roster")
    requests = [
        {"request_id": unit["task_id"], "expected_prompt_tokens": counts[unit["task_id"]],
         "payload": pilot.payload(smoke, unit["visible"])}
        for unit in smoke["units"]
    ]
    raw = "".join(pilot.base.serialized(row) + "\n" for row in requests).encode()
    manifest = {
        "export_id": "v2-free-cpu-host-smoke-v0.1",
        "scope": "synthetic development smoke",
        "backend": "linux-arm64-cpu",
        "source_smoke_plan_sha256": SMOKE_PLAN_SHA256,
        "llama_cpp_commit": profile["llama_cpp_commit"],
        "gguf_file": profile["gguf_file"],
        "gguf_sha256": profile["gguf_sha256"],
        "hf_repo_gguf": profile["hf_repo_gguf"],
        "hf_revision_gguf": profile["hf_revision_gguf"],
        "template_sha256": smoke["template_sha256"],
        "server_args": args,
        "context_tokens": 9216,
        "output_reserve_tokens": profile["request_params"]["max_tokens"],
        "generation_cap": len(requests),
        "metadata_cap": 1 + 2 * len(requests),
        "payloads_sha256": pilot.base.digest(raw),
    }
    return {"manifest.json": pilot.encode(manifest), "requests.jsonl": raw}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "check"))
    parser.add_argument("--smoke-plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    artifacts = build(args.smoke_plan)
    export.write(args.out, artifacts, verify=args.command == "check")
    print(pilot.base.digest(artifacts["manifest.json"]))


if __name__ == "__main__":
    main()
