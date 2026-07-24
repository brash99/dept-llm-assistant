#!/usr/bin/env python3
"""Validate the structure and sampled records of a built ISO vector DB."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_config
from app.vector_db_validation import validate_vector_db


def _default_vector_db() -> Path:
    config = load_config()
    configured_root = Path(config["project"]["root"])
    return configured_root / config["storage"]["vector_db"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vector-db", type=Path, default=None)
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)

    report = validate_vector_db(
        args.vector_db or _default_vector_db(), sample_size=args.sample_size
    )
    if args.json_output:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        status = "PASS" if report.valid else "FAIL"
        print(f"Vector DB validation: {status}")
        print(f"Path: {report.vector_db}")
        print(
            f"Vectors/records: {report.index_count:,}/{report.record_count:,} | "
            f"dimension: {report.dimension} | index: {report.index_type or '<unavailable>'}"
        )
        print(
            f"Sampled records: {report.sampled_records:,} of "
            f"{report.sample_size_requested:,} requested"
        )
        print("Object types: " + ", ".join(
            f"{key}={value:,}" for key, value in report.object_types.items()
        ))
        print("Semantic spaces: " + ", ".join(
            f"{key}={value:,}" for key, value in report.semantic_spaces.items()
        ))
        for warning in report.warnings:
            print(f"WARNING: {warning}")
        for error in report.errors:
            print(f"ERROR: {error}")
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
