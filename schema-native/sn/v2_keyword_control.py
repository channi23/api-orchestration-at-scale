"""Materialize, verify or run the v2 synthetic development schema-visibility control."""

import argparse
from collections import Counter
import json
from pathlib import Path

from . import keyword_seed, v2_dev_pilot as pilot


ROOT = pilot.ROOT
CONFIG = ROOT / "configs/runs/v2_keyword_control.json"
PAIRS = keyword_seed.DATA / "pairs.jsonl"
AUDIT = ROOT / "analysis/v2-keyword-control-v0.1/audit.json"
EXTRA_FILES = (Path(__file__), Path(keyword_seed.__file__), PAIRS, AUDIT)
VARIANTS = ("S", "S2")


def message_hash(task):
    return pilot.base.digest(pilot.base.serialized(pilot.messages(task)).encode())


def cases():
    packets = {task["task_id"]: task for task in keyword_seed.review_packet()}
    for pair in keyword_seed.cases():
        pair_id = pair["pair_id"]
        members = []
        for variant in VARIANTS:
            source_id = "KSEED_" + pilot.base.digest(f"{pair_id}:{variant}".encode())[:12]
            source = packets.pop(source_id)
            source_tool, = source["tools"]
            tool = {**source_tool, "description": "Submit the requested synthetic form."}
            policy = source["system_policy"].replace(
                "Use the tool descriptions and raw JSON Schemas to map",
                "Use the tool descriptions and any supplied JSON Schemas to map",
            )
            if policy == source["system_policy"]:
                raise ValueError("Expected shared policy clause missing")
            task_id = f"{pair_id}|visible|{variant}"
            visible = {"request": source["request"], "system_policy": policy, "tools": [tool]}
            gold = {"tool": pair["tool_name"], "arguments": pair[f"gold_{variant}"]}
            pilot.base.validator(tool["parameters"]).validate(gold["arguments"])
            members.append({"task_id": task_id, "visible": visible, "gold": gold})

        hidden_tasks = [
            {**member["visible"], "tools": [
                {key: value for key, value in tool.items() if key != "parameters"}
                for tool in member["visible"]["tools"]
            ]}
            for member in members
        ]
        if pilot.messages(hidden_tasks[0]) != pilot.messages(hidden_tasks[1]):
            raise ValueError(f"Schema-hidden messages differ for {pair_id}")
        hidden = {"task_id": f"{pair_id}|hidden", "visible": hidden_tasks[0]}
        yield pair, members, hidden

    if packets:
        raise ValueError("Expected full packet coverage")


def audit():
    evidence = []
    visible_hashes = set()
    hidden_hashes = set()
    for pair, members, hidden in cases():
        visible = dict(zip(VARIANTS, (message_hash(m["visible"]) for m in members), strict=True))
        hidden_hash = message_hash(hidden["visible"])
        if visible["S"] == visible["S2"] or hidden_hash in visible.values():
            raise ValueError(f"Invalid schema ablation for {pair['pair_id']}")
        visible_hashes.update(visible.values())
        hidden_hashes.add(hidden_hash)
        evidence.append({
            "pair_id": pair["pair_id"],
            "family_id": pair["family_id"],
            "pair_kind": pair["pair_kind"],
            "different_gold": not pilot.base.argument_equal(pair["gold_S"], pair["gold_S2"]),
            "visible_messages_sha256": visible,
            "hidden_messages_sha256": hidden_hash,
        })

    n = len(evidence)
    if len(visible_hashes) != 2 * n or len(hidden_hashes) != n:
        raise ValueError("Expected distinct prompts")
    same_gold = sum(not row["different_gold"] for row in evidence)
    return {
        "scope": "model-free development design",
        "pairs_sha256": pilot.provenance.file_sha(PAIRS),
        "pairs": n,
        "families": len({row["family_id"] for row in evidence}),
        "visible_prompts": len(visible_hashes),
        "hidden_prompts": len(hidden_hashes),
        "different_gold_pairs": n - same_gold,
        "hidden_max_exact_members": n + same_gold,
        "hidden_max_pair_correct": same_gold,
        "evidence": evidence,
    }


def task_plan():
    cfg = json.loads(CONFIG.read_text())
    pilot.checked(PAIRS, cfg["pairs_sha256"])
    receipt = audit()
    if receipt != json.loads(AUDIT.read_text()):
        raise ValueError("Rendered inputs differ from the locked prompt audit")
    units = []
    pairs = []
    for pair, members, hidden in cases():
        units.extend([hidden, *members])
        pairs.append({"pair_id": pair["pair_id"], "kind": pair["pair_kind"],
                      "hidden": hidden["task_id"], "visible": [unit["task_id"] for unit in members]})
    if len(units) != cfg["generation_cap"] or len({u["task_id"] for u in units}) != len(units):
        raise ValueError("Generation units differ from the hard request cap")
    return {"config": cfg, "units": units, "pairs": pairs}


def build():
    plan = task_plan()
    profile = json.loads(pilot.checked(pilot.PROFILE, plan["config"]["profile_sha256"]))
    return {
        **plan,
        "profile": profile,
        "implementation_sha256": pilot.implementation(CONFIG, EXTRA_FILES),
        "template_sha256": pilot.template_sha(),
        "runtime": pilot.preflight.runtime(profile, str(pilot.model_path(profile)), str(pilot.LLAMA)),
    }


def report(plan, responses):
    expected = [unit["task_id"] for unit in plan["units"]]
    if [row["task_id"] for row in responses] != expected:
        raise ValueError("Report requires all completions in the frozen order")
    response_for = {row["task_id"]: row for row in responses}
    unit_for = {unit["task_id"]: unit for unit in plan["units"]}
    details = []
    for pair in plan["pairs"]:
        outcomes = {}
        for arm in ("visible", "hidden"):
            scores = []
            for task_id in pair["visible"]:
                response_id = task_id if arm == "visible" else pair["hidden"]
                value = response_for[response_id]
                scores.append(pilot.score(unit_for[task_id], value["content"], value["finish_reason"]))
            outcomes[arm] = scores
        comparable = all(score["outcome"] not in ("malformed", "truncated") for score in outcomes["visible"])
        visible_same_answer = None
        if comparable:
            left, right = [pilot.router.strict_loads(response_for[key]["content"]) for key in pair["visible"]]
            visible_same_answer = pilot.base.argument_equal(left, right)
        details.append({"pair_id": pair["pair_id"], "kind": pair["kind"],
                        "visible_same_answer": visible_same_answer, **outcomes})

    arms = {}
    for arm in ("visible", "hidden"):
        groups = {}
        for kind in ("all", *sorted({row["kind"] for row in details})):
            subset = [row[arm] for row in details if kind == "all" or row["kind"] == kind]
            outcomes = Counter(member["outcome"] for pair in subset for member in pair)
            groups[kind] = {
                "pairs": len(subset),
                "members": 2 * len(subset),
                "pair_correct": sum(all(m["outcome"] == "correct" for m in pair) for pair in subset),
                "outcomes": dict(outcomes),
            }
        arms[arm] = groups
    return {
        "scope": "development-only, descriptive",
        "request_count": len(responses),
        "arms": arms,
        "total_usage": {key: sum(row["usage"][key] for row in responses)
                        for key in ("prompt_tokens", "completion_tokens")},
        "pairs": details,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "prepare", "run"))
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--approved-plan-sha256")
    args = parser.parse_args()
    if args.command == "audit":
        print(pilot.encode(audit()).decode(), end="")
    elif args.bundle is None:
        parser.error("prepare and run require --bundle")
    elif args.command == "prepare":
        data = pilot.encode(build())
        with args.bundle.open("xb") as file:
            file.write(data)
        print(pilot.provenance.file_sha(args.bundle))
    elif args.approved_plan_sha256 is None:
        parser.error("run requires --approved-plan-sha256")
    else:
        plan = json.loads(pilot.checked(args.bundle, args.approved_plan_sha256))
        current = task_plan()
        if any(plan[key] != value for key, value in current.items()):
            raise ValueError("Exact request selection or prompt changed")
        pilot.launch(plan, config_path=CONFIG, extra_files=EXTRA_FILES, reporter=report)


if __name__ == "__main__":
    main()
