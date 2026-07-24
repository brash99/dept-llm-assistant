#!/usr/bin/env python3
"""Ingest a directory of acquired academic catalog PDFs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.adapters.catalog_adapter import CatalogAdapter, write_observations
from app.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source_directory",
        nargs="?",
        default="data/acquisition/catalogs",
        help="Directory containing acquired catalog PDFs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Override the configured root for year-scoped Knowledge Object JSON",
    )
    args = parser.parse_args()

    config = load_config()
    configured_root = Path(config["project"]["root"])
    project_root = configured_root if configured_root.exists() else PROJECT_ROOT
    output = args.output or (
        project_root / config["catalog_ingestion"]["normalized_output_root"]
    )
    result = CatalogAdapter(Path(args.source_directory)).adapt()
    written = write_observations(result.observations, output)

    print("Academic Catalog Semantic Ingestion")
    print(f"Catalog files discovered: {result.files_discovered}")
    print(f"Catalog files processed:  {result.files_processed}")
    print(f"Catalog files failed:     {result.files_failed}")
    for object_type, count in sorted(result.objects_by_type.items()):
        print(f"{object_type}: {count}")
    print(f"Roster entries preserved: {result.roster_entries}")
    print(f"Registry entries created: {result.registry_entries}")
    print(f"Duplicate object IDs:     {result.duplicate_observation_ids}")
    print(f"Knowledge Objects written:{written:>7}")
    if result.failures:
        print("Failures:")
        for failure in result.failures:
            print(f"- {failure['path']}: {failure['error']}")
    return 1 if result.files_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
