"""Project read-only Swagger 2 path/query inputs into the benchmark JSON contract."""

from . import v2_holdout as intake


PARAMETER_METADATA = {"name", "in", "required", "collectionFormat", "allowEmptyValue"}


def project_operation(document, selector):
    if document.get("swagger") != "2.0":
        raise ValueError("Expected a Swagger 2.0 source")
    item, _ = intake.dereference(document, document["paths"][selector["path"]])
    get, _ = intake.dereference(document, item["get"])
    if get.get("operationId") != selector["operation_id"]:
        raise ValueError("Operation ID differs from the pinned source")

    merged = {}
    for scope in (item.get("parameters", []), get.get("parameters", [])):
        seen = set()
        for entry in scope:
            param, chain = intake.dereference(document, entry)
            key = (param["in"], param["name"])
            if (key in seen or key[0] not in {"path", "query"} or "schema" in param
                    or ("collectionFormat" in param and param["type"] != "array")
                    or (key[0] == "path" and not param.get("required"))):
                raise ValueError(f"Unsupported or repeated Swagger 2 parameter: {key}")
            if param.get("collectionFormat", "csv") not in {"csv", "ssv", "tsv", "pipes", "multi"}:
                raise ValueError(f"Unsupported array wire encoding: {key}")
            seen.add(key)
            schema = {k: v for k, v in param.items() if k not in PARAMETER_METADATA}
            if schema.get("type") not in {"string", "boolean", "number", "integer", "array"}:
                raise ValueError(f"Unsupported Swagger parameter type: {key}")
            merged[key] = (intake.project_schema(document, schema, chain), param.get("required", False))

    properties, required = {}, []
    for (_, name), (schema, is_required) in merged.items():
        if name in properties:
            raise ValueError(f"Ambiguous argument name: {name}")
        properties[name] = schema
        if is_required:
            required.append(name)
    return {"$schema": intake.official.DIALECT, "type": "object", "properties": properties,
            "required": required, "additionalProperties": False}


def project_openapi31(document, selector):
    """Use the shared OpenAPI projector only for the common 3.0/3.1 assertion subset."""
    item, _ = intake.dereference(document, document["paths"][selector["path"]])
    get, _ = intake.dereference(document, item["get"])

    def reject_dialect_changes(node, chain=()):
        if not isinstance(node, dict):
            return
        node, chain = intake.dereference(document, node, chain)
        if {"nullable", "exclusiveMinimum", "exclusiveMaximum"} & node.keys():
            raise ValueError("OpenAPI 3.1 parameter uses a dialect-specific keyword")
        for key in ("properties", "items", "additionalProperties", "allOf", "oneOf", "anyOf"):
            if key not in node:
                continue
            value = node[key]
            children = value.values() if key == "properties" else value if isinstance(value, list) else (value,)
            for child in children:
                reject_dialect_changes(child, chain)

    for node in (item, get):
        for entry in node.get("parameters", []):
            param, _ = intake.dereference(document, entry)
            reject_dialect_changes(param.get("schema"))
    return intake.project_operation(document, selector)
