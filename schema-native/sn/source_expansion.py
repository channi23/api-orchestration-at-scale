"""Source-derived offline candidate cards, not production APIs or approved peers."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import subprocess
import zipfile

import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

from . import v2_authoring as common


DATA = Path(common.paths.DATA, "v2-source-expansion-v0.1")


def binding(card, raw):
    """Preserve a non-object schema as its own resource, never transplant its refs."""
    registry = Registry(retrieve=common.no_remote)
    if card["binding"] == "identity":
        return raw, registry
    if card["binding"] != "root_value_resource":
        raise ValueError("Unknown source binding")
    uri = "urn:v2-source:sha256:" + common.su.sha(raw)
    resource = Resource.from_contents(raw, default_specification=DRAFT7)
    registry = registry.with_resource(uri, resource)
    wrapper = {"$schema": raw.get("$schema", "http://json-schema.org/draft-07/schema#"),
               "type": "object", "properties": {"value": {"$ref": uri}},
               "required": ["value"], "additionalProperties": False}
    return wrapper, registry


def validator(card, raw):
    schema, registry = binding(card, raw)
    cls = jsonschema.validators.validator_for(schema, default=jsonschema.Draft7Validator)
    cls.check_schema(schema)
    return cls(schema, registry=registry)


def load():
    revision = subprocess.check_output(["git", "-C", str(common.UPSTREAM), "rev-parse", "HEAD"], text=True).strip()
    if revision != common.UPSTREAM_REVISION:
        raise ValueError("Source collection revision differs")
    cards = common.read_rows(DATA / "cards.source.jsonl")
    if len({c["card_id"] for c in cards}) != len(cards) or len({c["tool_name"] for c in cards}) != len(cards):
        raise ValueError("Duplicate source card identity")
    raws = {}
    for card in cards:
        raw = common.su.load_schema(card["schema_id"])
        if common.su.sha(raw) != card["schema_sha256"]:
            raise ValueError("Source schema changed: " + card["card_id"])
        common.validator(raw)
        for path in card["purpose_evidence"]:
            node = raw
            for part in path.lstrip("/").split("/"):
                part = part.replace("~1", "/").replace("~0", "~")
                node = node[int(part)] if isinstance(node, list) else node[part]
        validator(card, raw).validate(card["example"])
        raws[card["card_id"]] = raw
    return cards, raws


def build():
    cards, raws = load()
    pool = common.paths.pool()
    old_hashes = {r["schema_sha256"]: r["tool_id"] for r in pool.values()}
    training = common.read_rows(Path(common.paths.DATA, "trainpool/schemas.v1.jsonl"))
    train_by_id = {r["schema_id"]: r for r in training}
    out = []
    for card in cards:
        raw = raws[card["card_id"]]
        schema, _ = binding(card, raw)
        rec = {**card, "collection_revision": common.UPSTREAM_REVISION,
               "schema_raw_sha256": common.digest(Path(common.su.DATA_DIR, card["schema_id"] + ".json").read_bytes()),
               "binding_schema_sha256": common.su.sha(schema),
               "declared_source_uri": raw.get("$id", raw.get("id")),
               "exact_frozen_pool_match": old_hashes.get(card["schema_sha256"]),
               "legacy_trainpool_assignment": train_by_id.get(card["schema_id"]),
               "split": "development_only", "schema_valid_sample": True,
               "production_endpoint_verified": False, "near_miss_verified": False,
               "licence_clearance": "unverified", "source_group_holdout_verified": False,
               "catalog_insertion_approved": False}
        if rec["exact_frozen_pool_match"]:
            raise ValueError("New candidate is an exact pool duplicate")
        out.append(rec)
    summary = {"candidate_cards": len(out), "valid_samples": len(out),
               "represented_gap_targets": sorted({t for c in out for t in c["proposed_peer_for"]}),
               "remaining_unrepresented_gap_targets": ["T045", "T243"],
               "bindings": dict(Counter(c["binding"] for c in out)),
               "near_misses_verified": 0, "catalog_insertions": 0, "approved_test_intents": 0,
               "native_capability_checks": 0, "additional_model_endpoint_requests": 0,
               "limits": ["Cards are offline adapters to pre-existing schemas, not asserted production APIs.",
                          "Positive examples establish validity only, not task difficulty or a semantic peer.",
                          "Wrapped scalar/array schemas need an offline resource binding; no runner compatibility is claimed.",
                          "Original corpus scan covered 9558 schemas; reviewed nomination is not exhaustive source clearance."]}
    manifest = {"source_sha256": common.digest(Path(__file__).read_bytes()),
                "cards_source_sha256": common.digest((DATA / "cards.source.jsonl").read_bytes()),
                "collection_revision": common.UPSTREAM_REVISION,
                "raw_schema_files_copied_to_git": False, "model_requests": 0, "training_runs": 0}
    return {"cards.jsonl": "".join(common.serialized(c) + "\n" for c in out),
            "validation.json": json.dumps(summary, indent=2, sort_keys=True) + "\n",
            "manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n"}


def export_payload():
    cards, raws = load(); payload = []
    for card in cards:
        schema, _ = binding(card, raws[card["card_id"]])
        rec = copy.deepcopy(card)
        rec["argument_schema"] = schema
        rec["source_schema"] = raws[card["card_id"]]
        payload.append(rec)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "export-review"])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.command == "audit":
        for name, text in build().items():
            path = DATA / name
            if args.check:
                if not path.exists() or path.read_text() != text: raise SystemExit("Artifact differs: " + name)
            else: path.write_text(text)
        print("PASS: source hashes, purpose paths and sample validity; no peer approval")
    else:
        if args.out is None: parser.error("export-review requires --out")
        with zipfile.ZipFile(args.out, "x", compression=zipfile.ZIP_DEFLATED) as z:
            for name, text in {"source-candidates.jsonl": "".join(common.serialized(r) + "\n" for r in export_payload()),
                               "REVIEW_INSTRUCTIONS.md": (DATA / "REVIEW_INSTRUCTIONS.md").read_text()}.items():
                info = zipfile.ZipInfo(name, date_time=(2026, 11, 25, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, text)
        print("Wrote source audit packet; this is not a blind model/task evaluation")


if __name__ == "__main__":
    main()
