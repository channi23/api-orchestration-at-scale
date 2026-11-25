import pytest

from sn import v2_digitalocean as pilot


def test_resolves_relative_file_then_local_json_pointer(monkeypatch):
    tree = pilot.SourceTree(None)
    origin = "specification/resources/metrics.yml"
    docs = {origin: {"schemas": {"a/b": {"type": "string"}}}}
    monkeypatch.setattr(tree, "load", docs.__getitem__)
    result, path = tree.resolve({"$ref": "./resources/metrics.yml#/schemas/a~1b"}, pilot.ROOT)
    assert path == origin
    assert result == {"type": "string"}


def test_reference_resolution_rejects_remote_escape_and_cycles(monkeypatch):
    tree = pilot.SourceTree(None)
    with pytest.raises(ValueError, match="relative"):
        tree.resolve({"$ref": "https://example.com/params.yml"}, pilot.ROOT)
    with pytest.raises(ValueError, match="outside"):
        tree.resolve({"$ref": "../%2e%2e/params.yml"}, pilot.ROOT)
    monkeypatch.setattr(tree, "load", lambda _: {"cycle": {"$ref": "#/cycle"}})
    with pytest.raises(ValueError, match="cycle"):
        tree.resolve({"$ref": "#/cycle"}, pilot.ROOT)


def test_projection_preserves_annotation_and_does_not_encode_prose_as_an_assertion():
    path = "/v2/droplets"
    op = {"path": path, "operation_id": "droplets_list"}
    root = {"paths": {path: {"get": {"operationId": "droplets_list", "parameters": [
        {"name": "tag_name", "in": "query", "description": "Cannot be combined with name.",
         "schema": {"type": "string"}},
        {"name": "name", "in": "query", "schema": {"type": "string"}},
        {"name": "per_page", "in": "query",
         "schema": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20}},
    ]}}}}
    schema, locations, _ = pilot.operation_schema(pilot.SourceTree(None), root, op)
    assert locations == {"tag_name": "query", "name": "query", "per_page": "query"}
    assert schema["properties"]["tag_name"]["description"] == "Cannot be combined with name."
    assert schema["properties"]["per_page"]["default"] == 20
    validator = pilot.BASE.validator(schema)
    arguments = {"tag_name": "batch"}
    assert validator.is_valid(arguments)
    assert arguments == {"tag_name": "batch"}
    assert validator.is_valid({**arguments, "name": "example"})
    assert not validator.is_valid({**arguments, "per_page": 201})
