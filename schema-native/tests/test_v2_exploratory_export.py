import json

import pytest

from sn import v2_exploratory_export as export


def test_export_accepts_only_visible_inputs_and_preserves_proposed_runtime_parameters():
    row = {"request_id": "example", "task_id": "example-task", "request": "Retrieve the receipt.",
           "system_policy": "Return one call.", "tools": [{"name": "get_receipt"}],
           "catalog_serialization": "compact", "prompt_tokens": 155}
    profile = {"server_args": ["-c", "9216"], "request_params": {"max_tokens": 512, "temperature": 0}}
    freeze = {"requests": 1, "context_tokens": 9216, "output_reserve_tokens": 512}

    def build(task):
        return list(export.inference_payloads([task], profile, freeze))

    item, = build(row)
    assert set(item) == {"request_id", "expected_prompt_tokens", "payload"}
    assert item["payload"]["cache_prompt"] is False
    assert item["payload"]["max_tokens"] == 512
    assert item["payload"]["messages"][1]["content"] == row["request"]
    assert json.loads(item["payload"]["messages"][0]["content"].split("\n")[-1]) == row["tools"]
    with pytest.raises(ValueError, match="visible fields"):
        build({**row, "arguments": {"secret": "gold"}})
    with pytest.raises(ValueError, match="exceeds context"):
        build({**row, "prompt_tokens": 8800})


def test_export_verifies_bytes_and_refuses_overwrite(tmp_path):
    out = tmp_path / "inference-packet"
    artifacts = {"requests.jsonl": b"{}\n", "manifest.json": b"{}\n"}
    export.write(out, artifacts, verify=False)
    export.write(out, artifacts, verify=True)
    with pytest.raises(FileExistsError):
        export.write(out, artifacts, verify=False)
    (out / "manifest.json").write_bytes(b'{"modified":true}\n')
    with pytest.raises(ValueError, match="Inference export differs"):
        export.write(out, artifacts, verify=True)
