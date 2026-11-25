"""Prepare or execute one reviewed, capped development-only free-decoding pilot."""

import argparse
from collections import Counter
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
from queue import Empty, Queue
import signal
import socket
from statistics import median
import subprocess
from threading import Thread
import time
from zipfile import ZipFile

from . import e0b, e0b_resources, paths, preflight, provenance, resources, router, run
from . import v2_authoring as base


ROOT = Path(paths.ROOT)
CONFIG = ROOT / "configs/runs/v2_dev_free.json"
PROFILE = ROOT / "configs/model.qwen3-1.7b.sustainable.json"
LLAMA = ROOT / ".tools/llama.cpp"
SOURCE_TEMPLATE = ROOT / "analysis/e0-clean-v1/manifest.public.json"


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def checked(path, expected):
    data = path.read_bytes()
    if base.digest(data) != expected:
        raise ValueError(f"Pinned file changed: {path.name}")
    return data


def rows_by_id(data):
    rows = [base.strict_loads(line) for line in data.decode().splitlines() if line.strip()]
    indexed = {row["task_id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Input has repeated task IDs")
    return indexed


def inputs(outputs, config):
    units = []
    for source in config["sources"]:
        receipt = outputs / source["receipt_dir"]
        checked(receipt / "adjudication-receipt.json", source["adjudication_receipt_sha256"])
        gold = rows_by_id(checked(receipt / "gold.jsonl", source["gold_sha256"]))
        packet = checked(outputs / source["packet"], source["packet_sha256"])
        with ZipFile(io.BytesIO(packet)) as archive:
            visible = rows_by_id(archive.read("tasks.jsonl"))
        if set(visible) != set(gold):
            raise ValueError("Review packet and gold IDs do not agree")
        for task_id in source["task_ids"]:
            task = visible[task_id]
            answer = gold[task_id]
            if set(task) != {"task_id", "request", "system_policy", "tools"} or set(answer) != {
                "task_id", "tool", "arguments"
            }:
                raise ValueError("Expected the reviewed visible and gold fields")
            tools = task["tools"]
            if any(set(item) != {"name", "description", "parameters"} for item in tools):
                raise ValueError("Unexpected model-visible tool fields")
            schemas = {tool["name"]: tool["parameters"] for tool in tools}
            if len(tools) != 5 or len(schemas) != 5:
                raise ValueError("Expected five distinct selected tools")
            for schema in schemas.values():
                base.validator(schema)
            base.validator(schemas[answer["tool"]]).validate(answer["arguments"])
            units.append({"task_id": task_id, "group": source["group"], "visible": task, "gold": answer})
    if len(units) != config["generation_cap"] or len({row["task_id"] for row in units}) != len(units):
        raise ValueError("Development task count differs from the hard cap")
    return units


def model_path(profile):
    return ROOT / "models" / profile["gguf_file"]


def template_sha():
    template = json.loads(SOURCE_TEMPLATE.read_text())["server_props"]["chat_template"]
    return provenance.digest(template)


def implementation(config_path=CONFIG, extra_files=()):
    modules = (e0b, e0b_resources, preflight, provenance, resources, router, run, base)
    files = (Path(__file__), *(Path(module.__file__) for module in modules), config_path, *extra_files)
    return {str(file.relative_to(ROOT)): provenance.file_sha(file) for file in files}


def build(outputs):
    config = json.loads(CONFIG.read_text())
    profile = json.loads(checked(PROFILE, config["profile_sha256"]))
    units = inputs(outputs, config)
    return {
        "config": config, "profile": profile, "units": units, "implementation_sha256": implementation(),
        "template_sha256": template_sha(),
        "runtime": preflight.runtime(profile, str(model_path(profile)), str(LLAMA)),
    }


def messages(task):
    catalog = json.dumps(task["tools"], ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    return [
        {"role": "system", "content": task["system_policy"] + "\n\nAvailable tools (JSON):\n" + catalog},
        {"role": "user", "content": task["request"]},
    ]


def payload(plan, task):
    return {
        **plan["profile"]["request_params"],
        "cache_prompt": plan["config"]["cache_prompt"],
        "messages": messages(task),
    }


def append(directory, filename, record):
    with (directory / filename).open("ab") as file:
        file.write((base.serialized(record) + "\n").encode())
        file.flush()
        os.fsync(file.fileno())


def score(unit, content, finish):
    if finish == "length":
        return {"outcome": "truncated"}
    try:
        call = router.strict_loads(content)
    except (ValueError, TypeError, RecursionError):
        return {"outcome": "malformed"}
    if not isinstance(call, dict) or set(call) != {"tool", "arguments"} or not isinstance(call["tool"], str):
        return {"outcome": "malformed"}
    gold = unit["gold"]
    schemas = {tool["name"]: tool["parameters"] for tool in unit["visible"]["tools"]}
    known = call["tool"] in schemas
    valid = known and base.validator(schemas[call["tool"]]).is_valid(call["arguments"])
    same_tool = call["tool"] == gold["tool"]
    if not same_tool:
        outcome = "wrong_tool"
    elif not valid:
        outcome = "schema_invalid_arguments"
    elif not base.argument_equal(call["arguments"], gold["arguments"]):
        outcome = "valid_wrong_arguments"
    else:
        outcome = "correct"
    return {"outcome": outcome, "tool_matches": same_tool, "known_tool": known, "schema_valid": valid}


def report(plan, results):
    expected = [row["task_id"] for row in plan["units"]]
    if [row["task_id"] for row in results] != expected:
        raise ValueError("Report requires all results in the frozen order")
    details = [{**score(u, r["content"], r["finish_reason"]), "task_id": r["task_id"],
                "elapsed_seconds": r["elapsed_seconds"], "usage": r["usage"]}
               for u, r in zip(plan["units"], results)]
    return {"scope": "development-only, descriptive", "request_count": len(results),
            "outcomes": dict(Counter(row["outcome"] for row in details)),
            "median_elapsed_seconds": median(row["elapsed_seconds"] for row in details),
            "total_usage": {key: sum(row["usage"][key] for row in details)
                            for key in ("prompt_tokens", "completion_tokens")},
            "tasks": details}


def request(send, guard, path, body=None):
    """Monitor an in-flight HTTP request. A warning exits and unloads the owned server."""
    result = Queue(maxsize=1)

    def fetch():
        try:
            result.put(send(path, body))
        except Exception as error:
            result.put(error)

    guard()
    Thread(target=fetch, daemon=True).start()
    while True:
        try:
            response = result.get(timeout=5)
        except Empty:
            guard()
            continue
        if isinstance(response, Exception):
            raise response
        code, content = response
        if code != 200 or not isinstance(content, dict):
            raise RuntimeError(f"{path} failed with HTTP status {code}")
        return content


def token_preflight(plan, post):
    props = post("/props")
    model = plan["profile"]
    n_ctx = props.get("default_generation_settings", {}).get("n_ctx")
    if n_ctx != int(model["server_args"][model["server_args"].index("-c") + 1]):
        raise RuntimeError("Running server context differs from the pinned profile")
    if model["llama_cpp_commit"][:7] not in str(props.get("build_info", "")):
        raise RuntimeError("Running server build does not match the pin")
    if Path(props.get("model_path", "")).resolve() != model_path(model).resolve():
        raise RuntimeError("Running model path does not match the pin")
    if provenance.digest(props.get("chat_template")) != plan["template_sha256"]:
        raise RuntimeError("Running chat template does not match the E0 profile")
    counts = {}
    for unit in plan["units"]:
        params = payload(plan, unit["visible"])
        rendered = post("/apply-template", {"messages": params["messages"], "add_generation_prompt": True,
                                             "chat_template_kwargs": params["chat_template_kwargs"]})
        if not isinstance(rendered.get("prompt"), str):
            raise RuntimeError("Template rendering returned no prompt")
        tokens = post("/tokenize", {"content": rendered["prompt"], "add_special": True}).get("tokens")
        if not isinstance(tokens, list) or not tokens or len(tokens) + params["max_tokens"] > n_ctx:
            raise RuntimeError(f"Token count or context check failed: {unit['task_id']}")
        counts[unit["task_id"]] = len(tokens)
    return {"context": n_ctx, "output_token_reserve": model["request_params"]["max_tokens"], "prompt_tokens": counts}


def generate(plan, directory, post, guard, *, cooldown=time.sleep, reporter=report):
    cfg = plan["config"]
    budget = e0b.Budget(directory / "request-budget.jsonl", benchmark_cap=cfg["generation_cap"], readiness_cap=0)
    results = []
    for index, unit in enumerate(plan["units"]):
        guard()
        budget.reserve("benchmark", unit["task_id"])
        started = time.monotonic()
        response = post("/v1/chat/completions", payload(plan, unit["visible"]))
        choices = response.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise RuntimeError("Expected exactly one completion")
        choice = choices[0]
        content = choice.get("message", {}).get("content")
        finish = choice.get("finish_reason")
        usage = response.get("usage")
        if not isinstance(content, str) or finish not in {"stop", "length"}:
            raise RuntimeError("Completion missing text or an expected finish reason")
        if not isinstance(usage, dict) or any(
            type(usage.get(key)) is not int or usage[key] < 0 for key in ("prompt_tokens", "completion_tokens")
        ):
            raise RuntimeError("Completion is missing token usage")
        result = {"task_id": unit["task_id"], "content": content, "finish_reason": finish, "usage": usage,
                  "elapsed_seconds": time.monotonic() - started}
        append(directory, "results.jsonl", result)
        results.append(result)
        guard()
        if index + 1 < len(plan["units"]):
            cooldown(cfg["request_cooldown_seconds"])
    return reporter(plan, results)


def port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


@contextmanager
def server(model, port, log):
    binary = LLAMA / "build-metal/bin/llama-server"
    if port_open(port):
        raise RuntimeError("Dedicated pilot port is already in use")
    cmd = [str(binary), "-m", str(model_path(model)), *model["server_args"], "--host", "127.0.0.1", "--port", str(port)]
    with log.open("xb") as stream:
        proc = subprocess.Popen(cmd, stdout=stream, stderr=stream, start_new_session=True)
        try:
            yield proc
        finally:
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait(timeout=10)


def launch(plan, *, config_path=CONFIG, extra_files=(), reporter=report):
    cfg, model = plan["config"], plan["profile"]
    if cfg != json.loads(config_path.read_text()) or plan["implementation_sha256"] != implementation(config_path, extra_files):
        raise ValueError("Approved plan does not match current runner and config")
    if model != json.loads(checked(PROFILE, cfg["profile_sha256"])) or template_sha() != plan["template_sha256"]:
        raise ValueError("Approved model profile or template changed")
    if preflight.runtime(model, str(model_path(model)), str(LLAMA)) != plan["runtime"]:
        raise ValueError("Runtime hashes changed after preparation")
    directory = Path(paths.RUNS) / cfg["run_id"]
    directory.mkdir(mode=0o700, parents=True)
    destination = directory / "manifest.json"
    destination.write_bytes(encode(plan))
    port = cfg["port"]
    state = {}

    def check_swap():
        page, count = resources.swap_snapshot()
        resources.check_swap_growth(cfg, page * count)

    def load_pressure():
        check_swap()
        if resources.thermal_state() != 0:
            raise resources.ResourceWarning("Thermal state is not nominal")
        return resources.pressure_level()

    def guard():
        check_swap()
        sample = resources.check(cfg, state)
        if sample["thermal_state"] != 0:
            raise resources.ResourceWarning("Thermal state is not nominal")
        e0b_resources.event(directory, "resource_sample", **sample)

    def send(path, body):
        return run.http_json(f"http://127.0.0.1:{port}{path}", body, timeout=120)

    def post(path, body=None):
        offset = log.stat().st_size
        response = request(send, guard, path, body)
        if proc.poll() is not None or provenance.engine_log_errors(log, offset):
            raise RuntimeError("Dedicated server exited or logged an engine fault")
        return response

    try:
        # Keep the pre-load inventory local. Only the memory estimate is retained here.
        def summary():
            inventory = e0b_resources.memory_inventory()
            return {key: value for key, value in inventory.items() if key != "largest_processes"}

        e0b_resources.admission(directory, inventory=summary)
        if resources.thermal_state() != 0:
            raise resources.ResourceWarning("Thermal state is not nominal before launch")
        resources.initialize_swap_baseline(cfg)
        log = directory / "server.log"
        with server(model, port, log) as proc:
            start = time.monotonic()
            while True:
                load_pressure()
                if proc.poll() is not None or time.monotonic() - start > 180:
                    raise RuntimeError("Dedicated server exited or timed out during loading")
                if port_open(port):
                    break
                time.sleep(1)
            e0b_resources.settle(directory, pressure=load_pressure)
            if "offloaded 29/29" not in log.read_text(errors="replace"):
                raise RuntimeError("No full Metal offload evidence in the dedicated log")
            (directory / "preflight.json").write_bytes(encode(token_preflight(plan, post)))
            result = generate(plan, directory, post, guard, reporter=reporter)
        e0b_resources.event(directory, "server_unloaded")
        (directory / "report.json").write_bytes(encode(result))
    except (Exception, KeyboardInterrupt) as error:
        e0b_resources.event(directory, "stopped", reason=str(error) or type(error).__name__)
        (directory / "STOPPED.json").write_bytes(encode({"reason": str(error) or type(error).__name__}))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "check", "run"))
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--outputs", type=Path)
    parser.add_argument("--approved-plan-sha256")
    args = parser.parse_args()
    if args.command == "run":
        if not args.approved_plan_sha256:
            parser.error("run requires the separately approved plan SHA-256")
        launch(json.loads(checked(args.bundle, args.approved_plan_sha256)))
    else:
        if args.outputs is None:
            parser.error("prepare and check require --outputs")
        blob = encode(build(args.outputs))
        if args.command == "prepare":
            with args.bundle.open("xb") as file:
                file.write(blob)
        elif args.bundle.read_bytes() != blob:
            raise SystemExit("Current model-free preflight differs from the prepared plan")
        print(f"Model-free preflight passed. Plan SHA-256 {base.digest(blob)}")


if __name__ == "__main__":
    main()
