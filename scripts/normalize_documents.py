#!/usr/bin/env python3

import argparse
from datetime import datetime
import json
from pathlib import Path

from app.config import load_config
from app.normalize import (
    normalize_single_file,
    normalize_source_roots,
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=1000000,
    )

    parser.add_argument(
        "--file",
        type=str,
        help="Normalize a single file.",
    )

    parser.add_argument(
        "--source",
        choices=[
            "all",
            "cnu_website",
            "sec_google_drive",
        ],
        default="all",
        help="Acquisition source to normalize.",
    )

    args = parser.parse_args()

    config = load_config()

    project_root = Path(
        config["project"]["root"]
    )

    storage_cfg = config["storage"]

    raw_drive = (
        project_root
        / storage_cfg["raw_drive"]
    )

    raw_web = (
        project_root
        / storage_cfg.get(
            "raw_web",
            "storage/raw_web",
        )
    )

    normalized = (
        project_root
        / storage_cfg["normalized"]
    )

    logs = (
        project_root
        / storage_cfg["logs"]
    )

    logs.mkdir(
        parents=True,
        exist_ok=True,
    )

    configured_sources = {
        "cnu_website": raw_web,
        "sec_google_drive": raw_drive,
    }

    # Public institutional sources are processed first so that, when
    # identical bytes occur in multiple observers, the authoritative
    # public observation becomes the canonical searchable copy.
    source_order = [
        "cnu_website",
        "sec_google_drive",
    ]

    if args.source == "all":
        selected_keys = source_order
    else:
        selected_keys = [args.source]

    sources = [
        {
            "key": key,
            "root": configured_sources[key],
        }
        for key in selected_keys
    ]

    print("=" * 70)
    print("Multi-Source Document Normalization")
    print("=" * 70)

    for source in sources:
        print(
            f"{source['key']:20}: "
            f"{source['root']}"
        )

    print(f"Normalized dir      : {normalized}")
    print(f"Limit               : {args.limit}")
    print()

    if args.file:
        file_path = Path(args.file)

        if not file_path.is_absolute():
            file_path = project_root / file_path

        matched_source_key = None
        matched_source_root = None

        for source in sources:
            source_root = Path(
                source["root"]
            ).resolve()

            try:
                file_path.resolve().relative_to(
                    source_root
                )
                matched_source_key = source["key"]
                matched_source_root = source_root
                break
            except ValueError:
                continue

        if matched_source_key is None:
            raise SystemExit(
                "The requested file is not beneath any "
                "selected source root."
            )

        document, outpath = normalize_single_file(
            path=file_path,
            raw_drive=matched_source_root,
            normalized_dir=normalized,
            source_key=matched_source_key,
        )

        results = {
            "mode": "single_file",
            "attempted": 1,
            "succeeded": 1,
            "failed": 0,
            "skipped": 0,
            "skipped_duplicate_content": 0,
            "source_counts": {
                matched_source_key: 1,
            },
            "parser_counts": {
                document.parser: 1,
            },
            "outputs": [str(outpath)],
            "errors": [],
        }

    else:
        results = normalize_source_roots(
            sources=sources,
            normalized_dir=normalized,
            limit=args.limit,
        )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    log_path = (
        logs
        / f"normalization_{timestamp}.json"
    )

    with log_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            results,
            handle,
            indent=2,
        )

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Attempted : {results['attempted']}")
    print(f"Succeeded : {results['succeeded']}")
    print(f"Failed    : {results['failed']}")
    print(f"Skipped   : {results['skipped']}")
    print(
        "Duplicate-content skips: "
        f"{results.get('skipped_duplicate_content', 0)}"
    )

    print()
    print("Documents by Source")
    print("-" * 70)

    for source_name, count in (
        results.get(
            "source_counts",
            {},
        ).items()
    ):
        print(
            f"{source_name:25} "
            f"{count:8,d}"
        )

    print()
    print("Parser Usage")
    print("-" * 70)

    for parser_name, count in (
        results.get(
            "parser_counts",
            {},
        ).items()
    ):
        print(
            f"{parser_name:25} "
            f"{count:8,d}"
        )

    print()
    print(f"Log file: {log_path}")


if __name__ == "__main__":
    main()
