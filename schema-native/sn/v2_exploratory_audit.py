"""Describe argument differences in the completed v2 baseline without changing its scores."""

import argparse
from collections import Counter, defaultdict
from importlib.metadata import version
import json
from pathlib import Path

from . import v2_dev_pilot as pilot, v2_holdout_score as frozen_score


BASELINE = pilot.ROOT / "analysis/v2-exploratory-baseline-v0.1/aggregate.public.json"
CHANGE_KINDS = ("missing", "extra", "changed")
ARGUMENT_ERRORS = {"valid_wrong_arguments", "schema_invalid_arguments"}


def differences(wanted, actual, path=()):
    """Compare objects recursively. Compare arrays as whole values under the frozen equality rule."""
    if isinstance(wanted, dict) and isinstance(actual, dict):
        for key in sorted(wanted.keys() - actual.keys()):
            yield "missing", (*path, key)
        for key in sorted(actual.keys() - wanted.keys()):
            yield "extra", (*path, key)
        for key in sorted(wanted.keys() & actual.keys()):
            yield from differences(wanted[key], actual[key], (*path, key))
    elif not pilot.base.argument_equal(wanted, actual):
        yield "changed", path


def summarize_changes(cases):
    signatures = Counter()
    calls = Counter()
    paths = Counter()
    nested = Counter()
    extras_per_intent = Counter()
    intents = defaultdict(set)
    sizes_by_intent = defaultdict(set)
    all_intents = set()
    for gold, changes in cases:
        kinds = {kind for kind, _ in changes}
        signatures["+".join(kind for kind in CHANGE_KINDS if kind in kinds)] += 1
        all_intents.add(gold["intent_key"])
        for kind in kinds:
            calls[kind] += 1
            intents[kind].add(gold["intent_key"])
            sizes_by_intent[gold["intent_key"], kind].add(gold["catalog_size"])
        paths.update(kind for kind, _ in changes)
        nested.update({kind for kind, path in changes if len(path) > 1})
        extras_per_intent[gold["intent_key"]] += sum(kind == "extra" for kind, _ in changes)
    repeats = Counter(kind for (_, kind), sizes in sizes_by_intent.items() if sizes == {5, 20})
    return {
        "calls": len(cases),
        "intents": len(all_intents),
        "call_signatures": dict(signatures),
        "calls_by_change": dict(calls),
        "intents_by_change": {kind: len(seen) for kind, seen in intents.items()},
        "paths_by_change": dict(paths),
        "calls_with_nested_change": dict(nested),
        "api_intents_with_same_change_kind_at_both_sizes": dict(repeats),
        "most_extra_paths_on_one_intent": max(extras_per_intent.values(), default=0),
    }


def matches_direct_default(schema, arguments, path):
    for key in path:
        if not isinstance(schema, dict):
            return False
        schema = schema.get("properties", {}).get(key)
        arguments = arguments[key]
    return (isinstance(schema, dict) and "default" in schema
            and pilot.base.argument_equal(schema["default"], arguments))


def summarize(inputs, answers, responses, score):
    groups = {outcome: [] for outcome in sorted(ARGUMENT_ERRORS)}
    invalid_keywords = Counter()
    valid_misses = Counter()
    calls_with_extra_default = 0
    for task, gold, response, row in zip(inputs, answers, responses, score["tasks"], strict=True):
        outcome = row["outcome"]
        if outcome != "correct" and row["schema_valid"]:
            valid_misses[outcome] += 1
        if outcome not in ARGUMENT_ERRORS:
            continue
        arguments = pilot.router.strict_loads(response["content"])["arguments"]
        changes = list(differences(gold["arguments"], arguments))
        if not changes:
            raise ValueError("Argument failure has no difference under frozen equality")
        groups[outcome].append((gold, changes))
        schema = next(t["parameters"] for t in task["tools"] if t["name"] == gold["tool"])
        if outcome == "schema_invalid_arguments":
            invalid_keywords.update({error.validator for error in pilot.base.validator(schema).iter_errors(arguments)})
        else:
            calls_with_extra_default += any(
                kind == "extra" and matches_direct_default(schema, arguments, path) for kind, path in changes
            )
    return {
        "scope": "exploratory, post hoc audit of frozen baseline",
        "requests": len(responses),
        "intents": len({gold["intent_key"] for gold in answers}),
        "argument_errors": {outcome: summarize_changes(cases) for outcome, cases in groups.items()},
        "all_argument_error_intents": len({gold["intent_key"] for cases in groups.values() for gold, _ in cases}),
        "wrong_calls_valid_under_emitted_tool_schema": dict(valid_misses),
        "valid_wrong_argument_calls_with_extra_matching_direct_default": calls_with_extra_default,
        "schema_invalid_calls_by_reported_validator_keyword": dict(invalid_keywords),
    }


def audit(freeze, responses_path):
    pins = json.loads(BASELINE.read_bytes())["provenance_sha256"]
    manifest = json.loads(pilot.checked(freeze / "manifest.json", pins["freeze_manifest"]))
    if version("jsonschema") != manifest["jsonschema_version"]:
        raise ValueError("Validator version differs from the frozen contract")
    for module in (frozen_score, pilot, pilot.base, pilot.router):
        path = Path(module.__file__)
        pilot.checked(path, manifest["implementation_sha256"][path.name])
    inputs, answers = (
        [pilot.base.strict_loads(line) for line in pilot.checked(freeze / name, manifest["file_sha256"][name]).decode().splitlines()]
        for name in ("inference/requests.jsonl", "scoring/expected.jsonl")
    )
    responses = [pilot.base.strict_loads(line) for line in
                 pilot.checked(responses_path, pins["response_ledger"]).decode().splitlines()]
    score = frozen_score.report(inputs, answers, responses)
    if pilot.base.digest(pilot.encode(score)) != pins["offline_private_score"]:
        raise ValueError("Replayed scores differ from the published baseline")
    result = summarize(inputs, answers, responses, score)
    result["input_sha256"] = {name: pins[name] for name in ("freeze_manifest", "response_ledger", "offline_private_score")}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--responses", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.freeze, args.responses)
    with args.out.open("xb") as stream:
        stream.write(pilot.encode(report))


if __name__ == "__main__":
    main()
