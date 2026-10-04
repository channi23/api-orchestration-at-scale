"""SMOKE-TEST ONLY fake llama-server. Produces synthetic outputs (gold or perturbed) to exercise
run.py / count_tokens.py / analyze.py end to end without a model. Never used for results.

python tests/fake_server.py --port 8081
"""
import argparse
import hashlib
import json
import os
import random
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import schema_utils as su  # noqa: E402

TASKS = [json.loads(l) for l in open(os.path.join(su.EXP, "tasks", "tasks.v1.jsonl"))]
BY_PROMPT = {t["prompt"]: t for t in TASKS}
POOL = [json.loads(l) for l in open(os.path.join(su.EXP, "dataset", "tool_pool.v1.jsonl"))]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        if self.path == "/props":
            return self._send(200, {"model_path": "FAKE-SMOKE-TEST", "n_ctx": 32768, "total_slots": 1})
        self._send(404, {})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/tokenize":
            return self._send(200, {"tokens": list(range(max(1, len(body["content"]) // 3)))})
        msgs = body["messages"]
        sysp, user = msgs[0]["content"], msgs[1]["content"]
        n_in = len(sysp) // 3 + len(user) // 3
        if n_in > 32768:
            return self._send(400, {"error": {"message": "the request exceeds the available context size"}})
        prompt = user.split("\n\nUse the tool")[0]
        t = BY_PROMPT[prompt]
        rng = random.Random(hashlib.sha256((sysp[:2000] + user).encode()).hexdigest())
        r = rng.random()
        if r < 0.6:
            out = {"tool": t["tool_name"], "arguments": t["gold_args"]}
        elif r < 0.75:
            out = {"tool": rng.choice(POOL)["tool_name"], "arguments": t["gold_args"]}
        elif r < 0.85:
            a = dict(t["gold_args"]); a.pop(next(iter(a)))
            out = {"tool": t["tool_name"], "arguments": a}
        elif r < 0.95:
            out = {"tool": t["tool_name"], "arguments": {k: "x" for k in t["gold_args"]}}
        else:
            out = "Sorry, I am not sure."
        content = out if isinstance(out, str) else json.dumps(out)
        self._send(200, {"choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": n_in, "completion_tokens": len(content) // 3},
                         "timings": {"prompt_n": n_in, "prompt_ms": n_in / 200 * 1000, "predicted_n": len(content) // 3,
                                     "predicted_ms": len(content) / 3 / 25 * 1000, "cache_n": 0}})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8081)
    HTTPServer(("127.0.0.1", ap.parse_args().port), H).serve_forever()
