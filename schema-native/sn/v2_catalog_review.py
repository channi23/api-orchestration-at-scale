"""Build provisional one-swap development catalogs and their blind review packet."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from . import source_expansion, v2_v03


BASE = v2_v03.BASE
DATA = Path(BASE.paths.DATA, "v2-catalog-review-v0.1")
VERSION = DATA.name
DATE = "2026-11-25"


def load():
    _, drafts, pool, schemas, parent_catalogs, _, policy = v2_v03.load()
    cards, raw_candidates = source_expansion.load()
    by_target = {draft["tool_id"]: draft for draft in drafts}
    by_card = {card["card_id"]: card for card in cards}
    swaps = BASE.read_rows(DATA / "swaps.jsonl")
    seen_targets = set()
    seen_cards = set()
    selected, catalogs, evidence = [], {}, []

    for swap in swaps:
        target_id, card_id, removed_id = (
            swap["target_tool_id"], swap["candidate_card_id"], swap["replaced_tool_id"]
        )
        if target_id in seen_targets or card_id in seen_cards:
            raise ValueError("The packet needs distinct target requests and candidate tools")
        seen_targets.add(target_id)
        seen_cards.add(card_id)
        card = by_card[card_id]
        if target_id not in card["proposed_peer_for"] or card["binding"] != "identity":
            raise ValueError(f"{card_id} needs a nominated target and a direct object binding")

        parent = by_target[target_id]
        control_ids = parent_catalogs[target_id]["tool_ids"]
        if removed_id == target_id or control_ids.count(removed_id) != 1 or card_id in pool:
            raise ValueError("A swap must replace exactly one existing distractor")
        new_ids = [card_id if tool_id == removed_id else tool_id for tool_id in control_ids]
        candidate_schema = raw_candidates[card_id]
        target_schema = schemas[target_id]
        alternative = swap["candidate_witness"]
        candidate_validator = BASE.validator(candidate_schema)
        target_validator = BASE.validator(target_schema)
        target_validator.validate(parent["gold_args"])
        candidate_validator.validate(alternative)

        key = BASE.digest(f"{VERSION}\0{parent['task_id']}\0{card_id}".encode())[:12]
        task_id = "V2CR_" + key
        selected.append({**parent, "task_id": task_id})
        pool[card_id] = {"tool_name": card["tool_name"], "description": swap["description"]}
        schemas[card_id] = candidate_schema
        if len(new_ids) != 5 or len({pool[tid]["tool_name"] for tid in new_ids}) != 5:
            raise ValueError("Review requires five distinct tools")
        accepts_gold = [
            tid for tid in new_ids if BASE.validator(schemas[tid]).is_valid(parent["gold_args"])
        ]
        catalogs[target_id] = {
            "task_id": task_id,
            "parent_task_id": parent["task_id"],
            "tool_id": target_id,
            "tool_ids": new_ids,
            "control_tool_ids": control_ids,
            "replaced_tool_id": removed_id,
            "candidate_card_id": card_id,
            "source_group": swap["source_group"],
            "scope": "development_only",
            "approved_for_test": False,
        }
        evidence.append({
            "task_id": task_id,
            "target_tool_id": target_id,
            "candidate_card_id": card_id,
            "target_gold_valid": True,
            "candidate_witness_valid": True,
            "target_gold_also_valid_for_candidate": card_id in accepts_gold,
            "candidate_witness_also_valid_for_target": target_validator.is_valid(alternative),
            "catalog_tool_ids_accepting_target_arguments": accepts_gold,
            "candidate_schema_sha256": card["schema_sha256"],
            "author_semantic_rationale": swap["rationale"],
        })
    return selected, pool, schemas, catalogs, policy, evidence


def lines(rows):
    return "".join(BASE.serialized(row) + "\n" for row in rows)


def build(loaded):
    drafts, _, _, catalogs, policy, evidence = loaded
    inputs = [
        Path(__file__),
        DATA / "swaps.jsonl",
        DATA / "FRESH_REVIEW_INSTRUCTIONS.md",
        v2_v03.DATA / "manifest.json",
        v2_v03.DATA / "catalogs.jsonl",
        v2_v03.DATA / "drafts.clean.jsonl",
        source_expansion.DATA / "manifest.json",
        source_expansion.DATA / "cards.source.jsonl",
    ]
    manifest = {
        "version": VERSION,
        "date": DATE,
        "source_collection_revision": BASE.UPSTREAM_REVISION,
        "inputs_sha256": {
            str(path.relative_to(BASE.REPO)): BASE.digest(path.read_bytes()) for path in inputs
        },
        "policy_sha256": BASE.digest(policy.encode()),
        "scope": "Model-free catalog review, development only",
    }
    validation = {
        "catalogs": len(drafts),
        "tools_per_catalog": 5,
        "target_gold_valid": sum(row["target_gold_valid"] for row in evidence),
        "candidate_witness_valid": sum(row["candidate_witness_valid"] for row in evidence),
        "cases": evidence,
        "independent_reviews": 0,
        "verified_near_misses": 0,
        "approved_test_intents": 0,
        "endpoint_requests": 0,
    }
    return {
        "catalogs.jsonl": lines(catalogs[target] for target in sorted(catalogs)),
        "manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        "validation.json": json.dumps(validation, indent=2, sort_keys=True) + "\n",
    }


def export_review(path, loaded):
    drafts, pool, schemas, catalogs, policy, _ = loaded
    visible = v2_v03.previous.packet(drafts, pool, schemas, catalogs, policy)
    payloads = {
        "tasks.jsonl": lines(visible),
        "REVIEW_INSTRUCTIONS.md": (DATA / "FRESH_REVIEW_INSTRUCTIONS.md").read_text(),
    }
    with ZipFile(path, "x", compression=ZIP_DEFLATED) as archive:
        for name, content in payloads.items():
            info = ZipInfo(name, date_time=(2026, 11, 25, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "export-review", "check-review"])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--reviewer")
    args = parser.parse_args()
    loaded = load()
    if args.command == "audit":
        for name, content in build(loaded).items():
            path = DATA / name
            if args.check:
                if not path.exists() or path.read_text() != content:
                    raise SystemExit(f"Artifact differs: {name}")
            else:
                path.write_text(content)
        print("PASS: development catalogs and candidate witnesses")
    elif args.out is None:
        parser.error("Review commands require --out")
    elif args.command == "export-review":
        export_review(args.out, loaded)
    else:
        if args.responses is None or not args.reviewer:
            parser.error("check-review requires --responses and --reviewer")
        drafts, pool, schemas, catalogs, _, _ = loaded
        result = v2_v03.previous.compare_review(
            drafts, pool, schemas, catalogs, BASE.read_rows(args.responses), args.reviewer
        )
        with args.out.open("x") as stream:
            stream.write(BASE.serialized(result) + "\n")


if __name__ == "__main__":
    main()
