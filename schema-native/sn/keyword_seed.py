"""Development-only assertion-keyword seeds. No inference or training entry point.

Assistant-authored synthetic contracts, not real APIs or independent held-out tasks.
Generated pairs preserve their declared cross-validity matrices and valid-wrong witnesses.
"""
import argparse
import copy
import json
from importlib.metadata import version
from pathlib import Path
import subprocess
import zipfile

from . import v2_authoring as common


DATA = Path(common.paths.DATA, "v2-keyword-seed-v0.1")
DIALECT = "https://json-schema.org/draft/2020-12/schema"
TF = [True, False, False, True]
TT = [True, True, True, True]


def obj(props, required, closed=True):
    result = {"type": "object", "properties": props, "required": required}
    if closed:
        result["additionalProperties"] = False
    return result


def replace(schema, path, value):
    result = copy.deepcopy(schema)
    node = result
    tokens = path.lstrip("/").split("/")
    for token in tokens[:-1]:
        token = token.replace("~1", "/").replace("~0", "~")
        node = node[int(token)] if isinstance(node, list) else node[token]
    token = tokens[-1].replace("~1", "/").replace("~0", "~")
    node[int(token) if isinstance(node, list) else token] = copy.deepcopy(value)
    return result


def pointer(schema, path):
    node = schema
    for token in path.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        node = node[int(token)] if isinstance(node, list) else node[token]
    return node


def cases():
    rows = []
    def add(key, family, request, s, s2, g, g2, wrong, wrong2, matrix=TF, edit=None, proof=None):
        rows.append({"pair_id": key, "family_id": family, "track": "assertion_keywords",
                     "source_group": "assistant-authored-development-seeds", "split": "development_only",
                     "tool_name": "submit_" + key.lower(), "request": request,
                     "schema_S": {"$schema": DIALECT, **s}, "schema_S2": {"$schema": DIALECT, **s2},
                     "gold_S": g, "gold_S2": g2, "valid_wrong_S": wrong, "valid_wrong_S2": wrong2,
                     "expected_matrix": matrix, "edit_path": edit, "proof": proof,
                     "pair_kind": "equivalent_rewrite" if proof else "validity_separable" if matrix == TF else "asymmetric_edit",
                     "approved_for_test": False})
    text = {"type": "string"}
    contact = obj({"id": text, "email": text, "phone": text}, ["id", "email"])
    add("K01", "contact_requirements", "Submit id C01. Email is nia@example.com and phone is 555-0104. Include only the contact field required by the schema.",
        contact, replace(contact, "/required", ["id", "phone"]),
        {"id": "C01", "email": "nia@example.com"}, {"id": "C01", "phone": "555-0104"},
        {"id": "C01", "email": "nia@example.com", "phone": "555-0104"},
        {"id": "C01", "email": "nia@example.com", "phone": "555-0104"}, edit="/required")
    mode = obj({"id": text, "mode": {"type": "string", "enum": ["economy", "priority"]}}, ["id", "mode"])
    add("K02", "ranked_modes", "Submit id S02 using the cheapest allowed service. The price ranking is economy, then priority, then express, from cheapest to most expensive.",
        mode, replace(mode, "/properties/mode/enum", ["priority", "express"]),
        {"id": "S02", "mode": "economy"}, {"id": "S02", "mode": "priority"},
        {"id": "S02", "mode": "priority"}, {"id": "S02", "mode": "express"},
        matrix=[True, False, True, True], edit="/properties/mode/enum")
    a = {"properties": {"a": {"const": True}}, "required": ["a"]}
    b = {"properties": {"b": {"const": True}}, "required": ["b"]}
    permissions = obj({"id": text, "a": {"type": "boolean"}, "b": {"type": "boolean"}, "exception": {"type": "boolean"}}, ["id"])
    s = {**copy.deepcopy(permissions), "oneOf": [a, b]}
    request = "Submit id P03. Include a and b, each true, if that combination validates; otherwise include only a=true. Do not include exception."
    add("K03", "permission_preference", request, s, replace(s, "/oneOf/1/required", ["b", "exception"]),
        {"id": "P03", "a": True}, {"id": "P03", "a": True, "b": True},
        {"id": "P03", "b": True}, {"id": "P03", "a": True},
        matrix=[True, True, False, True], edit="/oneOf/1/required")
    s = {**copy.deepcopy(permissions), "anyOf": [copy.deepcopy(a), copy.deepcopy(b)]}
    branches = [{**copy.deepcopy(a), "not": {"required": ["b"]}}, {**copy.deepcopy(b), "not": {"required": ["a"]}}]
    add("K04", "permission_preference", request.replace("P03", "P04"), s, replace(s, "/anyOf", branches),
        {"id": "P04", "a": True, "b": True}, {"id": "P04", "a": True},
        {"id": "P04", "b": True}, {"id": "P04", "b": True},
        matrix=[True, False, True, True], edit="/anyOf")
    s = obj({"id": text, "zone": {"enum": ["A", "B"]}, "tax_id": text, "customs_token": text}, ["id", "zone"])
    s.update({"if": {"properties": {"zone": {"const": "A"}}, "required": ["zone"]},
              "then": {"required": ["tax_id"]}, "else": {"required": ["customs_token"]}})
    add("K05", "contact_requirements", "Submit id D05 for zone A. Use tax_id TX5 and customs_token CT5 only when the schema requires that field; omit the other field.",
        s, replace(s, "/if/properties/zone/const", "B"),
        {"id": "D05", "zone": "A", "tax_id": "TX5"}, {"id": "D05", "zone": "A", "customs_token": "CT5"},
        {"id": "D05", "zone": "A", "tax_id": "TX5", "customs_token": "CT5"},
        {"id": "D05", "zone": "A", "tax_id": "TX5", "customs_token": "CT5"}, edit="/if/properties/zone/const")
    for key, dep in (("K06", "dependentRequired"), ("K07", "dependentSchemas")):
        s = obj({"id": text, "account_id": text, "email": text, "phone": text}, ["id", "account_id"])
        s[dep] = {"account_id": ["email"] if dep == "dependentRequired" else {"required": ["email"]}}
        path = "/" + dep + "/account_id" + ("/required" if dep == "dependentSchemas" else "")
        base = {"id": key, "account_id": "acct-7"}
        add(key, "contact_requirements", "Submit id " + key + " for account_id acct-7. Email is nia@example.com and phone is 555-0104. Include only the additional contact field required for this account.",
            s, replace(s, path, ["phone"]), {**base, "email": "nia@example.com"}, {**base, "phone": "555-0104"},
            {**base, "email": "nia@example.com", "phone": "555-0104"}, {**base, "email": "nia@example.com", "phone": "555-0104"}, edit=path)
    s = obj({"pair": {"type": "array", "prefixItems": [{"type": "string", "enum": ["alpha", "beta"]}, {"type": "integer", "enum": [1, 2]}], "items": False, "minItems": 2}}, ["pair"])
    add("K08", "typed_tuple", "Encode tag beta and count 2 in the two array positions whose types the schema defines. Keep the tag a string and the count a number.",
        s, replace(s, "/properties/pair/prefixItems", list(reversed(s["properties"]["pair"]["prefixItems"]))),
        {"pair": ["beta", 2]}, {"pair": [2, "beta"]}, {"pair": ["alpha", 1]}, {"pair": [1, "alpha"]}, edit="/properties/pair/prefixItems")
    address = obj({"postal_code": text, "country": {"enum": ["US", "CA"]}}, ["postal_code", "country"])
    s = obj({"order": obj({"destination": obj({"address": {"$ref": "#/$defs/AddressAlias"}}, ["address"])}, ["destination"])}, ["order"])
    s["$defs"] = {"AddressAlias": {"$ref": "#/$defs/Address"}, "Address": address}
    s2 = replace(s, "/properties/order/properties/destination/properties/address", address)
    del s2["$defs"]
    g = {"order": {"destination": {"address": {"postal_code": "98101", "country": "US"}}}}
    w = copy.deepcopy(g); w["order"]["destination"]["address"]["country"] = "CA"
    add("K09", "nested_address_rewrite", "Submit an order destination address with postal_code 98101 and country US.",
        s, s2, g, copy.deepcopy(g), w, copy.deepcopy(w), matrix=TT, proof="local-address-chain-substitution")
    s = {"allOf": [obj({"name": text}, ["name"], False), obj({"units": {"type": "integer"}}, ["units"], False)]}
    s2 = obj({"name": text, "units": {"type": "integer"}}, ["name", "units"], False)
    add("K10", "open_object_intersection", "Submit name Cedar and units 2.", s, s2,
        {"name": "Cedar", "units": 2}, {"name": "Cedar", "units": 2}, {"name": "Other", "units": 2}, {"name": "Other", "units": 2},
        matrix=TT, proof="open-disjoint-object-intersection")
    s = obj({"mode": {"enum": ["economy", "priority", "express"]}}, ["mode"])
    s["not"] = {"properties": {"mode": {"const": "economy"}}, "required": ["mode"]}
    add("K11", "ranked_modes", "Choose the cheapest valid service: economy is cheapest, priority next, express most expensive.",
        s, replace(s, "/not/properties/mode/const", "priority"), {"mode": "priority"}, {"mode": "economy"},
        {"mode": "express"}, {"mode": "express"}, edit="/not/properties/mode/const")
    s = obj({"retries": {"type": "integer", "minimum": 0, "maximum": 5}}, ["retries"])
    add("K12", "bounded_budget", "Set retries to the largest integer allowed by the schema, without exceeding my budget of 9 retries.",
        s, replace(s, "/properties/retries/maximum", 7), {"retries": 5}, {"retries": 7}, {"retries": 4}, {"retries": 6},
        matrix=[True, True, False, True], edit="/properties/retries/maximum")
    s = obj({"values": {"type": "array", "items": {"enum": ["a", "b", "c"]}, "minItems": 1}}, ["values"])
    add("K13", "ordered_prefix", "Use the shortest valid prefix of the ordered list a, b, c. Do not skip or reorder entries.",
        s, replace(s, "/properties/values/minItems", 2), {"values": ["a"]}, {"values": ["a", "b"]},
        {"values": ["a", "b"]}, {"values": ["a", "b", "c"]}, matrix=[True, False, True, True], edit="/properties/values/minItems")
    s = obj({"id": text}, ["id"])
    add("K14", "supported_details", "Submit id M14. Include memo ready if the schema accepts an extra memo field; otherwise omit memo.",
        s, replace(s, "/additionalProperties", True), {"id": "M14"}, {"id": "M14", "memo": "ready"},
        {"id": "OTHER"}, {"id": "M14"}, matrix=[True, True, False, True], edit="/additionalProperties")
    s = obj({"values": {"type": "array", "items": {"type": "integer"}, "contains": {"multipleOf": 2}, "minContains": 1}}, ["values"])
    add("K15", "ordered_prefix", "Use the shortest valid prefix of the ordered list 2, 3, 4. Do not skip or reorder entries.",
        s, replace(s, "/properties/values/minContains", 2), {"values": [2]}, {"values": [2, 3, 4]},
        {"values": [2, 4]}, {"values": [2, 4]}, matrix=[True, False, True, True], edit="/properties/values/minContains")
    s = obj({"code": {"type": "string", "pattern": "^PK-[0-9]{2}$"}}, ["code"])
    add("K16", "identifier_choice", "Choose the first valid identifier from this ordered list: PK-12, PK-A9, PK-99.",
        s, replace(s, "/properties/code/pattern", "^PK-[A-Z][0-9]$"), {"code": "PK-12"}, {"code": "PK-A9"},
        {"code": "PK-99"}, {"code": "PK-B1"}, edit="/properties/code/pattern")
    return rows


def proof_check(pair):
    s, t = pair["schema_S"], pair["schema_S2"]
    if pair["proof"] == "local-address-chain-substitution":
        leaf = obj({"postal_code": {"type": "string"}, "country": {"enum": ["US", "CA"]}}, ["postal_code", "country"])
        expected_source = obj({"order": obj({"destination": obj({"address": {"$ref": "#/$defs/AddressAlias"}}, ["address"])}, ["destination"])}, ["order"])
        expected_source = {"$schema": DIALECT, **expected_source,
                           "$defs": {"AddressAlias": {"$ref": "#/$defs/Address"}, "Address": leaf}}
        if s != expected_source: return False
        path = "/properties/order/properties/destination/properties/address"
        expected = replace(s, path, s["$defs"]["Address"]); del expected["$defs"]
        return expected == t
    if pair["proof"] == "open-disjoint-object-intersection":
        expected_branches = [obj({"name": {"type": "string"}}, ["name"], False),
                             obj({"units": {"type": "integer"}}, ["units"], False)]
        if s != {"$schema": DIALECT, "allOf": expected_branches}: return False
        props = {}; required = []
        for branch in s["allOf"]:
            props.update(branch["properties"]); required += branch["required"]
        return {"$schema": DIALECT, **obj(props, required, False)} == t
    return replace(s, pair["edit_path"], pointer(t, pair["edit_path"])) == t


def negatives(schema, gold, other):
    candidates = [other, {}, None, []]
    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                changed = copy.deepcopy(gold); parent = changed
                for p in path: parent = parent[p]
                del parent[key]; candidates.append(changed)
                walk(value, path + [key])
        elif isinstance(node, list):
            for i, value in enumerate(node): walk(value, path + [i])
        else:
            for value in (None, "__INVALID__", {}, []):
                changed = copy.deepcopy(gold); parent = changed
                for p in path[:-1]: parent = parent[p]
                parent[path[-1]] = value; candidates.append(changed)
    walk(gold, [])
    validator = common.validator(schema)
    unique = {common.serialized(c): c for c in candidates if not validator.is_valid(c)}
    return [unique[k] for k in sorted(unique)]


def audit():
    pairs = cases(); checks = []
    for p in pairs:
        a, b = common.validator(p["schema_S"]), common.validator(p["schema_S2"])
        g, h = p["gold_S"], p["gold_S2"]
        matrix = [a.is_valid(g), b.is_valid(g), a.is_valid(h), b.is_valid(h)]
        if matrix != p["expected_matrix"] or not proof_check(p):
            raise ValueError("Cross-validity/edit proof mismatch: " + p["pair_id"])
        if p["proof"] and not common.argument_equal(g, h):
            raise ValueError("Equivalent rewrite changes gold")
        for validator, key, gold in ((a, "valid_wrong_S", g), (b, "valid_wrong_S2", h)):
            if not validator.is_valid(p[key]) or common.argument_equal(p[key], gold):
                raise ValueError("Invalid valid-wrong witness: " + p["pair_id"])
        checks.append({"pair_id": p["pair_id"], "matrix": matrix, "pair_kind": p["pair_kind"],
                       "edit_verified": True, "valid_wrong_witnesses_verified": 2,
                       "negative_counts": [len(negatives(p["schema_S"], g, h)), len(negatives(p["schema_S2"], h, g))]})
    return pairs, checks


def build():
    from collections import Counter
    pairs, checks = audit()
    summary = {"version": "v2-keyword-seed-v0.1", "pairs": len(pairs), "schema_units": 2 * len(pairs),
               "proposed_family_groups": len({p["family_id"] for p in pairs}), "pair_kinds": dict(Counter(p["pair_kind"] for p in pairs)),
               "checks": checks, "approved_test_intents": 0, "independent_reviews": 0,
               "status": "Development-only synthetic seeds, not a frozen or powered held-out dataset",
               "limits": ["Family groups are conservative author labels, not proof of independence.",
                          "Synthetic schema-conditioned preferences are not representative API traffic.",
                          "Equivalent examples share concepts with exposed stress-fixtures 0.4; no held-out novelty claim.",
                          "Engine support and tokenizer behavior require separate evidence."]}
    manifest = {"source_sha256": common.digest(Path(__file__).read_bytes()), "dialect": DIALECT,
                "validator_version": version("jsonschema"),
                "authoring": "assistant-authored development contracts; no additional model endpoint",
                "native_support_claimed": False, "inference_requests": 0, "training_runs": 0}
    return {"pairs.jsonl": "".join(common.serialized(p) + "\n" for p in pairs),
            "validation.json": json.dumps(summary, indent=2, sort_keys=True) + "\n",
            "manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n"}


def native_check(binary, library):
    from .native_audit import verified_build
    metadata = verified_build(binary, library)
    engine_commit = subprocess.check_output(["git", "-C", str(Path(library).parents[2]), "rev-parse", "HEAD"], text=True).strip()
    profile = json.loads(Path(common.paths.ROOT, "configs/model.qwen3-1.7b.sustainable.json").read_text())
    if engine_commit != profile["llguidance_commit"]:
        raise ValueError("Native engine source does not match pinned E0 profile")
    pairs, _ = audit(); requests = []; labels = []
    for p in pairs:
        for variant, other in (("S", "S2"), ("S2", "S")):
            schema = p["schema_" + variant]; gold = p["gold_" + variant]
            bad = negatives(schema, gold, p["gold_" + other])
            samples = [json.dumps(gold, ensure_ascii=False), *[json.dumps(v, ensure_ascii=False) for v in bad]]
            requests.append(json.dumps({"schema": schema, "samples": samples}))
            labels.append({"pair_id": p["pair_id"], "variant": variant, "negative_samples": bad,
                           "schema_sha256": common.su.sha(schema), "gold_sha256": common.su.sha(gold)})
    proc = subprocess.run([str(binary)], input="\n".join(requests) + "\n", text=True, capture_output=True, timeout=60, check=True)
    results = [json.loads(line) for line in proc.stdout.splitlines()]
    if len(results) != len(labels):
        raise ValueError("Native helper response count mismatch")
    evidence = []
    for label, result in zip(labels, results):
        accepts = result.get("accepts", [])
        if result["compile_ok"] and (len(accepts) != 1 + len(label["negative_samples"]) or any(type(v) is not bool for v in accepts)):
            raise ValueError("Malformed native acceptance evidence")
        evidence.append({**label, "compile_ok": result["compile_ok"], "error": result.get("error"),
                         "gold_accepted": accepts[0] if accepts else False,
                         "invalid_accepted": [value for value, accepted in zip(label["negative_samples"], accepts[1:]) if accepted]})
    return {"kind": "Hash-verified bundled engine with byte tokenizer; no server, model weights or GPU",
            "engine_commit": engine_commit, "engine_version": profile["llguidance_version"],
            "pairs_sha256": common.digest("".join(common.serialized(p) + "\n" for p in pairs).encode()),
            "helper_sha256": metadata["helper_sha256"], "library_sha256": metadata["library_sha256"],
            "compiled": sum(r["compile_ok"] for r in evidence), "schema_units": len(evidence),
            "gold_accepted": sum(r["gold_accepted"] for r in evidence),
            "invalid_accepted": sum(len(r["invalid_accepted"]) for r in evidence), "evidence": evidence,
            "invalid_probes_checked_on_compiled_schemas": sum(len(r["negative_samples"]) for r in evidence if r["compile_ok"]),
            "invalid_probes_offered_total": sum(len(r["negative_samples"]) for r in evidence),
            "limits": "Finite probes only; no model-tokenizer or actual inference guarantee; no schema was relaxed."}


def review_packet():
    from .v2_v03 import load
    policy = load()[-1]; packets = []
    for p in cases():
        for variant in ("S", "S2"):
            packets.append({"task_id": "KSEED_" + common.digest((p["pair_id"] + ":" + variant).encode())[:12],
                            "request": p["request"], "system_policy": policy,
                            "tools": [{"name": p["tool_name"], "description": "Submit the requested synthetic form using the supplied schema. This is an offline development contract.",
                                       "parameters": p["schema_" + variant]}]})
    return sorted(packets, key=lambda p: p["task_id"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "native", "export-review"])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.command == "audit":
        for name, text in build().items():
            path = DATA / name
            if args.check:
                if not path.exists() or path.read_text() != text: raise SystemExit("Artifact differs: " + name)
            else: path.write_text(text)
        print("PASS: keyword matrices, edit checks and valid-wrong witnesses; development only")
    elif args.command == "native":
        if args.out is None: parser.error("native requires --out")
        if args.out.exists(): raise SystemExit("Refusing to overwrite native evidence")
        root = Path(common.paths.ROOT, ".tools")
        result = native_check(root / "native-llg-audit", root / "llama.cpp/build-metal/llguidance/source/target/release/libllguidance.a")
        with args.out.open("x") as stream: stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print({k: result[k] for k in ("compiled", "schema_units", "gold_accepted", "invalid_accepted")})
    else:
        if args.out is None: parser.error("export-review requires --out")
        with zipfile.ZipFile(args.out, "x", compression=zipfile.ZIP_DEFLATED) as z:
            for name, text in {"tasks.jsonl": "".join(common.serialized(p) + "\n" for p in review_packet()),
                               "REVIEW_INSTRUCTIONS.md": (DATA / "FRESH_REVIEW_INSTRUCTIONS.md").read_text()}.items():
                info = zipfile.ZipInfo(name, date_time=(2026, 11, 25, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, text)
        print("Wrote blind synthetic keyword review; no gold, inference or approval")


if __name__ == "__main__":
    main()
