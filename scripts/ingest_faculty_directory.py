#!/usr/bin/env python3
"""Ingest one acquired faculty-directory snapshot into Knowledge Objects."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.adapters.faculty_adapter import FacultyDirectoryAdapter, write_observations


def _counter(label: str, values: Counter[str]) -> None:
    print(f"{label}: {sum(values.values())}")
    for name, count in sorted(values.items()):
        print(f"  - {name}: {count}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adapt an acquired faculty-directory snapshot into factual observations."
    )
    parser.add_argument("snapshot_directory", type=Path)
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Override the configured faculty normalized-output root.",
    )
    args = parser.parse_args()

    config = load_config()
    configured_root = Path(config["project"]["root"])
    project_root = configured_root if configured_root.exists() else PROJECT_ROOT
    output_root = args.output_root or (
        project_root / config["faculty_ingestion"]["normalized_output_root"]
    )
    result = FacultyDirectoryAdapter(args.snapshot_directory).adapt()
    output = output_root / args.snapshot_directory.name
    written = write_observations(result.observations, output)

    print("Faculty directory ingestion")
    print(f"Source: {args.snapshot_directory}")
    print(f"Output: {output}")
    print(f"Files discovered: {result.files_discovered}")
    print(f"Objects created: {written}")
    print(f"Skipped files: {result.skipped_files}")
    print(f"Failures: {len(result.failures)}")
    print(f"Missing names: {result.missing_names}")
    print(f"Missing departments: {result.missing_departments}")
    print(f"Missing emails: {result.missing_emails}")
    print(f"Duplicate deterministic IDs: {result.duplicate_observation_ids}")
    print(f"Structural variants encountered: {len(result.structural_variants)}")
    for name, count in sorted(result.structural_variants.items()):
        print(f"  - {name}: {count}")
    _counter("Unknown labels retained", result.unknown_labels)
    for failure in result.failures:
        print(f"  [FAIL] {failure['path']}: {failure['error']}")
    return 1 if result.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
