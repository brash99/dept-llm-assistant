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


def load_normalization_sources(config, project_root):
    """
    Load and validate the configured normalization source registry.

    Lower priority values are normalized first. This determines which source
    becomes canonical when byte-identical content exists in multiple sources.
    """
    configured = config.get("normalization_sources", [])

    if not configured:
        raise ValueError(
            "No normalization_sources are configured in "
            "config/settings.yaml"
        )

    sources = []

    seen_keys = set()
    seen_roots = set()

    for item in configured:
        if not isinstance(item, dict):
            raise TypeError(
                "Each normalization_sources entry must be a mapping."
            )

        key = str(item.get("key", "")).strip()
        root_value = str(item.get("root", "")).strip()

        if not key:
            raise ValueError(
                "Every normalization source requires a non-empty key."
            )

        if not root_value:
            raise ValueError(
                f"Normalization source {key!r} requires a root."
            )

        if key in seen_keys:
            raise ValueError(
                f"Duplicate normalization source key: {key}"
            )

        root = Path(root_value)

        if not root.is_absolute():
            root = project_root / root

        root = root.resolve()

        if root in seen_roots:
            raise ValueError(
                f"Duplicate normalization source root: {root}"
            )

        priority = int(item.get("priority", 1000))

        sources.append(
            {
                "key": key,
                "root": root,
                "priority": priority,
                "description": item.get("description", ""),
            }
        )

        seen_keys.add(key)
        seen_roots.add(root)

    return sorted(
        sources,
        key=lambda source: (
            source["priority"],
            source["key"],
        ),
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
        type=str,
        default="all",
        help=(
            "Normalization source key from config/settings.yaml, "
            "or 'all'."
        ),
    )

    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List configured normalization sources and exit.",
    )

    args = parser.parse_args()

    config = load_config()

    project_root = Path(
        config["project"]["root"]
    )

    storage_cfg = config["storage"]

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

    registry = load_normalization_sources(
        config,
        project_root,
    )

    if args.list_sources:
        print("Configured normalization sources:")
        for source in registry:
            exists = source["root"].exists()
            print(
                f"{source['priority']:4d}  "
                f"{source['key']:24s}  "
                f"{'present' if exists else 'missing':7s}  "
                f"{source['root']}"
            )
        return

    available_keys = {
        source["key"]
        for source in registry
    }

    if args.source == "all":
        selected_sources = registry
    else:
        if args.source not in available_keys:
            choices = ", ".join(sorted(available_keys))
            raise SystemExit(
                f"Unknown source {args.source!r}. "
                f"Configured sources: {choices}"
            )

        selected_sources = [
            source
            for source in registry
            if source["key"] == args.source
        ]

    sources = [
        {
            "key": source["key"],
            "root": source["root"],
        }
        for source in selected_sources
    ]

    print("=" * 70)
    print("Multi-Source Document Normalization")
    print("=" * 70)

    for source in selected_sources:
        status = (
            "present"
            if source["root"].exists()
            else "missing"
        )

        print(
            f"{source['priority']:4d}  "
            f"{source['key']:24s}  "
            f"{status:7s}  "
            f"{source['root']}"
        )

    print(f"Normalized dir : {normalized}")
    print(f"Limit          : {args.limit}")
    print()

    if args.file:
        file_path = Path(args.file)

        if not file_path.is_absolute():
            file_path = project_root / file_path

        file_path = file_path.resolve()

        matched_source = None

        for source in selected_sources:
            source_root = source["root"]

            try:
                file_path.relative_to(source_root)
                matched_source = source
                break
            except ValueError:
                continue

        if matched_source is None:
            raise SystemExit(
                "The requested file is not beneath any selected "
                "normalization source root."
            )

        document, outpath = normalize_single_file(
            path=file_path,
            raw_drive=matched_source["root"],
            normalized_dir=normalized,
            source_key=matched_source["key"],
        )

        results = {
            "mode": "single_file",
            "attempted": 1,
            "succeeded": 1,
            "failed": 0,
            "skipped": 0,
            "skipped_duplicate_content": 0,
            "source_counts": {
                matched_source["key"]: 1,
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
