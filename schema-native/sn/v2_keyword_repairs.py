"""Prepare and score a three-arm comparison on the exposed v2 keyword examples."""

import argparse
from collections import Counter
import json
from pathlib import Path

from . import v2_dev_pilot as pilot
from . import v2_keyword_control as control


CONFIG = pilot.ROOT / "configs/runs/v2_keyword_repairs.json"
EXTRA_FILES = (Path(__file__), control.CONFIG, *control.EXTRA_FILES)
CHECKLIST = (
    "Before returning the call, silently check each requested detail against the schema. "
    "Include every requested detail the schema allows, even when its value equals a default. "
    "Check required fields, array item positions, and applicable branch or dependency rules. "
    "Return only the final JSON object."
)
TOKEN_FIELDS = ("prompt_tokens", "completion_tokens")


def validation_feedback(task, content, finish_reason):
    """Use only the supplied schemas and candidate answer to route a schema repair."""
    tools = {tool["name"]: tool["parameters"] for tool in task["tools"]}
    decision = pilot.router.route(content, tools, truncated=finish_reason == "length")
    if decision["reason"] != "raw_schema":
        return None
    call = decision["call"]
    errors = pilot.base.validator(tools[call["tool"]]).iter_errors(call["arguments"])
    first = min(errors, key=lambda error: (error.json_path, str(list(error.absolute_schema_path)), error.message))
    return f"Arguments at {first.json_path}: {first.message}"


def schedule(units, baseline):
    cases = []
    requests = []
    for unit in units:
        task_id = unit["task_id"]
        if unit.get("gold") is None:
            continue
        task = unit["visible"]
        first = baseline[task_id]
        checklist_id = task_id + "|checklist"
        checklist_task = {**task, "system_policy": task["system_policy"].rstrip() + "\n\n" + CHECKLIST}
        requests.append({"task_id": checklist_id, "visible": checklist_task})
        feedback = validation_feedback(task, first["content"], first["finish_reason"])
        retry_id = None
        if feedback is not None:
            retry_id = task_id + "|retry"
            repair_task = {**task, "follow_up": [
                {"role": "assistant", "content": first["content"]},
                {"role": "user", "content": (
                    "The previous call failed schema validation. " + feedback
                    + "\nCorrect the call while preserving the original request. Return only the corrected JSON object."
                )},
            ]}
            requests.append({"task_id": retry_id, "visible": repair_task})
        cases.append({"unit": unit, "baseline": first, "retry": retry_id, "checklist": checklist_id})

    return cases, requests


def task_plan():
    cfg = json.loads(CONFIG.read_text())
    source = Path(pilot.paths.RUNS) / cfg["baseline_run"]
    manifest = json.loads(pilot.checked(source / "manifest.json", cfg["baseline_manifest_sha256"]))
    previous = control.task_plan()
    if any(manifest[key] != value for key, value in previous.items()):
        raise ValueError("Baseline manifest differs from locked control")
    baseline = pilot.rows_by_id(pilot.checked(source / "results.jsonl", cfg["baseline_results_sha256"]))
    if list(baseline) != [unit["task_id"] for unit in previous["units"]]:
        raise ValueError("Baseline response sequence differs from locked control")
    cases, requests = schedule(previous["units"], baseline)
    if len(cases) != 32 or len(requests) != cfg["generation_cap"]:
        raise ValueError("Development roster or request cap differs from the locked protocol")
    return {"config": cfg, "cases": cases, "units": requests,
            **{key: manifest[key] for key in ("profile", "template_sha256", "runtime")}}


def build():
    return {**task_plan(), "implementation_sha256": pilot.implementation(CONFIG, EXTRA_FILES)}


def token_usage(responses):
    return {key: sum(row["usage"][key] for row in responses) for key in TOKEN_FIELDS}


def report(plan, responses):
    if [r["task_id"] for r in responses] != [u["task_id"] for u in plan["units"]]:
        raise ValueError("Report requires all responses in the frozen order")
    by_id = {row["task_id"]: row for row in responses}
    details = []
    baseline_responses = []
    retry_responses = []
    checklist_responses = []
    for case in plan["cases"]:
        unit = case["unit"]
        baseline = case["baseline"]
        baseline_responses.append(baseline)
        checklist = by_id[case["checklist"]]
        checklist_responses.append(checklist)
        retry = by_id.get(case["retry"])
        if retry is not None:
            retry_responses.append(retry)
        answers = {"baseline": baseline, "validator_retry": retry or baseline, "checklist": checklist}
        outcomes = {arm: pilot.score(unit, row["content"], row["finish_reason"])["outcome"]
                    for arm, row in answers.items()}
        details.append({"task_id": unit["task_id"], "retry_sent": retry is not None, "outcomes": outcomes})

    traffic = {"baseline": baseline_responses, "validator_retry": baseline_responses + retry_responses,
               "checklist": checklist_responses}
    arms = {}
    for arm, rows in traffic.items():
        transitions = [(d["outcomes"]["baseline"], d["outcomes"][arm]) for d in details]
        arms[arm] = {"logical_requests": len(rows), "token_usage": token_usage(rows),
                     "outcomes": dict(Counter(new for _, new in transitions)),
                     "improved": sum(old != "correct" and new == "correct" for old, new in transitions),
                     "regressed": sum(old == "correct" and new != "correct" for old, new in transitions)}
    return {"scope": "development-only, descriptive; stored baseline", "items": len(details),
            "live_requests": len(responses), "live_token_usage": token_usage(responses),
            "arms": arms, "tasks": details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run"))
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--approved-plan-sha256")
    args = parser.parse_args()
    current = pilot.encode(build())
    if args.command == "prepare":
        with args.bundle.open("xb") as file:
            file.write(current)
        print(pilot.base.digest(current))
    else:
        if args.approved_plan_sha256 is None:
            parser.error("run requires the locked plan SHA-256")
        sealed = pilot.checked(args.bundle, args.approved_plan_sha256)
        if sealed != current:
            raise ValueError("Prepared plan no longer matches the frozen inputs and runner")
        pilot.launch(json.loads(sealed), config_path=CONFIG, extra_files=EXTRA_FILES, reporter=report)


if __name__ == "__main__":
    main()
