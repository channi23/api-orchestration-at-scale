import pytest

from sn import v2_holdout, v2_swagger_inputs as inputs


def test_swagger_array_and_path_assertions_are_preserved():
    selector = {"path": "/results/{slug}", "operation_id": "list_results"}
    document = {"swagger": "2.0", "paths": {selector["path"]: {"get": {
        "operationId": "list_results", "parameters": [
            {"name": "slug", "in": "path", "required": True, "type": "string", "pattern": "^[a-z]+$"},
            {"name": "ids", "in": "query", "collectionFormat": "csv", "type": "array",
             "items": {"type": "integer", "multipleOf": 2}, "uniqueItems": True},
        ],
    }}}}
    schema = inputs.project_operation(document, selector)
    validator = v2_holdout.BASE.validator(schema)
    assert validator.is_valid({"slug": "tour", "ids": [2, 6]})
    assert not validator.is_valid({"slug": "tour", "ids": [2, 2]})
    assert not validator.is_valid({"slug": "tour", "ids": [3]})
    assert not validator.is_valid({"ids": [2]})

    document["paths"][selector["path"]]["get"]["parameters"].append(
        {"name": "Authorization", "in": "header", "type": "string"}
    )
    with pytest.raises(ValueError, match="Unsupported or repeated Swagger 2 parameter"):
        inputs.project_operation(document, selector)


def test_openapi31_subset_refuses_nullable_without_changing_atomic_bounds():
    selector = {"path": "/coordinates", "operation_id": "lookup"}
    schema = {"type": "number", "minimum": -90, "maximum": 90, "multipleOf": 0.25}
    document = {"openapi": "3.1.2", "paths": {selector["path"]: {"get": {
        "operationId": "lookup", "parameters": [{"name": "latitude", "in": "query", "schema": schema}],
    }}}}
    validator = v2_holdout.BASE.validator(inputs.project_openapi31(document, selector))
    assert validator.is_valid({"latitude": 40.25})
    assert not validator.is_valid({"latitude": 40.21})
    schema["nullable"] = True
    with pytest.raises(ValueError, match="dialect-specific"):
        inputs.project_openapi31(document, selector)
