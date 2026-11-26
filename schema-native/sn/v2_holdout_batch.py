"""Build the private v2 tranche B review packet and an aggregate audit."""

import argparse
from collections import Counter
from importlib.metadata import version
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from . import keyword_seed, v2_holdout as intake, v2_lineage, v2_swagger_inputs, v2_v03

BASE = intake.BASE
RUN = "v2-holdout-candidate-b-v0.1"
NEXT = "v2-holdout-candidate-c-v0.1"
DIALECT = intake.official.DIALECT
MATRICES = {
    "validity_separable": ([True, False, False, True],),
    "asymmetric_edit": ([True, False, True, True], [True, True, False, True]),
    "description_grounding": ([True, True, True, True],),
}


def read_previous(bundles):
    owners, schemas, requests = set(), set(), set()
    for bundle in bundles:
        manifest = json.loads((bundle / "sealed/manifest.json").read_text())
        owners.update(source["project"].split("/")[0].casefold() for source in manifest.get("sources", ()))
        packet, = (bundle / "review").glob("*.zip")
        if BASE.digest(packet.read_bytes()) != manifest["review_zip_sha256"]:
            raise ValueError("Earlier packet bytes changed")
        with ZipFile(packet) as archive:
            for raw in archive.read("tasks.jsonl").decode().splitlines():
                task = BASE.strict_loads(raw)
                requests.add(v2_lineage.normalized_request(task["request"]))
                schemas.update(BASE.su.sha(tool["parameters"]) for tool in task["tools"])
    return owners, schemas, requests


def identifier(intent, suffix, stem=RUN):
    prefix = {RUN: "V2HCB_", NEXT: "V2HCC_"}[stem]
    return prefix + BASE.digest(f"{stem}\0{intent}\0{suffix}".encode())[:16]


def task(task_id, request, tools):
    return {"task_id": task_id, "request": request, "system_policy": intake.POLICY, "tools": tools}


def pair_rows(pair, stem=RUN):
    original = pair["schema"]
    path = pair["edit_path"]
    if original.get("$schema") != DIALECT:
        raise ValueError("Expected explicit Draft 2020-12")
    kind = pair["kind"]
    grounding = kind == "description_grounding"
    if grounding != path.endswith("/description"):
        raise ValueError("Description changes belong exclusively to the grounding track")
    if grounding and (not isinstance(pair["replacement"], str)
                      or tuple(path.split("/")[1::2]) not in {("properties", "description"), ("description",)}):
        raise ValueError("Grounding edits must change a root or direct property description")
    changed = keyword_seed.replace(original, path, pair["replacement"])
    if original == changed:
        raise ValueError("Pair edit must change the schema")
    g, h = pair["arguments"]
    if BASE.argument_equal(g, h):
        raise ValueError("Expected distinct golds for a changed-answer pair")
    a, b = BASE.validator(original), BASE.validator(changed)
    matrix = [a.is_valid(g), b.is_valid(g), a.is_valid(h), b.is_valid(h)]
    if matrix not in MATRICES[kind]:
        raise ValueError(f"Unexpected cross-validity matrix: {pair['intent_id']}")
    for validator, negative in zip((a, b), pair["negatives"], strict=True):
        if validator.is_valid(negative):
            raise ValueError("Declared negative witness validates for a pair")
    tools = [{"name": pair["tool"], "description": pair["tool_description"], "parameters": schema}
             for schema in (original, changed)]
    ids = [identifier(pair["intent_id"], side, stem) for side in ("S", "S2")]
    tasks = [task(key, pair["request"], [tool]) for key, tool in zip(ids, tools, strict=True)]
    gold = [{"task_id": key, "tool": pair["tool"], "arguments": args}
            for key, args in zip(ids, (g, h), strict=True)]
    return tasks, gold, matrix


def assemble(folder, index, prior_bundles, *, stem=RUN):
    sources = BASE.read_rows(folder / "sources.jsonl")
    operations = BASE.read_rows(folder / "operations.jsonl")
    drafts = BASE.read_rows(folder / "drafts.jsonl")
    pairs = BASE.read_rows(folder / "pairs.jsonl")

    earlier_owners, earlier_schemas, earlier_requests = read_previous(prior_bundles)
    if not earlier_owners:
        raise ValueError("The original previous tranche is required for the source screen")
    owners = {row["project"].split("/")[0].casefold() for row in sources}
    if len(owners) != len(sources) or owners & (earlier_owners | intake.exposed_owners()):
        raise ValueError("Repeated or previously reserved source owner")
    matches, coverage, legacy_hashes, _ = intake.official.screen(index, owners)
    if any(matches.values()):
        raise ValueError("Source owner occurs in the indexed legacy inventory")
    _, public_drafts, _, _, _, _, _ = v2_v03.load()
    exposed_requests = earlier_requests | {
        v2_lineage.normalized_request(row["prompt"]) for row in BASE.paths.tasks()
    } | {
        v2_lineage.normalized_request(row["request"]) for row in [*public_drafts, *keyword_seed.cases()]
    }
    exposed_schemas = earlier_schemas | legacy_hashes.keys() | {
        BASE.su.sha(pair[key]) for pair in keyword_seed.cases() for key in ("schema_S", "schema_S2")
    }
    seen_intents, seen_requests = set(), set()
    for row in [*drafts, *pairs]:
        intent = row["intent_id"]
        request = v2_lineage.normalized_request(row["request"])
        if intent in seen_intents or not request or request in exposed_requests or request in seen_requests:
            raise ValueError(f"Duplicate intent ID or normalized request: {intent}")
        seen_intents.add(intent)
        seen_requests.add(request)

    tools_by_source, documents, notices = {}, {}, {}
    for source in sources:
        group = source["project"]
        entries = source.get("specs") or {"default": {**source["spec"], "dialect": source["openapi"],
                                                     "version": source["version"]}}
        documents[group] = {}
        for key, entry in entries.items():
            spec = intake.official.load_spec(folder, entry)
            dialect = spec.get("openapi", spec.get("swagger"))
            if (dialect, str(spec["info"]["version"])) != (entry["dialect"], entry["version"]):
                raise ValueError("API source version changed")
            if dialect != "2.0" and not dialect.startswith(("3.0.", "3.1.")):
                raise ValueError("Supported API projection requires Swagger 2, OpenAPI 3.0 or the 3.1 shared subset")
            documents[group][key] = spec
        tools_by_source[group] = {}
        notice = source["notice"]
        notices[notice["file"]] = intake.official.source_file(folder, notice)

    ops_audit, validators = [], {}
    for op in operations:
        group, name = op["project"], op["tool"]
        if name in validators:
            raise ValueError("Repeated tool name")
        document = documents[group][op.get("document", "default")]
        if "swagger" in document:
            schema = v2_swagger_inputs.project_operation(document, op)
        elif document["openapi"].startswith("3.1."):
            schema = v2_swagger_inputs.project_openapi31(document, op)
        else:
            schema = intake.project_operation(document, op)
        digest = BASE.su.sha(schema)
        if digest in exposed_schemas:
            raise ValueError("Exact known schema overlaps tranche B")
        validators[name] = BASE.validator(schema)
        tools_by_source[group][name] = {"name": name, "description": op["description"], "parameters": schema}
        ops_audit.append({**op, "schema_sha256": digest})

    review, five_tools, gold, evidence = [], [], [], []
    for draft in drafts:
        intent = draft["intent_id"]
        task_id = identifier(intent, "api", stem)
        catalog = tools_by_source[draft["project"]]
        target, args = draft["tool"], draft["arguments"]
        peers = set(draft["close_catalog"])
        if len(catalog) != 20 or len(peers) != 5 or target not in peers or not peers <= catalog.keys():
            raise ValueError("Expected a nested 5/20-tool catalog with the intended target")
        good = [name for name in sorted(catalog) if validators[name].is_valid(args)]
        negative = draft["negative"]
        if target not in good or validators[target].is_valid(negative):
            raise ValueError("Gold or negative witness failed an API check")
        ordered = sorted(catalog, key=lambda name: BASE.digest(f"{task_id}\0{name}".encode()))
        review.append(task(task_id, draft["request"], [catalog[n] for n in ordered]))
        five_tools.append(task(task_id, draft["request"], [catalog[n] for n in ordered if n in peers]))
        gold.append({"task_id": task_id, "tool": target, "arguments": args})
        evidence.append({"intent_id": intent, "project": draft["project"], "task_ids": [task_id],
                         "schema_valid_tools_5": sorted(peers & set(good)), "schema_valid_tools_20": good})

    for pair in pairs:
        variants, answers, matrix = pair_rows(pair, stem)
        if any(BASE.su.sha(row["tools"][0]["parameters"]) in exposed_schemas for row in variants):
            raise ValueError("Exact exposed pair schema")
        review.extend(variants)
        five_tools.extend(variants)
        gold.extend(answers)
        evidence.append({"intent_id": pair["intent_id"], "family_id": pair["family_id"],
                         "kind": pair["kind"], "task_ids": [row["task_id"] for row in variants],
                         "cross_validity": matrix})

    summary = {
        "status": "private review candidate; zero locked-test approvals",
        "approved_test_intents": 0,
        "api_intents": len(drafts),
        "api_source_groups": len(sources),
        "api_tool_counts": sorted(len(group) for group in tools_by_source.values()),
        "api_cross_valid_gold_5": sum(len(row["schema_valid_tools_5"]) > 1 for row in evidence[:len(drafts)]),
        "api_cross_valid_gold_20": sum(len(row["schema_valid_tools_20"]) > 1 for row in evidence[:len(drafts)]),
        "pair_intents_by_kind": dict(Counter(pair["kind"] for pair in pairs)),
        "pair_structural_families": len({p["family_id"] for p in pairs}),
        "new_candidate_intents": len(drafts) + len(pairs),
        "review_rows": len(review),
        "negative_witnesses_rejected": len(drafts) + 2 * len(pairs),
        "indexed_prior_coverage": coverage,
        "indexed_prior_owner_matches": sum(len(v) for v in matches.values()),
        "validator": f"jsonschema {version('jsonschema')}, formats as annotations",
    }
    sealed = {"summary": summary, "sources": sources, "operations": ops_audit, "intents": evidence,
              "input_sha256": {name: BASE.digest((folder / name).read_bytes()) for name in
                               ("sources.jsonl", "operations.jsonl", "drafts.jsonl", "pairs.jsonl")},
              "source_index_sha256": v2_lineage.INDEX_SHA256}
    return review, five_tools, gold, notices, sealed


def emit(out, review, five_tools, gold, notices, sealed, *, stem=RUN):
    out.mkdir(mode=0o700)
    (out / "review").mkdir(mode=0o700)
    private = out / "sealed"
    private.mkdir(mode=0o700)

    def encode(rows):
        return "".join(BASE.serialized(row) + "\n" for row in sorted(rows, key=lambda x: x["task_id"])).encode()

    visible = encode(review)
    packet = out / "review" / f"{stem}-blind-review.zip"
    with ZipFile(packet, "x", compression=ZIP_DEFLATED) as archive:
        entries = {"tasks.jsonl": visible, "REVIEW_INSTRUCTIONS.md": intake.REVIEW.encode(), **notices}
        for name, content in sorted(entries.items()):
            info = ZipInfo(name, date_time=(2026, 11, 26, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content)
    gold_bytes, c5 = encode(gold), encode(five_tools)
    (private / "gold.jsonl").write_bytes(gold_bytes)
    (private / "tasks.c5.jsonl").write_bytes(c5)
    sha = {"review_zip_sha256": BASE.digest(packet.read_bytes()), "gold_sha256": BASE.digest(gold_bytes),
           "tasks_c5_sha256": BASE.digest(c5), "visible_tasks_sha256": BASE.digest(visible)}
    (private / "manifest.json").write_text(json.dumps({**sealed, **sha}, indent=2, sort_keys=True) + "\n")
    return {**sealed["summary"], "review_zip_sha256": sha["review_zip_sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--source-index", type=Path, required=True)
    parser.add_argument("--prior", action="append", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--stem", choices=(RUN, NEXT), default=RUN)
    args = parser.parse_args()
    bundle = assemble(args.inputs, v2_lineage.load_index(args.source_index), args.prior, stem=args.stem)
    print(json.dumps(emit(args.out, *bundle, stem=args.stem), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
