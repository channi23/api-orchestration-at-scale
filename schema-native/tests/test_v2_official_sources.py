import copy
import json

import pytest

from sn import v2_official_sources as official


def test_projection_preserves_nested_arguments_and_omits_the_local_only_field():
    created = {
        "anyOf": [
            {"type": "object", "properties": {"gte": {"type": "integer"}}},
            {"type": "integer"},
        ]
    }
    spec = {"paths": {"/items/{id}": {
        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
        "get": {"operationId": "getItems", "requestBody": official.EMPTY_FORM_BODY, "parameters": [
            {"name": "created", "in": "query", "schema": created},
            {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Only available locally"},
        ]},
    }}}
    op = {"path": "/items/{id}", "operation_id": "getItems", "omit_local_only": ["q"]}
    schema, locations = official.project(spec, op)
    assert locations == {"id": "path", "created": "query"}
    assert schema["required"] == ["id"]
    assert schema["properties"]["created"] == created
    validator = official.BASE.validator(schema)
    assert validator.is_valid({"id": "example", "created": {"gte": 31}})
    assert validator.is_valid({"id": "example", "created": 31})
    assert not validator.is_valid({"id": "example", "created": {"gte": "31"}})
    assert not validator.is_valid({"id": "example", "q": "should not appear"})


def test_projection_rejects_required_body_and_unsupported_openapi_nullable():
    op = {"path": "/items", "operation_id": "getItems"}
    body = copy.deepcopy(official.EMPTY_FORM_BODY)
    body["required"] = True
    get = {"operationId": "getItems", "requestBody": body}
    spec = {"paths": {"/items": {"get": get}}}
    with pytest.raises(ValueError, match="request body"):
        official.project(spec, op)
    del get["requestBody"]
    get["parameters"] = [{"name": "x", "in": "query", "schema": {"type": "string", "nullable": True}}]
    with pytest.raises(ValueError, match="nullable"):
        official.project(spec, op)


def test_blind_export_contains_visible_task_and_license_notices(tmp_path):
    from zipfile import ZipFile

    output = tmp_path / "packet.zip"
    task = {"task_id": "visible-task", "request": "Query the weather", "tools": [],
            "system_policy": "Use the supplied fields"}
    official.archive(output, [task], {"upstream-license.txt": b"verbatim notice"})
    with ZipFile(output) as packet:
        assert set(packet.namelist()) == {"tasks.jsonl", "REVIEW_INSTRUCTIONS.md", "upstream-license.txt"}
        assert json.loads(packet.read("tasks.jsonl")) == task
        assert packet.read("upstream-license.txt") == b"verbatim notice"
