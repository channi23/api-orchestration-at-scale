"""Assemble a private source-held-out candidate packet without loading a model."""

import argparse
from collections import Counter
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from . import v2_lineage, v2_official_sources as official


BASE = official.BASE
ATOMS = official.LITERAL_KEYWORDS | {"default", "pattern", "example", "exclusiveMinimum",
                                     "exclusiveMaximum", "minProperties", "maxProperties",
                                     "multipleOf", "uniqueItems"}
REVIEW = """Use only tasks.jsonl, the supplied tool schemas and the policy in each task.
The notices identify the upstream schema terms. Do not open the repo, prior reviews, files
with answer keys, or outside documentation. Do not call endpoints. Disclose prior exposure.
Save answers.jsonl with one row per task and keys task_id, tool, and arguments. In
REVIEW_NOTES.md, give any alternative answer that could fulfill the request, assumptions,
schema mismatches, or unclear wording. Preserve both files before requesting gold.
"""
POLICY = (
    'Return exactly one JSON object with keys "tool" and "arguments". Use the visible '
    "descriptions and schemas to choose a tool that fulfills the request. Preserve stated values, "
    "string case and array order. Include explicitly requested values even when they equal a "
    "schema default. Omit unrequested defaults and do not guess missing values. Use the supplied "
    "JSON argument shape. Do not execute a tool or include commentary."
)


def dereference(document, value, chain=()):
    if "$ref" not in value:
        return value, chain
    ref = value["$ref"]
    if set(value) != {"$ref"} or not ref.startswith("#/") or ref in chain:
        raise ValueError(f"Unexpected, external or cyclic OpenAPI reference: {ref}")
    target = document
    for part in ref[2:].split("/"):
        target = target[part.replace("~1", "/").replace("~0", "~")]
    return dereference(document, target, (*chain, ref))


def project_schema(document, schema, chain=()):
    if isinstance(schema, bool):
        return schema
    schema, chain = dereference(document, schema, chain)
    result = {}
    for key, value in schema.items():
        if key == "properties":
            result[key] = {name: project_schema(document, sub, chain) for name, sub in value.items()}
        elif key in {"items", "additionalProperties"}:
            result[key] = project_schema(document, value, chain)
        elif key in {"anyOf", "oneOf", "allOf"}:
            result[key] = [project_schema(document, sub, chain) for sub in value]
        elif key in ATOMS:
            result[key] = value
        elif key == "nullable" or key.startswith("x-"):
            continue
        else:
            raise ValueError(f"Unsupported OpenAPI schema keyword: {key}")
    if schema.get("nullable") is True:
        if not isinstance(result.get("type"), str):
            raise ValueError("OpenAPI 3.0 nullable requires a local single type")
        result["type"] = [result["type"], "null"]
    for key, bound in (("exclusiveMinimum", "minimum"), ("exclusiveMaximum", "maximum")):
        if key in result:
            if type(result[key]) is not bool:
                raise ValueError(f"Expected the OpenAPI 3.0 form of {key}")
            if result.pop(key):
                result[key] = result.pop(bound)
    return result


def project_operation(document, selector):
    item, _ = dereference(document, document["paths"][selector["path"]])
    get, _ = dereference(document, item["get"])
    if get["operationId"] != selector["operation_id"] or "requestBody" in get:
        raise ValueError("Expected the pinned read-only operation without a request body")
    merged = {}
    for scope in (item.get("parameters", []), get.get("parameters", [])):
        names = set()
        for value in scope:
            param, _ = dereference(document, value)
            key = (param["in"], param["name"])
            if key in names or key[0] not in {"path", "query"} or "content" in param:
                raise ValueError(f"Unsupported parameter definition: {key}")
            if key[0] == "path" and not param.get("required"):
                raise ValueError(f"Missing required path parameter: {key}")
            names.add(key)
            merged[key] = param
    arguments, required = {}, []
    for (_, name), param in merged.items():
        if name in arguments:
            raise ValueError(f"Repeated argument name: {name}")
        projected = project_schema(document, param["schema"])
        if param.get("description"):
            projected["description"] = param["description"]
        arguments[name] = projected
        if param.get("required"):
            required.append(name)
    return {"$schema": official.DIALECT, "type": "object", "properties": arguments,
            "required": required, "additionalProperties": False}


def exposed_owners():
    folder = Path(BASE.paths.DATA)
    owners = {entry["project"].split("/")[0].casefold() for entry in
              BASE.read_rows(official.DATA / "sources.jsonl")}
    digitalocean = json.loads((folder / "v2-digitalocean-v0.1/audit.json").read_text())
    owners.add(digitalocean["project"].split("/")[0].casefold())
    return owners


def assemble(inputs, index):
    manifest_path = inputs / "sources.jsonl"
    operations_path = inputs / "operations.jsonl"
    drafts_path = inputs / "drafts.jsonl"
    sources = BASE.read_rows(manifest_path)
    operations = BASE.read_rows(operations_path)
    drafts = BASE.read_rows(drafts_path)
    owners = [source["project"].split("/")[0].casefold() for source in sources]
    if len(set(owners)) != len(owners) or set(owners) & exposed_owners():
        raise ValueError("Duplicate or exposed development source owner")
    matches, coverage, legacy_hashes, _ = official.screen(index, owners)
    if any(matches.values()):
        raise ValueError("A source owner already appears in the indexed benchmark inventory")
    catalogs, notices, documents = {}, {}, {}
    for source in sources:
        group = source["project"]
        document = official.load_spec(inputs, source["spec"])
        if (document["openapi"], document["info"]["version"]) != (source["openapi"], source["version"]):
            raise ValueError(f"Source version changed: {group}")
        if not document["openapi"].startswith("3.0."):
            raise ValueError("This source intake handles OpenAPI 3.0")
        documents[group] = document
        catalogs[group] = {}
        notice = source["notice"]
        notices[notice["file"]] = official.source_file(inputs, notice)

    validators, tool_evidence = {}, []
    for op in operations:
        name, group = op["tool"], op["project"]
        if name in validators:
            raise ValueError(f"Duplicate tool: {name}")
        schema = project_operation(documents[group], op)
        sha = BASE.su.sha(schema)
        if sha in legacy_hashes:
            raise ValueError("An exact projected schema already exists in the prior inventory")
        catalogs[group][name] = {"name": name, "description": op["description"], "parameters": schema}
        validators[name] = BASE.validator(schema)
        tool_evidence.append({**op, "schema_sha256": sha})

    tasks, gold, records, ids = [], [], [], set()
    for draft in drafts:
        group = draft["project"]
        catalog = catalogs[group]
        task_id = "V2HC_" + BASE.digest(("a-v0.1\0" + draft["intent_id"]).encode())[:12]
        target, args = draft["tool"], draft["arguments"]
        if task_id in ids or len(catalog) != 5 or target not in catalog:
            raise ValueError("Expected a unique task with a five-tool source catalog")
        ids.add(task_id)
        selected = sorted(catalog, key=lambda name: BASE.digest(f"{task_id}\0{name}".encode()))
        valid_names = [name for name in selected if validators[name].is_valid(args)]
        if target not in valid_names:
            raise ValueError(f"Gold fails projected input schema: {task_id}")
        for invalid in draft.get("schema_negatives", []):
            if validators[target].is_valid(invalid):
                raise ValueError(f"Declared invalid witness validates: {task_id}")
        tasks.append({"task_id": task_id, "request": draft["request"], "system_policy": POLICY,
                      "tools": [catalog[name] for name in selected]})
        gold.append({"task_id": task_id, "tool": target, "arguments": args})
        records.append({"task_id": task_id, "project": group, "intent_id": draft["intent_id"],
                        "gold_valid_tool_names": valid_names, "schema_negatives": len(draft.get("schema_negatives", []))})
    if {row["tool"] for row in gold} != set(validators):
        raise ValueError("Every pilot operation must have a primary task")
    provenance = {
        "status": "private_candidate_review_pending", "approved_test_intents": 0,
        "sources": sources, "indexed_prior_owner_matches": matches, "prior_index_coverage": coverage,
        "source_index_sha256": v2_lineage.INDEX_SHA256,
        "tool_evidence": tool_evidence, "tasks": records,
        "counts_by_source": dict(Counter(row["project"] for row in records)),
        "inputs_sha256": {f.name: BASE.digest(f.read_bytes()) for f in (manifest_path, operations_path, drafts_path)},
        "builder_sha256": BASE.digest(Path(__file__).read_bytes()),
    }
    return sorted(tasks, key=lambda row: row["task_id"]), sorted(gold, key=lambda row: row["task_id"]), notices, provenance


def emit(destination, tasks, gold, notices, provenance):
    sections = {
        "tasks.jsonl": "".join(BASE.serialized(row) + "\n" for row in tasks).encode(),
        "REVIEW_INSTRUCTIONS.md": REVIEW.encode(),
        **notices,
    }
    destination.mkdir(mode=0o700)
    visible_dir = destination / "review"
    private_dir = destination / "sealed"
    visible_dir.mkdir(mode=0o700)
    private_dir.mkdir(mode=0o700)
    review_zip = visible_dir / "v2-holdout-candidate-a-v0.1-blind-review.zip"
    with ZipFile(review_zip, "x", compression=ZIP_DEFLATED) as output:
        for name, content in sections.items():
            info = ZipInfo(name, date_time=(2026, 11, 25, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            output.writestr(info, content)
    gold_bytes = "".join(BASE.serialized(row) + "\n" for row in gold).encode()
    (private_dir / "gold.jsonl").write_bytes(gold_bytes)
    (private_dir / "manifest.json").write_text(json.dumps({
        **provenance, "review_zip_sha256": BASE.digest(review_zip.read_bytes()),
        "gold_sha256": BASE.digest(gold_bytes),
    }, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--source-index", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    emit(args.out, *assemble(args.inputs, v2_lineage.load_index(args.source_index)))
    print("PASS: private source-held-out candidates and separate review packet")


if __name__ == "__main__":
    main()
