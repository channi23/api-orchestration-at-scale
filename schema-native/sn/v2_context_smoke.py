"""Verify a separate 9,216-token runtime profile on synthetic development inputs."""

import argparse
from copy import deepcopy
import json
from pathlib import Path

from . import v2_dev_pilot as pilot, v2_holdout_budget


CONTEXTS = (8192, 9216)
PROFILES = {
    8192: pilot.PROFILE,
    9216: pilot.ROOT / "configs/model.qwen3-1.7b.v2-context-9216.json",
}


def config_path(context):
    return pilot.ROOT / f"configs/runs/v2_context_{context}_smoke.json"


def files(context):
    return (Path(__file__), PROFILES[context], Path(v2_holdout_budget.__file__))


def profiles():
    models = {}
    for n in CONTEXTS:
        cfg = json.loads(config_path(n).read_text())
        models[n] = json.loads(pilot.checked(PROFILES[n], cfg["profile_sha256"]))
    expected = deepcopy(models[8192])
    args = expected["server_args"]
    args[args.index("-c") + 1] = "9216"
    metadata = {"label", "notes", "resource_changes"}
    if {k: v for k, v in expected.items() if k not in metadata} != {
        k: v for k, v in models[9216].items() if k not in metadata
    }:
        raise ValueError("Candidate changes runtime settings beyond context")
    return models


def development_unit(name, label, repeat):
    target = {
        "name": "read_archive_certificate",
        "description": "Read exactly one certificate from the municipal archive.",
        "parameters": {"type": "object", "properties": {"id": {"type": "string"},
                        "view": {"type": "string", "enum": ["plain", "summary"]}},
                       "required": ["id", "view"], "additionalProperties": False},
    }
    tools = []
    for index in range(1, 20):
        tags = ", ".join(f"shelf-{index:02d}-{code:03d}" for code in range(repeat))
        description = f"List catalogued holdings for library branch {index:02d}."
        if tags:
            description += f" Internal shelf reference examples for this branch are {tags}."
        tools.append({
            "name": f"list_library_branch_{index:02d}",
            "description": description,
            "parameters": {"type": "object", "properties": {
                "section": {"type": "string"}, "page": {"type": "integer", "minimum": 1},
                "genre": {"type": "string", "enum": ["history", "design", "music"]}},
                "additionalProperties": False},
        })
    tools.insert(9, target)
    return {
        "task_id": name,
        "visible": {
            "catalog_serialization": "compact", "tools": tools,
            "system_policy": 'Return exactly one JSON object with keys "tool" and "arguments". '
                             "Use the offered schemas and omit unrequested arguments. Return only the JSON.",
            "request": f"Read certificate {label} from the municipal archive in plain view.",
        },
        "gold": {"tool": target["name"], "arguments": {"id": label, "view": "plain"}},
    }


def planned_units(count):
    short = development_unit("shared_short", "AR-519", 0)
    long_units = []
    for name, label, desired in (("shared_long", "AR-864", 7350), ("extended_long", "AR-387", 8250)):
        # Increase the amount of synthetic catalog text to reach predetermined test lengths.
        low, high = 0, 256
        while low < high:
            middle = (low + high) // 2
            if count(development_unit(name, label, middle)["visible"]) < desired:
                low = middle + 1
            else:
                high = middle
        unit = development_unit(name, label, low)
        observed = count(unit["visible"])
        if not desired <= observed < desired + 180:
            raise ValueError(f"Calibration did not reach the expected token band: {name}")
        long_units.append(unit)
    return [short, *long_units]


def build_plans(tokenizer_file):
    from jinja2 import Environment
    from tokenizers import Tokenizer

    pilot.checked(tokenizer_file, v2_holdout_budget.TOKENIZER_SHA256)
    tokenizer = Tokenizer.from_file(str(tokenizer_file))
    template = json.loads(pilot.SOURCE_TEMPLATE.read_text())["server_props"]["chat_template"]
    jinja = Environment(trim_blocks=True, lstrip_blocks=True).from_string(template)

    def count(task):
        prompt = jinja.render(messages=pilot.messages(task), add_generation_prompt=True, enable_thinking=False)
        return len(tokenizer.encode(prompt, add_special_tokens=False).ids)

    models = profiles()
    all_units = planned_units(count)
    token_counts = {u["task_id"]: count(u["visible"]) for u in all_units}
    runtime = pilot.preflight.runtime(models[8192], str(pilot.model_path(models[8192])), str(pilot.LLAMA))
    plans = {}
    for context in CONTEXTS:
        config = config_path(context)
        cfg = json.loads(config.read_text())
        profile = models[context]
        # The reference receives the same two inputs as the candidate. Only the candidate gets the extended input.
        units = all_units[:2] if context == 8192 else all_units
        counts = {u["task_id"]: token_counts[u["task_id"]] for u in units}
        if len(units) != cfg["generation_cap"] or max(counts.values()) + profile["request_params"]["max_tokens"] > context:
            raise ValueError("Input roster exceeds the locked request or context limit")
        plans[context] = {"config": cfg, "profile": profile, "units": units,
                          "implementation_sha256": pilot.implementation(config, files(context)),
                          "template_sha256": pilot.provenance.digest(template), "runtime": runtime,
                          "expected_prompt_tokens": counts,
                          "tokenizer_sha256": v2_holdout_budget.TOKENIZER_SHA256}
    return plans


def require_completed_reference():
    cfg = json.loads(config_path(8192).read_text())
    directory = Path(pilot.paths.RUNS) / cfg["run_id"]
    if not (directory / "report.json").is_file() or (directory / "STOPPED.json").exists():
        raise ValueError("The separate 8,192-token reference must complete first")
    if pilot.port_open(cfg["port"]):
        raise ValueError("The 8,192-token server is still listening")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run"))
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--plan-dir", type=Path, required=True)
    parser.add_argument("--context", type=int, choices=CONTEXTS)
    parser.add_argument("--approved-plan-sha256")
    args = parser.parse_args()
    plans = build_plans(args.tokenizer)
    if args.command == "prepare":
        args.plan_dir.mkdir(mode=0o700)
        for context, plan in plans.items():
            data = pilot.encode(plan)
            name = f"context-{context}.json"
            with (args.plan_dir / name).open("xb") as stream:
                stream.write(data)
            print(context, pilot.base.digest(data), plan["expected_prompt_tokens"])
        return

    if args.context is None or args.approved_plan_sha256 is None:
        parser.error("run requires the context and locked plan SHA-256")
    context = args.context
    plan_file = args.plan_dir / f"context-{context}.json"
    sealed = pilot.checked(plan_file, args.approved_plan_sha256)
    if sealed != pilot.encode(plans[context]):
        raise ValueError("Prepared context smoke inputs or implementation changed")
    if context == 9216:
        require_completed_reference()
    pilot.launch(json.loads(sealed), config_path=config_path(context),
                 profile_path=PROFILES[context], extra_files=files(context))


if __name__ == "__main__":
    main()
