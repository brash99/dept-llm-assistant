#!/usr/bin/env python3
"""Report metadata inventory from records.pkl without loading models or FAISS."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import pickle
import sys
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_config


def _default_vector_db() -> Path:
    config = load_config()
    return Path(config["project"]["root"]) / config["storage"]["vector_db"]


def _source_family(record: Dict[str, Any]) -> str:
    metadata = record.get("metadata") or {}
    for key in (
        "source_family",
        "normalization_source",
        "source_key",
        "issuing_authority",
        "source_type",
    ):
        if metadata.get(key):
            return str(metadata[key])
    citation = record.get("citation") or {}
    path = str(citation.get("relative_path") or citation.get("source_path") or "")
    parts = [part for part in PurePosixPath(path.replace("\\", "/")).parts if part not in ("/", ".")]
    return parts[0] if parts else "<missing>"


def build_inventory(records) -> Dict[str, Any]:
    counters = {
        "object_type": Counter(),
        "semantic_space": Counter(),
        "evidence_role": Counter(),
        "source_family": Counter(),
        "catalog_year": Counter(),
    }
    for record in records:
        if not isinstance(record, dict):
            counters["object_type"]["<invalid-record>"] += 1
            continue
        metadata = record.get("metadata") or {}
        counters["object_type"][str(record.get("object_type") or "<missing>")] += 1
        counters["semantic_space"][str(metadata.get("semantic_space") or "<missing>")] += 1
        if metadata.get("evidence_role"):
            counters["evidence_role"][str(metadata["evidence_role"])] += 1
        counters["source_family"][_source_family(record)] += 1
        if metadata.get("catalog_year"):
            counters["catalog_year"][str(metadata["catalog_year"])] += 1
    return {
        "total_records": len(records),
        **{
            name: dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))
            for name, counter in counters.items()
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vector-db", type=Path, default=None)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args(argv)
    if args.top < 1:
        parser.error("--top must be at least 1")

    vector_db = args.vector_db or _default_vector_db()
    records_path = vector_db / "records.pkl"
    if not records_path.is_file():
        print(f"ERROR: records file not found: {records_path}", file=sys.stderr)
        return 1
    try:
        with records_path.open("rb") as handle:
            records = pickle.load(handle)
    except Exception as exc:
        print(f"ERROR: unable to load {records_path}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(records, list):
        print("ERROR: records.pkl does not contain a list", file=sys.stderr)
        return 1

    inventory = build_inventory(records)
    if args.json_output:
        print(json.dumps(inventory, indent=2, sort_keys=True))
        return 0

    print(f"Vector DB inventory: {vector_db}")
    print(f"Total records: {inventory['total_records']:,}")
    for category in (
        "object_type", "semantic_space", "evidence_role", "source_family", "catalog_year"
    ):
        print(f"\n{category.replace('_', ' ').title()}")
        values = list(inventory[category].items())
        if not values:
            print("  <none recorded>")
        for name, count in values[: args.top]:
            print(f"  {count:>9,}  {name}")
        if len(values) > args.top:
            print(f"  ... {len(values) - args.top} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
