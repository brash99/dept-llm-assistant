#!/usr/bin/env python3
"""Ingest one raw Schedule of Classes CSV into semantic observations."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.adapters.schedule_adapter import ScheduleCSVAdapter, write_observations


DEFAULT_OUTPUT_ROOT = Path("data/normalized/schedules")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Adapt a raw institutional schedule CSV into one factual "
            "CourseOfferingObservation Knowledge Object per scheduled section."
        )
    )
    parser.add_argument("source_csv", type=Path)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Output root (default: {DEFAULT_OUTPUT_ROOT})",
    )
    return parser.parse_args()


def _print_counter(label: str, values: Counter[str]) -> None:
    total = sum(values.values())
    print(f"{label}: {total}")
    for name, count in sorted(values.items()):
        print(f"  - {name}: {count}")


def main() -> int:
    args = parse_args()
    adapter = ScheduleCSVAdapter(args.source_csv)
    result = adapter.adapt()

    output_directory = args.output_root / args.source_csv.stem
    observations_created = write_observations(
        result.observations,
        output_directory,
    )

    print("Schedule CSV ingestion")
    print(f"Source: {args.source_csv}")
    print(f"Output: {output_directory}")
    print(f"Rows processed: {result.rows_processed}")
    print(f"Observations created: {observations_created}")
    print(f"Rows skipped: {result.rows_skipped}")
    print(f"Duplicate observations detected: {result.duplicate_observations}")
    _print_counter("Missing required fields", result.missing_required_fields)
    _print_counter("Parsing warnings", result.parsing_warnings)

    if result.missing_required_fields and result.rows_processed == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
