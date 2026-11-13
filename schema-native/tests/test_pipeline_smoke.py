"""End-to-end smoke test with fake endpoints. Exercises code paths only; produces no results."""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import jsonschema

from sn import envelope as env
from sn import mlxdata, paths, report, synth
import schema_utils as su

sys.path.insert(0, os.path.join(paths.EXP, "tests"))
import fake_server  # the experiment's own smoke-test server  # noqa: E402

SEEN = []


class Recording(fake_server.H):
    def do_POST(self):
        n = int(self.headers["Content-Length"])
        raw = self.rfile.read(n)
        SEEN.append(json.loads(raw))
        import io
        self.rfile = io.BytesIO(raw)
        super().do_POST()


def _serve(handler):
    srv = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def test_runner_sends_envelope_only_for_constrained_arms_and_report_runs(tmp_path, monkeypatch):
    srv, url = _serve(Recording)
    monkeypatch.setattr(paths, "RUNS", str(tmp_path / "runs"))
    monkeypatch.setattr(paths, "ANALYSIS", str(tmp_path / "analysis"))
    from sn import run as sn_run
    monkeypatch.setattr(sys, "argv", ["sn.run", "--config", "configs/runs/smoke.json", "--server", url, "--run-id", "_smoke"])
    SEEN.clear()
    sn_run.main()
    sn_run.main()  # actual resume must add no duplicate rows
    srv.shutdown()
    rows = paths.jsonl(str(tmp_path / "runs" / "_smoke" / "results.jsonl"))
    assert len(rows) == 2 * (5 + 5)                      # 2 arms x (5 select + 5 arggen) tasks of replicate 0
    free = [p for p in SEEN if "response_format" not in p]
    cd = [p for p in SEEN if "response_format" in p]
    assert len(free) == len(cd) == 10
    pool = paths.pool()
    tasks = {t["prompt"]: t for t in paths.tasks()}
    for p in cd:
        schema = p["response_format"]["json_schema"]["schema"]
        jsonschema.Draft7Validator.check_schema(schema)
        t = tasks[p["messages"][1]["content"].split("\n\nUse the tool")[0]]
        call = env.gold_call(t, su.load_schema(pool[t["tool_id"]]["schema_id"]))
        assert not list(jsonschema.Draft7Validator(schema).iter_errors(call))
    assert {r["decoding"] for r in rows} == {"free", "constrained"}
    # resumable: a second invocation adds nothing
    monkeypatch.setattr(sys, "argv", ["sn.run", "--config", "configs/runs/smoke.json", "--server", url, "--run-id", "_smoke"])
    res = report.run("_smoke")
    assert res["n"] == 20 and res["comparisons"]
    assert os.path.exists(tmp_path / "analysis" / "_smoke" / "REPORT.md")


class Teacher(BaseHTTPRequestHandler):
    """Fake teacher: first call returns a tool card, second call echoes the same arguments."""
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        sysmsg = body["messages"][0]["content"]
        if sysmsg.startswith("You write test data"):
            out = {"tool_name": "set_widget_size", "description": "Set the size of a widget on the page.",
                   "request": "Please make the widget 3 wide, thanks a lot.", "arguments": Teacher.args}
        else:
            out = {"tool": "set_widget_size", "arguments": Teacher.second or Teacher.args}
        b = json.dumps({"choices": [{"message": {"content": json.dumps(out)}, "finish_reason": "stop"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def test_synth_filters_and_mlx_rows(tmp_path, monkeypatch):
    schema = {"type": "object", "properties": {"width": {"type": "integer", "minimum": 1}}, "required": ["width"]}
    monkeypatch.setattr(su, "load_schema", lambda sid: schema)
    srv, url = _serve(Teacher)
    row = {"schema_id": "X/a", "family": "F1", "split": "train", "stratum": "flat"}
    params = {"temperature": 0.0}
    Teacher.args, Teacher.second = {"width": 3}, None
    ex, audit = synth.make_example(url, row, 0, params)
    assert audit["reason"] == "kept" and ex["gold_args"] == {"width": 3}
    Teacher.args = {"width": 0}                               # violates minimum
    assert synth.make_example(url, row, 0, params)[1]["reason"] == "arguments_invalid_against_raw_schema"
    Teacher.args, Teacher.second = {"width": 3}, {"width": 4}  # second pass disagrees
    assert synth.make_example(url, row, 0, params)[1]["reason"] == "round_trip_disagrees"
    srv.shutdown()
    assert synth.leaks_name("please run set widget size now", "set_widget_size")
    ex2 = dict(ex, example_id="X/b#0", schema_id="X/b", family="F2", tool_name="other_tool")
    rows = mlxdata.build_split([ex, ex2], "minified", [3], seed=1)
    m = rows[0]["messages"]
    assert [x["role"] for x in m] == ["system", "user", "assistant"]
    assert json.loads(m[2]["content"]) == {"tool": "set_widget_size", "arguments": {"width": 3}}
    assert '"name":"other_tool"' in m[0]["content"] and "\n  " not in m[0]["content"].split("Available tools:")[1].split("Respond")[0].strip()


def test_infrastructure_errors_are_not_model_failures():
    from sn.run import error_kind
    assert error_kind(401, {"error": "auth"}, "constrained") == "http_error"
    assert error_kind(500, {"error": "server"}, "constrained") == "http_error"
    assert error_kind(400, {"error": "grammar refused schema"}, "constrained") == "engine_error"
    assert error_kind(400, {"error": "context too large"}, "constrained") == "context_error"
    assert error_kind(0, {"error": "offline"}, "free") == "transport_error"
    from evaluate import evaluate
    task = paths.tasks()[0]
    ev = evaluate("", task, {}, set())
    c = report.cell([{"http_status": 400, "engine_error": True, "request_error": "engine_error",
                     "eval": ev, "usage": {}, "wall_latency_ms": 1}])
    assert c["engine_errors"] == 1 and sum(c["classes"].values()) == 0
