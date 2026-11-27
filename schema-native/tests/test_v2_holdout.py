import json
from zipfile import ZipFile

import pytest

from sn import v2_holdout as holdout


def test_nullable_and_local_reference_preserve_other_assertions():
    document = {"components": {"schemas": {"example": {
        "type": "string", "nullable": True, "enum": ["short"], "default": "short",
    }}}}
    schema = holdout.project_schema(document, {"$ref": "#/components/schemas/example"})
    assert schema["type"] == ["string", "null"]
    assert schema["default"] == "short"
    validator = holdout.BASE.validator(schema)
    assert validator.is_valid("short")
    assert not validator.is_valid(None)
    with pytest.raises(ValueError, match="external"):
        holdout.project_schema(document, {"$ref": "https://example.com/pointer"})


def test_schema_projection_rejects_both_members_of_exclusive_cursor_choice():
    source = {"allOf": [
        {"type": "object", "properties": {"before": {"type": "string"}, "after": {"type": "string"}}},
        {"oneOf": [{"required": ["before"]}, {"required": ["after"]}]},
    ]}
    schema = holdout.project_schema({}, source)
    validator = holdout.BASE.validator(schema)
    assert validator.is_valid({"after": "cursor"})
    assert not validator.is_valid({"before": "one", "after": "two"})


def test_review_zip_and_gold_have_separate_paths(tmp_path):
    task = {"task_id": "fixture", "request": "Find an entry", "system_policy": "Use the supplied tool",
            "tools": [{"name": "find_entry", "description": "Find an entry", "parameters": {"type": "object"}}]}
    gold = {"task_id": "fixture", "tool": "find_entry", "arguments": {"id": "private-gold"}}
    out = tmp_path / "bundle"
    holdout.emit(out, [task], [gold], {"UPSTREAM-LICENSE": b"sample notice"}, {})
    review = next((out / "review").glob("*.zip"))
    with ZipFile(review) as archive:
        assert set(archive.namelist()) == {"tasks.jsonl", "REVIEW_INSTRUCTIONS.md", "UPSTREAM-LICENSE"}
        assert json.loads(archive.read("tasks.jsonl")) == task
        assert b"private-gold" not in archive.read("tasks.jsonl")
    assert json.loads((out / "sealed/gold.jsonl").read_text()) == gold
    with pytest.raises(FileExistsError):
        holdout.emit(out, [task], [gold], {}, {})
