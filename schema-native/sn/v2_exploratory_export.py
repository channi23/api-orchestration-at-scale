"""Stage inference-only requests for an approved host without accessing the answer key."""

import argparse
import json
from pathlib import Path

from . import v2_dev_pilot as pilot


PROFILE = pilot.ROOT / "configs/model.qwen3-1.7b.v2-context-9216.json"
VISIBLE_FIELDS = {"request_id", "task_id", "request", "system_policy", "tools",
                  "catalog_serialization", "prompt_tokens"}


def inference_payloads(rows, profile, freeze):
    if len(rows) != freeze["requests"] or len({row["request_id"] for row in rows}) != len(rows):
        raise ValueError("Unexpected frozen request roster")
    reserve = profile["request_params"]["max_tokens"]
    context = int(profile["server_args"][profile["server_args"].index("-c") + 1])
    if (context, reserve) != (freeze["context_tokens"], freeze["output_reserve_tokens"]):
        raise ValueError("Profile differs from the frozen context policy")
    for row in rows:
        if set(row) != VISIBLE_FIELDS or row["catalog_serialization"] != "compact":
            raise ValueError("Only frozen visible fields and compact serialization are allowed")
        size = row["prompt_tokens"]
        if type(size) is not int or not 0 < size <= context - reserve:
            raise ValueError("Frozen prompt exceeds context or has an invalid token count")
        yield {"request_id": row["request_id"], "expected_prompt_tokens": size,
               "payload": pilot.payload({"profile": profile, "config": {"cache_prompt": False}}, row)}


def prepare(freeze_manifest, manifest_sha, visible_file):
    freeze = json.loads(pilot.checked(freeze_manifest, manifest_sha))
    if freeze["freeze_id"] != "v2-exploratory-freeze-v0.1" or freeze["requests"] != 177:
        raise ValueError("Unexpected exploratory freeze")
    pilot.checked(Path(pilot.__file__), freeze["implementation_sha256"]["v2_dev_pilot.py"])
    raw = pilot.checked(visible_file, freeze["file_sha256"]["inference/requests.jsonl"])
    rows = [pilot.base.strict_loads(line) for line in raw.decode().splitlines()]
    profile = json.loads(pilot.checked(PROFILE, freeze["profile_sha256"]))
    payloads = list(inference_payloads(rows, profile, freeze))
    visible = "".join(pilot.base.serialized(row) + "\n" for row in payloads).encode()
    manifest = {
        "export_id": "v2-exploratory-free-inference-v0.1",
        "freeze_manifest_sha256": manifest_sha,
        "frozen_visible_requests_sha256": freeze["file_sha256"]["inference/requests.jsonl"],
        "profile_sha256": freeze["profile_sha256"],
        "template_sha256": freeze["template_sha256"],
        "gguf_sha256": profile["gguf_sha256"],
        "gguf_file": profile["gguf_file"],
        "llama_cpp_commit": profile["llama_cpp_commit"],
        "server_args": profile["server_args"],
        "context_tokens": freeze["context_tokens"],
        "output_reserve_tokens": freeze["output_reserve_tokens"],
        "generation_cap": len(payloads),
        "planned_first_preflight_metadata_calls": 1 + 2 * len(payloads),
        "catalog_cache_prompt": False,
        "payloads_sha256": pilot.base.digest(visible),
    }
    return {"requests.jsonl": visible, "manifest.json": pilot.encode(manifest)}


def write(out, artifacts, verify):
    if verify:
        for name, data in artifacts.items():
            if (out / name).read_bytes() != data:
                raise ValueError(f"Inference export differs: {name}")
        return
    out.mkdir(mode=0o700)
    for name, data in artifacts.items():
        with (out / name).open("xb") as stream:
            stream.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "check"))
    parser.add_argument("--freeze-manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--inference-requests", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    artifacts = prepare(args.freeze_manifest, args.manifest_sha256, args.inference_requests)
    write(args.out, artifacts, args.command == "check")
    print(pilot.base.digest(artifacts["manifest.json"]))


if __name__ == "__main__":
    main()
