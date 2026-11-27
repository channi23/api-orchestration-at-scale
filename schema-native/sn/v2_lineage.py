"""Model-free lineage and provenance audit for the existing v2 development material."""

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re
from statistics import median
import unicodedata
from urllib.parse import urlsplit

from . import keyword_seed, source_expansion, trainpool, v2_catalog_review, v2_v03


BASE = v2_v03.BASE
DATA = Path(BASE.paths.DATA, "v2-lineage-v0.1")
INDEX_REVISION = "79f808b10c9e3269ea57f5c7c64fd663eadf2703"
INDEX_SHA256 = "0bd4becb72ffb8fa6a0cdcef9853f0ec29ed051f7d5c247d1f98efcec5f7d72c"
INDEX_URL = (
    "https://raw.githubusercontent.com/sdbs-uni-p/json-schema-corpus/"
    + INDEX_REVISION + "/repos_fullpath.csv"
)


def load_index(path):
    raw = path.read_bytes()
    if BASE.digest(raw) != INDEX_SHA256:
        raise ValueError("Source index does not match the pinned corpus snapshot")
    entries = {}
    for line in raw.decode("utf-8").splitlines():
        key, url = line.split(maxsplit=1)
        if key in entries:
            raise ValueError(f"Duplicate corpus index key: {key}")
        entries[key] = url
    return entries


def origin(schema_id, index):
    subset, name = schema_id.split("/", 1)
    if subset.startswith("Github_"):
        match = re.fullmatch(r"o([0-9]+)", name)
        url = index.get(f"js_{match.group(1)}.json") if match else None
        if url:
            parsed = urlsplit(url)
            parts = parsed.path.strip("/").split("/")
            if parsed.hostname == "github.com" and len(parts) >= 5 and parts[2] == "blob":
                return "github:" + "/".join(parts[:2]).casefold(), "indexed_repository", url
        return None, "unresolved_repository", url
    return "collection:" + subset, "collection_only", None


def normalized_request(request):
    return " ".join(unicodedata.normalize("NFC", request).casefold().split())


def components(families, canonical_hashes):
    """Join established family/ancestry and exact-schema matches only."""
    graph = trainpool.DSU()
    groups = defaultdict(list)
    for node, hashes in canonical_hashes.items():
        graph.find(node)
        for family in families.get(node, ()):
            groups[("family", family)].append(node)
        for sha in set(hashes):
            groups[("canonical", sha)].append(node)
    linked = defaultdict(list)
    for (reason, key), nodes in sorted(groups.items()):
        if len(nodes) > 1:
            for peer in nodes[1:]:
                graph.union(nodes[0], peer)
            linked[nodes[0]].append({"reason": reason, "key": key, "node_count": len(nodes)})
    members = defaultdict(list)
    reasons = defaultdict(list)
    for node in sorted(canonical_hashes):
        root = graph.find(node)
        members[root].append(node)
        reasons[root].extend(linked[node])
    result = {}
    for root, nodes in members.items():
        component_id = BASE.digest("\0".join(nodes).encode())[:16]
        result[component_id] = {
            "members": nodes,
            "links": sorted(reasons[root], key=lambda link: (link["reason"], link["key"])),
        }
    return result


def build(index):
    _, drafts, pool, schemas, catalogs, _, _ = v2_v03.load()
    cards, raw_cards = source_expansion.load()
    _, _, _, review_catalogs, _, _ = v2_catalog_review.load()
    legacy_file = Path(BASE.paths.DATA, "trainpool/schemas.v1.jsonl")
    legacy = BASE.read_rows(legacy_file)
    legacy_by_node = {"legacy:" + row["schema_id"]: row for row in legacy}
    legacy_schema_ids = {node: row["schema_id"] for node, row in legacy_by_node.items()}
    v1 = BASE.paths.tasks()
    v1_targets = {row["tool_id"] for row in v1}
    keyword_path = keyword_seed.DATA / "pairs.jsonl"
    keywords = BASE.read_rows(keyword_path)
    stress_path = BASE.DATA / "stress-inventory.json"
    stress = json.loads(stress_path.read_text())["cases"]
    inventory_path = BASE.DATA / "inventory.jsonl"
    historical_exposure = {
        row["tool_id"]: row["historical_catalog_exposure"]
        for row in BASE.read_rows(inventory_path)
    }
    stress_hashes = {row["case_id"]: row["schema_hashes"] for row in stress}
    audit_path = Path(BASE.paths.EXP, "dataset/audit_schemas.jsonl.gz")
    with gzip.open(audit_path, "rt") as stream:
        normalized = {
            row["schema_id"]: row.get("normalized_sha256")
            for row in map(json.loads, stream)
        }

    schema_ids = {tid: row["schema_id"] for tid, row in pool.items()}
    schema_ids.update({card["card_id"]: card["schema_id"] for card in cards})
    schema_ids.update(legacy_schema_ids)
    raw = dict(schemas)
    raw.update(raw_cards)
    raw.update({node: BASE.su.load_schema(sid) for node, sid in legacy_schema_ids.items()})
    origins = {node: origin(sid, index) for node, sid in schema_ids.items()}
    hashes = {node: [BASE.su.sha(schema)] for node, schema in raw.items()}
    hashes.update({"seed:" + row["pair_id"]: [BASE.su.sha(row[k]) for k in ("schema_S", "schema_S2")]
                   for row in keywords})
    hashes.update({"stress:" + case_id: shas for case_id, shas in stress_hashes.items()})
    families = {tid: ["pool:" + row["family"]] for tid, row in pool.items()}
    for node, sid in schema_ids.items():
        if sid.startswith("Glaiveai2K/"):
            function = trainpool.glaive_base(sid)
            families.setdefault(node, []).append("glaive:" + function)
    families.update({"seed:" + row["pair_id"]: ["seed:" + row["family_id"]] for row in keywords})
    grouped = components(families, hashes)
    by_node = {node: key for key, comp in grouped.items() for node in comp["members"]}

    draft_ids = {row["tool_id"] for row in drafts}
    distractors = {
        tid for cat in [*catalogs.values(), *review_catalogs.values()]
        for tid in cat["tool_ids"] if tid != cat["tool_id"]
    }
    buckets = {"v1_target": v1_targets, "v2_draft_target": draft_ids, "v2_distractor": distractors}
    for row in legacy:
        buckets.setdefault("legacy_" + row["split"], set()).add("legacy:" + row["schema_id"])
    by_source = defaultdict(lambda: defaultdict(set))
    for bucket, nodes in buckets.items():
        for node in nodes:
            group = origins[node][0]
            if group:
                by_source[group][bucket].add(node)

    normalized_peers = defaultdict(set)
    comparison_nodes = set(pool) | legacy_schema_ids.keys()
    for node in comparison_nodes:
        sha = normalized.get(schema_ids[node])
        if sha:
            normalized_peers[sha].add(node)
    v1_by_request = defaultdict(list)
    for row in v1:
        v1_by_request[normalized_request(row["prompt"])].append(row["task_id"])
    by_draft = {row["tool_id"]: row for row in drafts}
    card_ids = {row["card_id"] for row in cards}
    evaluated_nodes = draft_ids | card_ids | {"seed:" + row["pair_id"] for row in keywords}
    records = []
    for node in sorted(evaluated_nodes):
        group, group_kind, url = origins.get(node, ("authored:keyword-seeds", "authored_group", None))
        comp = grouped[by_node[node]]
        sid = schema_ids.get(node)
        sha = normalized.get(sid)
        ids = set(comp["members"])
        counts = {
            bucket: len(nodes - {node})
            for bucket, nodes in sorted(by_source.get(group, {}).items()) if nodes - {node}
        }
        records.append({
            "node": node,
            "track": "api_draft" if node in draft_ids else "adapter" if node in card_ids else "keyword_pair",
            "schema_id": sid,
            "canonical_schema_hashes": hashes[node],
            "legacy_normalized_schema_hash": sha,
            "source_group": group,
            "source_group_kind": group_kind,
            "source_index_url": url,
            "source_license_status": "review_pending" if sid else "authored_examples",
            "source_overlap_counts": counts,
            "historical_catalog_exposure": historical_exposure.get(node),
            "component_id": by_node[node],
            "v1_target_lineage_matches": sorted(ids & v1_targets),
            "linked_stress_cases": sorted(n.removeprefix("stress:") for n in ids if n.startswith("stress:")),
            "legacy_lineage_matches": [
                {"schema_id": legacy_by_node[other]["schema_id"], "split": legacy_by_node[other]["split"]}
                for other in sorted(ids & legacy_by_node.keys())
            ],
            "normalized_schema_review_hits": sorted(normalized_peers[sha] - {node}) if sha else [],
            "normalized_v1_request_review_hits": (
                v1_by_request[normalized_request(by_draft[node]["request"])] if node in by_draft else []
            ),
            "disposition": "development_only",
            "approved_for_test": False,
        })

    # Historical source overlap is computed by project identity, even when subset labels differ.
    legacy_crossings = {
        group: {k: sorted(nodes) for k, nodes in counts.items() if k.startswith("legacy_")}
        for group, counts in sorted(by_source.items())
        if group.startswith("github:") and counts.get("legacy_train") and counts.get("legacy_holdout_family")
    }
    groups_in_scope = {row["source_group"] for row in records if row["source_group"]}
    draft_rows = [row for row in records if row["track"] == "api_draft"]
    sizes = sorted(len(comp["members"]) for comp in grouped.values())
    summary = {
        "index_revision": INDEX_REVISION,
        "index_sha256": INDEX_SHA256,
        "collection_revision": BASE.UPSTREAM_REVISION,
        "comparison_inventory": {
            "pool_schemas": len(pool), "legacy_assignments": len(legacy), "v1_paraphrases": len(v1),
            "v1_target_tools": len(v1_targets), "external_stress_cases": len(stress),
        },
        "origin_resolution": dict(sorted(Counter(kind for _, kind, _ in origins.values()).items())),
        "evaluated": dict(sorted(Counter(row["track"] for row in records).items())),
        "lineage_components": {
            "total": len(sizes), "min": sizes[0], "median": median(sizes),
            "p95": sizes[(95 * len(sizes) + 99) // 100 - 1], "max": sizes[-1],
            "largest": {key: comp for key, comp in grouped.items() if len(comp["members"]) == sizes[-1]},
        },
        "development_components": {key: grouped[key] for key in sorted({row["component_id"] for row in records})},
        "relevant_source_groups": {
            group: {bucket: sorted(nodes) for bucket, nodes in sorted(by_source[group].items())}
            for group in sorted(groups_in_scope)
        },
        "legacy_train_vs_holdout_repo_crossings": legacy_crossings,
        "drafts_with_legacy_train_project_overlap": sorted(
            row["node"] for row in draft_rows
            if row["source_group_kind"] == "indexed_repository" and row["source_overlap_counts"].get("legacy_train")
        ),
        "drafts_with_collection_only_origin": sorted(
            row["node"] for row in draft_rows if row["source_group_kind"] == "collection_only"
        ),
        "approved_test_intents": 0,
        "split_assigned": False,
    }
    input_files = [
        Path(__file__), Path(v2_v03.__file__), Path(v2_catalog_review.__file__),
        Path(source_expansion.__file__), legacy_file, keyword_path, stress_path, audit_path, inventory_path,
        v2_v03.DATA / "manifest.json", v2_v03.DATA / "drafts.clean.jsonl",
        v2_v03.DATA / "catalogs.jsonl", v2_catalog_review.DATA / "catalogs.jsonl",
        source_expansion.DATA / "cards.source.jsonl",
        Path(BASE.paths.EXP, "dataset/tool_pool.v1.jsonl"), Path(BASE.paths.EXP, "tasks/tasks.v1.jsonl"),
    ]
    summary["inputs_sha256"] = {
        str(path.relative_to(BASE.REPO)): BASE.digest(path.read_bytes()) for path in input_files
    }
    return {
        "lineage.jsonl": v2_catalog_review.lines(records),
        "audit.json": json.dumps(summary, indent=2, sort_keys=True) + "\n",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-index", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build(load_index(args.source_index))
    if not args.check:
        DATA.mkdir(exist_ok=True)
    for name, content in artifacts.items():
        path = DATA / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise SystemExit(f"Artifact differs: {name}")
        else:
            path.write_text(content)
    print("PASS: source overlap and lineage audit; development only")


if __name__ == "__main__":
    main()
