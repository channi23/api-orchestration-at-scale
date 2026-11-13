"""Turn kept synthetic examples into MLX-LM chat training files.

Each line is ``{"messages": [system, user, assistant]}``: the exact prompt wording of the benchmark
(``experiment/src/prompts.py``) and the exact output contract. The assistant turn is the only part
that receives loss when training with ``--mask-prompt``.

Per example a small catalog is sampled (size 1, 3 or 5): the gold tool plus distractors drawn from
OTHER FAMILIES OF THE SAME SPLIT. Test tools can never appear because they are not in the pool.

Representations:
  raw       tool parameters = original schema, indent 2      (arm C)
  minified  same content, compact separators                  (arms D, E; lossless by construction)

usage: python -m sn.mlxdata --representation minified [--sizes 1 3 5]
Output: data/mlx/<representation>/{train,valid}.jsonl + manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random

from . import paths
import prompts  # type: ignore  # noqa: E402
import schema_utils as su  # type: ignore  # noqa: E402


def tool_obj(name: str, description: str, params: dict) -> dict:
    return {"type": "function", "function": {"name": name, "description": description, "parameters": params}}


def render_catalog(tools: list[dict], representation: str) -> str:
    if representation == "minified":
        return json.dumps(tools, ensure_ascii=False, separators=(",", ":"))
    if representation == "raw":
        return json.dumps(tools, ensure_ascii=False, indent=2)
    raise ValueError(f"unknown representation {representation!r}")


def assistant_text(tool_name: str, args: dict) -> str:
    return json.dumps({"tool": tool_name, "arguments": args}, ensure_ascii=False)


def build_split(examples: list[dict], representation: str, sizes: list[int], seed: int) -> list[dict]:
    by_family = {}
    for e in examples:
        by_family.setdefault(e["family"], []).append(e)
    fams = sorted(by_family)
    out = []
    for e in examples:
        rng = random.Random(int(hashlib.sha256(f"{seed}:{e['example_id']}".encode()).hexdigest()[:12], 16))
        k = rng.choice(sizes)
        others = [f for f in fams if f != e["family"]]
        picks = [rng.choice(by_family[f]) for f in rng.sample(others, min(k - 1, len(others)))]
        names = {e["tool_name"]}
        cat = [e]
        for p in picks:                                  # tool names must be unique in a catalog
            if p["tool_name"] not in names:
                names.add(p["tool_name"])
                cat.append(p)
        rng.shuffle(cat)
        tools = [tool_obj(c["tool_name"], c["description"], su.load_schema(c["schema_id"])) for c in cat]
        system = prompts.SYSTEM_TEMPLATE.format(tools=render_catalog(tools, representation))
        user = e["request"]
        if len(cat) == 1:
            user += prompts.ARGGEN_SUFFIX.format(tool_name=e["tool_name"])
        out.append({"messages": [{"role": "system", "content": system}, {"role": "user", "content": user},
                                 {"role": "assistant", "content": assistant_text(e["tool_name"], e["gold_args"])}],
                    "meta": {"example_id": e["example_id"], "family": e["family"], "catalog_size": len(cat)}})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--representation", default="minified", choices=["raw", "minified"])
    ap.add_argument("--sizes", nargs="+", type=int, default=[1, 3, 5])
    ap.add_argument("--seed", type=int, default=20261112)
    ap.add_argument("--synth", default=os.path.join(paths.DATA, "synth"))
    ap.add_argument("--out", default=os.path.join(paths.DATA, "mlx"))
    a = ap.parse_args()
    out_dir = os.path.join(a.out, a.representation)
    os.makedirs(out_dir, exist_ok=True)
    manifest = {"representation": a.representation, "sizes": a.sizes, "seed": a.seed, "splits": {}}
    pool_ids = {t["schema_id"] for t in paths.pool().values()}
    for split in ("train", "valid"):
        src = os.path.join(a.synth, f"{split}.v1.jsonl")
        ex = paths.jsonl(src)
        assert not ({e["schema_id"] for e in ex} & pool_ids), "test tool found in training examples"
        rows = build_split(ex, a.representation, a.sizes, a.seed)
        with open(os.path.join(out_dir, f"{split}.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        manifest["splits"][split] = {"examples": len(rows), "families": len({e["family"] for e in ex}),
                                     "chars_p50": sorted(len(r["messages"][0]["content"]) for r in rows)[len(rows) // 2] if rows else 0}
    fams = {s: {e["family"] for e in paths.jsonl(os.path.join(a.synth, f"{s}.v1.jsonl"))} for s in ("train", "valid")}
    assert not (fams["train"] & fams["valid"]), "a family is in both train and valid"
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
