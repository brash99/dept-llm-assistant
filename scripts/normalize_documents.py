#!/usr/bin/env python3

from pathlib import Path
import argparse
import json
from datetime import datetime

from app.config import load_config
from app.normalize import normalize_files, normalize_single_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000000)
    parser.add_argument("--file", type=str, help="Normalize a single file.")
    args = parser.parse_args()

    config = load_config()

    project_root = Path(config["project"]["root"])
    raw_drive = project_root / config["storage"]["raw_drive"]
    normalized = project_root / config["storage"]["normalized"]
    logs = project_root / config["storage"]["logs"]

    print("=" * 70)
    print("Document Normalization")
    print("=" * 70)
    print(f"Raw drive     : {raw_drive}")
    print(f"Normalized dir: {normalized}")
    print(f"Limit         : {args.limit}")
    print()

    if args.file:
        file_path = Path(args.file)
    
        if not file_path.is_absolute():
            file_path = project_root / file_path

        document, outpath = normalize_single_file(
            path=file_path,
            raw_drive=raw_drive,
            normalized_dir=normalized,
        )

        results = {
            "mode": "single_file",
            "attempted": 1,
            "succeeded": 1,
            "failed": 0,
            "skipped": 0,
            "outputs": [str(outpath)],
            "errors": [],
        }

    else:
        results = normalize_files(
            raw_drive=raw_drive,
            normalized_dir=normalized,
            limit=args.limit,
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs / f"normalization_{timestamp}.json"

    with log_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Attempted : {results['attempted']}")
    print(f"Succeeded : {results['succeeded']}")
    print(f"Failed    : {results['failed']}")
    print(f"Skipped   : {results['skipped']}")
    print()
    print("Parser Usage")
    print("-" * 70)

    for parser_name, count in results.get("parser_counts", {}).items():
        print(f"{parser_name:15} {count:8,d}")
    
    print(f"Log file  : {log_path}")


if __name__ == "__main__":
    main()
