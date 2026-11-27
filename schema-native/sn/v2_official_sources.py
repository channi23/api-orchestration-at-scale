"""Build an offline development packet from pinned public OpenAPI operations."""

import argparse
import copy
from collections import Counter
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from . import source_expansion, v2_lineage, v2_v03


BASE = v2_v03.BASE
DATA = Path(BASE.paths.DATA, "v2-official-sources-v0.1")
DIALECT = "https://json-schema.org/draft/2020-12/schema"
# Restrict projection to keywords whose meaning is shared by the selected input schemas.
LITERAL_KEYWORDS = {
    "type", "title", "description", "required", "enum", "format",
    "minLength", "maxLength", "minimum", "maximum", "minItems", "maxItems",
}
EMPTY_FORM_BODY = {
    "content": {"application/x-www-form-urlencoded": {
        "encoding": {}, "schema": {"additionalProperties": False, "properties": {}, "type": "object"},
    }},
    "required": False,
}


def source_file(folder, entry):
    raw = (folder / entry["file"]).read_bytes()
    if BASE.digest(raw) != entry["sha256"]:
        raise ValueError(f"Source hash mismatch: {entry['file']}")
    return raw


def load_spec(folder, entry):
    raw = source_file(folder, entry)
    if entry["file"].endswith(".yml"):
        import yaml

        return yaml.safe_load(raw)
    return BASE.strict_loads(raw.decode())


def parameter_schema(schema):
    """Check the supported subset without rewriting nested constraints."""
    if not isinstance(schema, dict):
        raise ValueError("Expected an inline OpenAPI Schema Object")
    for key, value in schema.items():
        if key == "properties":
            for child in value.values():
                parameter_schema(child)
        elif key == "items":
            parameter_schema(value)
        elif key == "anyOf":
            for child in value:
                parameter_schema(child)
        elif key not in LITERAL_KEYWORDS:
            raise ValueError(f"Unsupported input schema keyword: {key}")
    return copy.deepcopy(schema)


def project(spec, operation):
    path_item = spec["paths"][operation["path"]]
    get = path_item["get"]
    if get["operationId"] != operation["operation_id"]:
        raise ValueError("Unexpected OpenAPI operation")
    body = get.get("requestBody")
    if body is not None and body != EMPTY_FORM_BODY:
        raise ValueError("Nonempty or required request body is outside this tranche")
    parameters = {}
    for scope in (path_item.get("parameters", []), get.get("parameters", [])):
        seen = set()
        for parameter in scope:
            if "$ref" in parameter or "content" in parameter:
                raise ValueError("Unsupported OpenAPI parameter reference or content")
            key = (parameter["in"], parameter["name"])
            if key in seen:
                raise ValueError("Duplicate parameter in OpenAPI scope")
            parameters[key] = parameter
            seen.add(key)
    properties, required, locations = {}, [], {}
    skip = set(operation.get("omit_local_only", []))
    for (location, name), parameter in parameters.items():
        if name in skip:
            if location != "query" or parameter.get("required") or (
                "Only available locally" not in parameter.get("description", "")
            ):
                raise ValueError(f"Cannot omit public or required parameter: {name}")
            skip.remove(name)
            continue
        if location not in {"path", "query"} or name in properties:
            raise ValueError(f"Unsupported parameter location or colliding name: {location}/{name}")
        schema = parameter_schema(parameter["schema"])
        if "description" in parameter:
            schema.setdefault("description", parameter["description"])
        properties[name] = schema
        locations[name] = location
        if parameter.get("required", False):
            required.append(name)
    if skip:
        raise ValueError("Recorded local-only parameter no longer exists")
    return {
        "$schema": DIALECT, "type": "object", "properties": properties,
        "required": required, "additionalProperties": False,
    }, locations


def screen(index, owners):
    pool = BASE.paths.pool()
    legacy = BASE.read_rows(Path(BASE.paths.DATA, "trainpool/schemas.v1.jsonl"))
    cards, _ = source_expansion.load()
    prior_ids = {row["schema_id"] for row in [*pool.values(), *legacy, *cards]}
    matches = {owner: {} for owner in owners}
    index_coverage = Counter()
    schema_hashes = {}
    names = {}
    for sid in sorted(prior_ids):
        group, kind, _ = v2_lineage.origin(sid, index)
        index_coverage[kind] += 1
        if kind == "indexed_repository":
            owner = group.removeprefix("github:").split("/", 1)[0]
            if owner in matches:
                matches[owner][sid] = group
        schema = BASE.su.load_schema(sid)
        schema_hashes.setdefault(BASE.su.sha(schema), []).append(sid)
        if isinstance(schema, dict) and schema.get("properties"):
            names.setdefault(tuple(sorted(schema["properties"])), []).append(sid)
    return matches, dict(index_coverage), schema_hashes, names


def prepare(folder, index):
    sources = BASE.read_rows(DATA / "sources.jsonl")
    operations = BASE.read_rows(DATA / "operations.jsonl")
    drafts = BASE.read_rows(DATA / "drafts.jsonl")
    policy = (DATA / "SYSTEM_POLICY.txt").read_text()
    matches, coverage, old_hashes, old_names = screen(index, {"stripe", "pokeapi", "github"})
    specifications, notices, tools, evidence = {}, {}, {}, {}
    for source in sources:
        group = source["project"]
        owner = group.split("/", 1)[0].lower()
        if matches[owner]:
            raise ValueError(f"Indexed prior source overlap for {group}")
        spec = load_spec(folder, source["spec"])
        if spec["openapi"] != source["openapi"] or spec["info"]["version"] != source["api_version"]:
            raise ValueError(f"Unexpected source version: {group}")
        specifications[group] = spec
        notices[source["notice"]["file"]] = source_file(folder, source["notice"])
    catalogs = {group: [] for group in specifications}
    for operation in operations:
        group, name = operation["project"], operation["tool"]
        if name in tools:
            raise ValueError("Duplicate operation tool name")
        schema, locations = project(specifications[group], operation)
        BASE.validator(schema)
        schema_sha256 = BASE.su.sha(schema)
        tools[name] = {"name": name, "description": operation["description"], "parameters": schema}
        catalogs[group].append(name)
        evidence[name] = {
            "project": group, "operation_id": operation["operation_id"], "method": "GET",
            "source_path": operation["path"], "parameter_locations": locations,
            "schema_sha256": schema_sha256,
            "exact_prior_argument_schema_matches": old_hashes.get(schema_sha256, []),
            "prior_root_property_name_set_hits": old_names.get(tuple(sorted(schema["properties"])), []),
            "empty_optional_body_omitted": "requestBody" in specifications[group]["paths"][operation["path"]]["get"],
            "omitted_local_only": operation.get("omit_local_only", []),
        }
    packet, checks = [], []
    task_ids = set()
    prior_requests = [v2_lineage.normalized_request(row["prompt"]) for row in BASE.paths.tasks()]
    prior_requests += [
        v2_lineage.normalized_request(row["request"])
        for row in BASE.read_rows(v2_v03.DATA / "drafts.clean.jsonl")
    ]
    for draft in drafts:
        group = draft["project"]
        names = catalogs[group]
        target = draft["tool"]
        key = BASE.digest((DATA.name + "\0" + draft["intent_id"]).encode())[:12]
        task_id = "V2OS_" + key
        if len(names) != 5 or target not in names or task_id in task_ids:
            raise ValueError(f"Invalid five-tool catalog or duplicate task for {task_id}")
        task_ids.add(task_id)
        if v2_lineage.normalized_request(draft["request"]) in prior_requests:
            raise ValueError(f"Repeated prior request: {task_id}")
        ordered = sorted(names, key=lambda name: BASE.digest(f"{task_id}\0{name}".encode()))
        accepted = [
            name for name in ordered
            if BASE.validator(tools[name]["parameters"]).is_valid(draft["arguments"])
        ]
        if target not in accepted:
            raise ValueError(f"Gold arguments fail source projection: {task_id}")
        packet.append({
            "task_id": task_id, "request": draft["request"], "system_policy": policy,
            "tools": [tools[name] for name in ordered],
        })
        checks.append({
            "task_id": task_id, "intent_id": draft["intent_id"], "project": group, "target": target,
            "catalog_tool_names": ordered, "schema_valid_gold_tool_names": accepted,
            "scope": "development_only", "approved_for_test": False,
        })
    inputs = [
        Path(__file__), Path(v2_lineage.__file__), DATA / "sources.jsonl", DATA / "operations.jsonl",
        DATA / "drafts.jsonl", DATA / "SYSTEM_POLICY.txt", DATA / "REVIEW_INSTRUCTIONS.md",
        v2_v03.DATA / "drafts.clean.jsonl", source_expansion.DATA / "cards.source.jsonl",
        Path(BASE.paths.DATA, "trainpool/schemas.v1.jsonl"),
        Path(BASE.paths.EXP, "dataset/tool_pool.v1.jsonl"), Path(BASE.paths.EXP, "tasks/tasks.v1.jsonl"),
    ]
    audit = {
        "source_index_sha256": v2_lineage.INDEX_SHA256,
        "input_sha256": {str(p.relative_to(BASE.REPO)): BASE.digest(p.read_bytes()) for p in inputs},
        "index_coverage": coverage, "indexed_owner_matches": matches,
        "operations": evidence, "tasks": checks,
        "approved_test_intents": 0, "api_calls": 0, "inference_calls": 0, "training_runs": 0,
    }
    return sorted(packet, key=lambda row: row["task_id"]), notices, audit


def archive(path, packet, notices):
    payloads = {
        "tasks.jsonl": "".join(BASE.serialized(row) + "\n" for row in packet).encode(),
        "REVIEW_INSTRUCTIONS.md": (DATA / "REVIEW_INSTRUCTIONS.md").read_bytes(),
        **notices,
    }
    with ZipFile(path, "x", compression=ZIP_DEFLATED) as bundle:
        for name, content in payloads.items():
            info = ZipInfo(name, date_time=(2026, 11, 25, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            bundle.writestr(info, content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-dir", type=Path, required=True)
    parser.add_argument("--source-index", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--export-review", type=Path)
    args = parser.parse_args()
    packet, notices, audit = prepare(args.sources_dir, v2_lineage.load_index(args.source_index))
    result = json.dumps(audit, indent=2, sort_keys=True) + "\n"
    path = DATA / "audit.json"
    if args.check or args.export_review:
        if path.read_text() != result:
            raise SystemExit("Recorded audit differs from the current inputs")
    else:
        path.write_text(result)
    if args.export_review:
        archive(args.export_review, packet, notices)
    print(f"PASS: {len(packet)} development tasks across {len(notices)} source projects")


if __name__ == "__main__":
    main()
