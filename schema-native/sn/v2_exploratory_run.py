"""Run the frozen inference-only export locally with durable before-send accounting."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import time

from . import e0b_resources, resources, v2_dev_pilot as pilot
from .v2_exploratory_export import PROFILE


CONFIG = pilot.ROOT / "configs/runs/v2_exploratory_free.json"
RUNS = Path(pilot.paths.RUNS)
SMOKE = RUNS / "v2-context-9216-smoke-v0.1/manifest.json"


def records(path):
    return pilot.base.read_rows(path) if path.exists() else []


def save(path, value):
    temp = path.with_suffix(".tmp")
    with temp.open("wb") as stream:
        stream.write(pilot.encode(value))
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def prepare(export):
    config = json.loads(CONFIG.read_bytes())
    manifest = json.loads(pilot.checked(export / "manifest.json", config["export_manifest_sha256"]))
    profile = json.loads(pilot.checked(PROFILE, manifest["profile_sha256"]))
    raw = pilot.checked(export / "requests.jsonl", manifest["payloads_sha256"])
    rows = [pilot.base.strict_loads(line) for line in raw.decode().splitlines()]
    if len(rows) != config["generation_cap"] or len({row["request_id"] for row in rows}) != len(rows):
        raise ValueError("Inference export roster differs from the generation budget")
    if config["metadata_cap"] < 1 + 2 * len(rows):
        raise ValueError("Metadata budget cannot cover preflight")
    for row in rows:
        payload = row["payload"]
        expected = dict(profile["request_params"], messages=payload["messages"], cache_prompt=False)
        if (payload != expected or not isinstance(payload["messages"], list)
                or not 0 < row["expected_prompt_tokens"] <= manifest["context_tokens"] - payload["max_tokens"]):
            raise ValueError("Export payload differs from the locked profile")
    return config, manifest, profile, rows


def remaining(rows, directory, ledger):
    saved = [r["request_id"] for r in records(directory / "results.jsonl")]
    charged = [r["key"] for r in records(ledger) if r["category"] == "benchmark"]
    if saved != charged:
        raise RuntimeError("The ledger has an unanswered generation charge. No generation will be resent.")
    if saved != [row["request_id"] for row in rows[:len(saved)]]:
        raise RuntimeError("Saved results are not a prefix of the frozen request order")
    return rows[len(saved):]


def attest(post, manifest, profile):
    props = post("/props")
    if (props.get("default_generation_settings", {}).get("n_ctx") != manifest["context_tokens"]
            or profile["llama_cpp_commit"][:7] not in str(props.get("build_info", ""))
            or Path(props.get("model_path", "")).resolve() != pilot.model_path(profile).resolve()
            or pilot.provenance.digest(props.get("chat_template")) != manifest["template_sha256"]):
        raise RuntimeError("Running server differs from the pinned context, build, model path or template")


def token_preflight(directory, rows, post):
    cache = directory / "prompt-counts.jsonl"
    verified = records(cache)
    expected = [{"request_id": r["request_id"], "prompt_tokens": r["expected_prompt_tokens"]} for r in rows]
    if verified != expected[:len(verified)]:
        raise RuntimeError("Saved prompt checks differ from the frozen requests")
    for row, check in zip(rows[len(verified):], expected[len(verified):], strict=True):
        payload = row["payload"]
        rendered = post("/apply-template", {"messages": payload["messages"], "add_generation_prompt": True,
                                             "chat_template_kwargs": payload["chat_template_kwargs"]})
        if not isinstance(rendered.get("prompt"), str):
            raise RuntimeError("Template endpoint did not return a prompt")
        tokens = post("/tokenize", {"content": rendered["prompt"], "add_special": True}).get("tokens")
        if not isinstance(tokens, list) or len(tokens) != check["prompt_tokens"]:
            raise RuntimeError("Online length differs from the frozen prompt length")
        pilot.append(directory, cache.name, check)


def generate(directory, rows, post, guard, cooldown):
    for index, row in enumerate(rows):
        started = time.monotonic()
        response = post("/v1/chat/completions", row["payload"], key=row["request_id"])
        choices = response.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise RuntimeError("Expected exactly one completion")
        content = choices[0].get("message", {}).get("content")
        finish = choices[0].get("finish_reason")
        usage = response.get("usage")
        if (not isinstance(content, str) or finish not in {"stop", "length"}
                or not isinstance(usage, dict) or usage.get("prompt_tokens") != row["expected_prompt_tokens"]
                or type(usage.get("completion_tokens")) is not int
                or not 0 <= usage["completion_tokens"] <= row["payload"]["max_tokens"]):
            raise RuntimeError("Completion text, finish reason or token usage differs from the protocol")
        pilot.append(directory, "results.jsonl", {
            "request_id": row["request_id"], "content": content, "finish_reason": finish,
            "usage": usage, "elapsed_seconds": time.monotonic() - started,
        })
        guard()
        if index + 1 < len(rows):
            time.sleep(cooldown)


def segment_run(directory, segment, config, manifest, profile, rows, pending, budget, prior_growth):
    port = config["port"]
    log = segment / "server.log"
    sampling = {}
    config = dict(config, system_swapout_baseline_file=str(segment / "swap-baseline.json"))
    limit = config["max_system_swapout_growth_bytes"]

    def sample_swap():
        page, swaps = resources.swap_snapshot()
        growth = resources.check_swap_growth(config, page * swaps)
        e0b_resources.event(segment, "swap_sample", system_swapout_growth_bytes=growth)
        if prior_growth + growth > limit:
            raise RuntimeError("Cumulative system swapout grew by more than 1 GiB; stop")

    def pressure():
        sample_swap()
        if resources.thermal_state() != 0:
            raise resources.ResourceWarning("Thermal state is not nominal")
        return resources.pressure_level()

    def guard():
        sample_swap()
        sample = resources.check(config, sampling)
        if sample["thermal_state"] != 0:
            raise resources.ResourceWarning("Thermal state is not nominal")
        e0b_resources.event(segment, "resource_sample", **sample)

    def send(path, body):
        return pilot.run.http_json(f"http://127.0.0.1:{port}{path}", body, timeout=120)

    def inventory():
        return {k: v for k, v in e0b_resources.memory_inventory().items() if k != "largest_processes"}

    if pilot.port_open(port):
        raise RuntimeError("The dedicated port is in use. No server was started.")
    resources.initialize_swap_baseline(config)
    if resources.thermal_state() != 0:
        raise resources.ResourceWarning("Thermal state is not nominal before launch")
    e0b_resources.admission(segment, inventory=inventory)
    metadata_index = 0
    log_offset = 0
    try:
        with pilot.server(profile, port, log) as proc:
            started = time.monotonic()
            while True:
                pressure()
                if proc.poll() is not None or time.monotonic() - started > 180:
                    raise RuntimeError("Dedicated server exited or timed out during loading")
                if pilot.port_open(port):
                    break
                time.sleep(1)
            e0b_resources.settle(segment, pressure=pressure)
            if "offloaded 29/29" not in log.read_text(errors="replace"):
                raise RuntimeError("No full Metal offload evidence in the dedicated log")
            e0b_resources.event(segment, "metal_offload_verified", layers=29)

            def post(path, body=None, *, key=None):
                nonlocal metadata_index, log_offset
                category = "readiness" if key is None else "benchmark"
                if key is None:
                    metadata_index += 1
                    key = f"{segment.name}|{metadata_index}|{path}"
                reserved = False

                def before_and_during():
                    nonlocal reserved
                    guard()
                    if not reserved:
                        budget.reserve(category, key)
                        reserved = True

                response = pilot.request(send, before_and_during, path, body)
                end = log.stat().st_size
                if proc.poll() is not None or pilot.provenance.engine_log_errors(log, log_offset):
                    raise RuntimeError("Dedicated server exited or logged an engine fault")
                log_offset = end
                return response

            attest(post, manifest, profile)
            token_preflight(directory, rows, post)
            e0b_resources.event(segment, "preflight_passed", frozen_lengths=len(rows))
            generate(directory, pending, post, guard, config["request_cooldown_seconds"])
    finally:
        if log.exists() and not pilot.port_open(port):
            e0b_resources.event(segment, "server_unloaded")


def execute(directory, config, manifest, profile, rows, identity):
    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        save(manifest_path, identity)
    elif json.loads(manifest_path.read_bytes()) != identity:
        raise RuntimeError("Run identity changed. Existing work is preserved.")
    if (directory / "COMPLETED.json").exists():
        return
    segments = sorted(directory.glob("segment-*"))
    prior_growth = 0
    for earlier in segments:
        stopped = json.loads((earlier / "STOPPED.json").read_bytes())
        if not stopped["resumable"]:
            raise RuntimeError("Previous segment recorded a final stop")
        prior_growth += max((e.get("system_swapout_growth_bytes") or 0
                             for e in records(earlier / "resource-events.jsonl")), default=0)

    ledger = directory / "request-budget.jsonl"
    pending = remaining(rows, directory, ledger)
    segment = directory / f"segment-{len(segments) + 1:03d}"
    segment.mkdir(mode=0o700)
    budget = pilot.e0b.Budget(ledger, benchmark_cap=config["generation_cap"], readiness_cap=config["metadata_cap"])
    try:
        if pending:
            segment_run(directory, segment, config, manifest, profile, rows, pending, budget, prior_growth)
        if remaining(rows, directory, ledger):
            raise RuntimeError("Run ended without the complete frozen roster")
        counts = records(ledger)
        save(directory / "COMPLETED.json", {"generation_requests": len(rows),
                                             "metadata_requests": sum(r["category"] == "readiness" for r in counts)})
    except (Exception, KeyboardInterrupt) as error:
        resumable = isinstance(error, (resources.ResourceWarning, e0b_resources.ResourceStop, KeyboardInterrupt))
        try:
            todo = remaining(rows, directory, ledger)
        except RuntimeError:
            resumable = False
            todo = pending
        save(segment / "STOPPED.json", {"reason": str(error) or type(error).__name__,
                                        "resumable": resumable, "saved_results": len(rows) - len(todo)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "run"))
    parser.add_argument("--export", type=Path, required=True)
    args = parser.parse_args()
    config, manifest, profile, rows = prepare(args.export)
    if args.command == "check":
        print(f"Verified the inference-only export for {len(rows)} frozen requests")
        return
    os.umask(0o077)
    smoke = json.loads(pilot.checked(SMOKE, config["smoke_manifest_sha256"]))
    runtime = pilot.preflight.runtime(profile, str(pilot.model_path(profile)), str(pilot.LLAMA))
    if runtime != smoke["runtime"] or manifest["template_sha256"] != smoke["template_sha256"]:
        raise RuntimeError("Runtime identity differs from the measured 9,216-token smoke")
    identity = {"config": config, "export": manifest, "runtime": runtime,
                "runner_sha256": pilot.provenance.file_sha(__file__)}
    directory = RUNS / config["run_id"]
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / "writer.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        execute(directory, config, manifest, profile, rows, identity)


if __name__ == "__main__":
    main()
