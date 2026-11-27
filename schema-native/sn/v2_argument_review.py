"""Run one development-only review of the arguments in each saved first call."""

import argparse
from collections import Counter
import fcntl
from importlib.metadata import version
import json
import os
from pathlib import Path
from statistics import median

from . import v2_dev_pilot as pilot, v2_exploratory_run as runner, v2_holdout_budget as budget


CONFIG = pilot.ROOT / "configs/runs/v2_argument_review.json"
FILES = (Path(__file__), Path(runner.__file__), Path(budget.__file__))
POLICY = (
    "Review the candidate arguments for the supplied tool against the original request. "
    "Keep the tool fixed. Include each requested filter, limit, flag, and other value that "
    "the tool supports, even when it equals a default. Use the tool's declared argument names "
    "and the specified string case and array order. Remove any argument that neither the "
    "request nor an applicable schema requirement supports. Do not guess missing values. "
    "If the arguments already fulfill the request, keep them. "
    "Return only the final JSON argument object, with no tool name, wrapper or commentary."
)


def baseline(config):
    source = runner.RUNS / config["baseline_run"]
    original = json.loads(pilot.checked(source / "manifest.json", config["baseline_manifest_sha256"]))
    first = list(pilot.rows_by_id(pilot.checked(source / "results.jsonl", config["baseline_results_sha256"])).values())
    if [unit["task_id"] for unit in original["units"]] != [row["task_id"] for row in first]:
        raise ValueError("Stored first calls do not match the development roster")
    if len(first) != config["generation_cap"]:
        raise ValueError("Development roster does not match the review request cap")
    return original, first


def review_task(visible, first):
    if first["finish_reason"] != "stop":
        raise ValueError("Argument review requires a completed first call")
    call = pilot.router.strict_loads(first["content"])
    tools = {tool["name"]: tool for tool in visible["tools"]}
    if (not isinstance(call, dict) or set(call) != {"tool", "arguments"}
            or not isinstance(call["tool"], str) or call["tool"] not in tools
            or not isinstance(call["arguments"], dict)):
        raise ValueError("Argument review requires a strict first call to a known tool")
    return {
        "system_policy": POLICY,
        "request": ("Original request:\n" + visible["request"]
                    + "\n\nCandidate arguments (JSON):\n" + pilot.base.serialized(call["arguments"])),
        "tools": [tools[call["tool"]]],
    }


def prepare(config, tokenizer):
    original, first = baseline(config)
    profile = json.loads(pilot.checked(pilot.PROFILE, config["profile_sha256"]))
    if original["profile"] != profile or original["config"]["cache_prompt"] != config["cache_prompt"]:
        raise ValueError("Review must retain the first-pass model profile and cache setting")
    count, calibration, template_sha = budget.calibrated_counter(tokenizer)
    if template_sha != original["template_sha256"]:
        raise ValueError("Review template differs from the original development template")
    context = int(profile["server_args"][profile["server_args"].index("-c") + 1])
    reserve = profile["request_params"]["max_tokens"]
    rows = []
    for unit, response in zip(original["units"], first, strict=True):
        task = review_task(unit["visible"], response)
        tokens = count(task)
        if not 0 < tokens <= context - reserve:
            raise ValueError("Review prompt exceeds the profile's context budget")
        rows.append({"request_id": unit["task_id"], "expected_prompt_tokens": tokens,
                     "payload": pilot.payload({"profile": profile, "config": config}, task)})
    return {
        "config": config, "profile": profile, "runtime": original["runtime"],
        "context_tokens": context, "template_sha256": template_sha,
        "tokenizer_sha256": budget.TOKENIZER_SHA256, "calibration_prompt_counts": calibration,
        "implementation_sha256": pilot.implementation(CONFIG, FILES), "rows": rows,
    }


def score_review(unit, first, reviewed):
    if reviewed["finish_reason"] == "length":
        return {"outcome": "truncated"}
    try:
        arguments = pilot.router.strict_loads(reviewed["content"])
    except (ValueError, TypeError, RecursionError):
        return {"outcome": "malformed"}
    if not isinstance(arguments, dict):
        return {"outcome": "malformed"}
    selected_tool = pilot.router.strict_loads(first["content"])["tool"]
    content = pilot.base.serialized({"tool": selected_tool, "arguments": arguments})
    return pilot.score(unit, content, reviewed["finish_reason"])


def totals(rows):
    return {key: sum(row["usage"][key] for row in rows) for key in ("prompt_tokens", "completion_tokens")}


def summarize(plan, original, first, reviewed):
    if [row["request_id"] for row in reviewed] != [row["request_id"] for row in plan["rows"]]:
        raise ValueError("Review report needs every response in the frozen order")
    transitions = []
    for unit, old, new in zip(original["units"], first, reviewed, strict=True):
        transitions.append((pilot.score(unit, old["content"], old["finish_reason"])["outcome"],
                            score_review(unit, old, new)["outcome"]))
    return {
        "scope": "development-only, descriptive; saved first calls",
        "tasks": len(transitions),
        "first_outcomes": dict(Counter(old for old, _ in transitions)),
        "reviewed_outcomes": dict(Counter(new for _, new in transitions)),
        "transitions": dict(Counter(f"{old} -> {new}" for old, new in transitions)),
        "exact_corrections": sum(old != "correct" and new == "correct" for old, new in transitions),
        "exact_regressions": sum(old == "correct" and new != "correct" for old, new in transitions),
        "first_call_tokens": totals(first),
        "added_review_tokens": totals(reviewed),
        "combined_tokens": totals(first + reviewed),
        "median_added_wall_seconds": median(row["elapsed_seconds"] for row in reviewed),
    }


def report(directory, plan):
    config = plan["config"]
    if version("jsonschema") != config["jsonschema_version"]:
        raise ValueError("Validator version differs from the development scoring contract")
    original, first = baseline(config)
    historical = pilot.encode(pilot.report(original, first))
    if pilot.base.digest(historical) != config["baseline_report_sha256"]:
        raise ValueError("Stored first-call scores no longer reproduce")
    completion = json.loads((directory / "COMPLETED.json").read_bytes())
    ledger = directory / "request-budget.jsonl"
    if runner.remaining(plan["rows"], directory, ledger) or pilot.port_open(config["port"]):
        raise ValueError("Review must complete and unload before scoring")
    charges = runner.records(ledger)
    if Counter(row["category"] for row in charges) != {
        "benchmark": completion["generation_requests"], "readiness": completion["metadata_requests"]
    }:
        raise ValueError("The ledger differs from the completion receipt")
    reviewed = runner.records(directory / "results.jsonl")
    result = summarize(plan, original, first, reviewed)
    result["request_counts"] = completion
    result["provenance_sha256"] = {name: pilot.provenance.file_sha(directory / name)
                                    for name in ("manifest.json", "results.jsonl", "request-budget.jsonl")}
    return result


def launch(plan, directory, plan_sha):
    cfg, profile = plan["config"], plan["profile"]
    if json.loads(CONFIG.read_bytes()) != cfg or pilot.implementation(CONFIG, FILES) != plan["implementation_sha256"]:
        raise ValueError("Sealed review code or config changed")
    current = pilot.preflight.runtime(profile, str(pilot.model_path(profile)), str(pilot.LLAMA))
    if current != plan["runtime"] or pilot.template_sha() != plan["template_sha256"]:
        raise ValueError("Runtime differs from the saved first-call profile")
    identity = {"config": cfg, "runtime": current, "plan_sha256": plan_sha,
                "template_sha256": plan["template_sha256"], "model_args": profile["server_args"]}
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / "writer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runner.execute(directory, cfg, plan, profile, plan["rows"], identity)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "report"))
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--tokenizer", type=Path)
    parser.add_argument("--plan-sha256")
    args = parser.parse_args()
    os.umask(0o077)
    if args.command == "prepare":
        if args.tokenizer is None:
            parser.error("prepare requires --tokenizer")
        plan = pilot.encode(prepare(json.loads(CONFIG.read_bytes()), args.tokenizer))
        with args.bundle.open("xb") as output:
            output.write(plan)
        print(pilot.base.digest(plan))
        return
    if args.plan_sha256 is None:
        parser.error("run and report require --plan-sha256")
    plan = json.loads(pilot.checked(args.bundle, args.plan_sha256))
    directory = runner.RUNS / plan["config"]["run_id"]
    if args.command == "run":
        launch(plan, directory, args.plan_sha256)
    else:
        identity = json.loads((directory / "manifest.json").read_bytes())
        if identity["plan_sha256"] != args.plan_sha256 or pilot.implementation(CONFIG, FILES) != plan["implementation_sha256"]:
            raise ValueError("Scoring code or plan differs from the campaign manifest")
        print(pilot.encode(report(directory, plan)).decode(), end="")


if __name__ == "__main__":
    main()
