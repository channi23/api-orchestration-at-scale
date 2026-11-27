"""Offline DigitalOcean development pilot against a pinned OpenAPI source tree."""

import argparse
from collections.abc import Mapping
import json
from pathlib import Path, PurePosixPath
import posixpath
import tarfile
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from . import v2_lineage, v2_official_sources as official


BASE = official.BASE
DATA = Path(BASE.paths.DATA, "v2-digitalocean-v0.1")
REVISION = "0644e10b56a1ea9eff4e221ff35758db5037510a"
ROOT = "specification/DigitalOcean-public.v2.yaml"
ROOT_SHA = "077698af2ea18b9713399901725ed1f142200d6a1882fc213144b39c649b186e"
LICENSE_SHA = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
PROJECT = "digitalocean/openapi"


class SourceTree:
    def __init__(self, archive):
        self.archive = archive
        self.hashes = {}
        self.docs = {}

    def read(self, path):
        if path != "LICENSE" and not path.startswith("specification/"):
            raise ValueError(f"Reference outside the pinned spec: {path}")
        relative = PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Reference outside the pinned spec: {path}")
        member = self.archive.getmember(f"openapi-{REVISION}/{path}")
        if not member.isfile():
            raise ValueError(f"Source member must be a regular file: {path}")
        with self.archive.extractfile(member) as file:
            payload = file.read()
        self.hashes[path] = BASE.digest(payload)
        return payload

    def load(self, path):
        import yaml

        if path not in self.docs:
            self.docs[path] = yaml.safe_load(self.read(path))
        return self.docs[path]

    def resolve(self, item, origin):
        """Resolve only file paths and JSON Pointers within the pinned specification tree."""
        seen = set()
        while isinstance(item, Mapping) and "$ref" in item:
            if set(item) != {"$ref"}:
                raise ValueError("Sibling fields on a reference are outside this pilot")
            ref = urlsplit(item["$ref"])
            path = unquote(ref.path)
            if ref.scheme or ref.netloc or ref.query or path.startswith("/") or "\\" in path:
                raise ValueError("Only relative repository references are allowed")
            if path:
                origin = posixpath.normpath(posixpath.join(posixpath.dirname(origin), path))
            fragment = unquote(ref.fragment)
            key = (origin, fragment)
            if key in seen:
                raise ValueError("Reference cycle")
            seen.add(key)
            if fragment and not fragment.startswith("/"):
                raise ValueError("Expected JSON Pointer fragment")
            item = self.load(origin)
            if fragment:
                for part in fragment[1:].split("/"):
                    token = part.replace("~1", "/").replace("~0", "~")
                    item = item[int(token)] if isinstance(item, list) else item[token]
        if not isinstance(item, Mapping):
            raise ValueError("Expected referenced object")
        return item, origin


def operation_schema(tree, root, operation):
    path = operation["path"]
    item, item_file = tree.resolve(root["paths"][path], ROOT)
    get, get_file = tree.resolve(item["get"], item_file)
    defaults = {}

    def inline(parameters, origin):
        result = []
        for parameter in parameters:
            record, record_file = tree.resolve(parameter, origin)
            schema, _ = tree.resolve(record["schema"], record_file)
            schema = dict(schema)
            if record["in"] != "query":
                raise ValueError("This pilot only projects query inputs")
            name = record["name"]
            if "default" in schema:
                defaults[name] = schema.pop("default")
            else:
                defaults.pop(name, None)
            result.append({**record, "schema": schema})
        return result

    parent_params = inline(item.get("parameters", []), item_file)
    get_params = inline(get.get("parameters", []), get_file)
    materialized = {"paths": {path: {
        "parameters": parent_params,
        "get": {**get, "parameters": get_params},
    }}}
    schema, locations = official.project(materialized, operation)
    for name, value in defaults.items():
        schema["properties"][name]["default"] = value
    return schema, locations, get_file


def build(archive, source_index):
    matches, coverage, hashes, _ = official.screen(source_index, {"digitalocean"})
    if matches["digitalocean"]:
        raise ValueError("DigitalOcean overlaps the indexed prior inventory")
    operation_file = DATA / "operations.jsonl"
    draft_file = DATA / "drafts.jsonl"
    instructions_file = DATA / "REVIEW_INSTRUCTIONS.md"
    operations = BASE.read_rows(operation_file)
    drafts = BASE.read_rows(draft_file)
    policy_file = official.DATA / "SYSTEM_POLICY.txt"
    policy = policy_file.read_text()
    schemas, tools, operations_audit = {}, {}, {}
    with tarfile.open(archive, "r:gz") as upstream:
        tree = SourceTree(upstream)
        root = tree.load(ROOT)
        notice = tree.read("LICENSE")
        if tree.hashes[ROOT] != ROOT_SHA or tree.hashes["LICENSE"] != LICENSE_SHA:
            raise ValueError("Pinned root or licence hash changed")
        if root["openapi"] != "3.0.0" or root["info"]["version"] != "2.0":
            raise ValueError("Unexpected DigitalOcean version")
        for op in operations:
            name = op["tool"]
            if name in tools:
                raise ValueError("Duplicate tool")
            schema, locations, path = operation_schema(tree, root, op)
            schemas[name] = BASE.validator(schema)
            tools[name] = {"name": name, "description": op["description"], "parameters": schema}
            sha = BASE.su.sha(schema)
            operations_audit[name] = {
                "path": op["path"], "operation_id": op["operation_id"], "operation_file": path,
                "parameter_locations": locations, "schema_sha256": sha,
                "exact_prior_argument_schema_matches": hashes.get(sha, []),
            }
        dependencies = tree.hashes
    if len(tools) != 5:
        raise ValueError("Five source tools are required")
    packet, tasks, ids = [], [], set()
    for draft in drafts:
        task_id = "V2DO_" + BASE.digest((DATA.name + "\0" + draft["intent_id"]).encode())[:12]
        if task_id in ids:
            raise ValueError("Duplicate task ID")
        ids.add(task_id)
        names = sorted(tools, key=lambda name: BASE.digest(f"{task_id}\0{name}".encode()))
        gold = draft["arguments"]
        valid = [name for name in names if schemas[name].is_valid(gold)]
        if draft["tool"] not in valid:
            raise ValueError(f"Gold arguments fail validation: {task_id}")
        entry = {"task_id": task_id, "intent_id": draft["intent_id"], "tool": draft["tool"],
                 "schema_valid_gold_tool_names": valid, "approved_for_test": False}
        if "invalid_by_description" in draft:
            foil = {**gold, **draft["invalid_by_description"]}
            if not schemas[draft["tool"]].is_valid(foil):
                raise ValueError("The description-based alternative must pass raw validation")
            entry["schema_valid_description_violation"] = foil
        tasks.append(entry)
        packet.append({"task_id": task_id, "request": draft["request"], "system_policy": policy,
                       "tools": [tools[name] for name in names]})
    audit = {
        "project": PROJECT, "revision": REVISION, "license": "Apache-2.0",
        "dependency_sha256": dependencies, "source_index_sha256": v2_lineage.INDEX_SHA256,
        "index_coverage": coverage, "indexed_owner_matches": matches["digitalocean"],
        "operations": operations_audit, "tasks": tasks,
        "input_sha256": {str(p.relative_to(BASE.REPO)): BASE.digest(p.read_bytes()) for p in
                         (Path(__file__), Path(official.__file__), Path(v2_lineage.__file__),
                          operation_file, draft_file, instructions_file, policy_file,
                          Path(BASE.paths.EXP, "dataset/tool_pool.v1.jsonl"),
                          Path(BASE.paths.DATA, "trainpool/schemas.v1.jsonl"),
                          official.source_expansion.DATA / "cards.source.jsonl")},
        "approved_test_intents": 0, "api_calls": 0, "inference_calls": 0, "training_runs": 0,
    }
    return sorted(packet, key=lambda task: task["task_id"]), notice, audit


def export_review(path, packet, notice):
    payloads = {
        "tasks.jsonl": "".join(BASE.serialized(row) + "\n" for row in packet).encode(),
        "REVIEW_INSTRUCTIONS.md": (DATA / "REVIEW_INSTRUCTIONS.md").read_bytes(),
        "DIGITALOCEAN-LICENSE.txt": notice,
    }
    with ZipFile(path, "x", compression=ZIP_DEFLATED) as bundle:
        for name, content in payloads.items():
            info = ZipInfo(name, date_time=(2026, 11, 25, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            bundle.writestr(info, content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source-index", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--export-review", type=Path)
    args = parser.parse_args()
    packet, notice, audit = build(args.archive, v2_lineage.load_index(args.source_index))
    text = json.dumps(audit, indent=2, sort_keys=True) + "\n"
    recorded = DATA / "audit.json"
    if args.check or args.export_review or recorded.exists():
        if recorded.read_text() != text:
            raise SystemExit("The current inputs differ from the recorded DigitalOcean audit")
    else:
        with recorded.open("x") as file:
            file.write(text)
    if args.export_review:
        export_review(args.export_review, packet, notice)
    print(f"PASS: {len(packet)} development tasks from {len(audit['operations'])} source operations")


if __name__ == "__main__":
    main()
