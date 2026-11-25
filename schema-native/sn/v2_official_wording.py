"""Export a two-request wording revision of the pinned official API review packet."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from . import v2_official_sources as parent


BASE = parent.BASE
DATA = Path(BASE.paths.DATA, "v2-official-sources-v0.2")
PARENT_SHA256 = "a134e1569f4f3199ab06f4b6ef8df158db0065db0dbb620d3a4cf2434ef335fa"
NOTICES = ("pokeapi-license.md", "stripe-license.txt")


def revised_packet(parent_zip):
    if BASE.digest(parent_zip.read_bytes()) != PARENT_SHA256:
        raise ValueError("Review packet does not match the pinned v0.1 export")
    with ZipFile(parent_zip) as archive:
        rows = [BASE.strict_loads(line) for line in archive.read("tasks.jsonl").decode().splitlines()]
        notices = {name: archive.read(name) for name in NOTICES}
    by_id = {row["task_id"]: row for row in rows}
    edits = BASE.read_rows(DATA / "wording.jsonl")
    seen, revised = set(), []
    for edit in edits:
        if set(edit) != {"parent_task_id", "request", "reason"}:
            raise ValueError("A wording edit can only change the request")
        parent_id = edit["parent_task_id"]
        if parent_id in seen or parent_id not in by_id:
            raise ValueError("Unknown or repeated parent task")
        seen.add(parent_id)
        original = by_id[parent_id]
        if edit["request"] == original["request"]:
            raise ValueError("A wording edit must change the visible request")
        new_id = "V2OSW_" + BASE.digest(f"{DATA.name}\0{parent_id}".encode())[:12]
        revised.append({**original, "task_id": new_id, "request": edit["request"]})
    return sorted(revised, key=lambda row: row["task_id"]), notices


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-zip", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    tasks, notices = revised_packet(args.parent_zip)
    entries = {
        "tasks.jsonl": "".join(BASE.serialized(row) + "\n" for row in tasks).encode(),
        "REVIEW_INSTRUCTIONS.md": (DATA / "REVIEW_INSTRUCTIONS.md").read_bytes(),
        **notices,
    }
    with ZipFile(args.out, "x", compression=ZIP_DEFLATED) as output:
        for name, payload in entries.items():
            info = ZipInfo(name, date_time=(2026, 11, 25, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            output.writestr(info, payload)
    print(f"PASS: exported {len(tasks)} wording revisions")


if __name__ == "__main__":
    main()
