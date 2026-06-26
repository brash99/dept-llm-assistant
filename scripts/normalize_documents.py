#!/usr/bin/env python3

from pathlib import Path
import argparse
import json
from datetime import datetime

from app.config import load_config
from app.normalize import normalize_files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
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
    print(f"Log file  : {log_path}")


if __name__ == "__main__":
    main()
