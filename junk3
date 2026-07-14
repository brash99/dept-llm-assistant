#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from app.acquisition import (
    AcquisitionManifest,
    SourceAuthority,
    WebAcquisitionRunner,
    WebAcquisitionService,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Perform a bounded, same-site ISO web acquisition."
        )
    )

    parser.add_argument("seed_url")

    parser.add_argument(
        "--storage-root",
        type=Path,
        default=Path("storage/raw_web"),
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "storage/manifests/cnu_website.jsonl"
        ),
    )

    parser.add_argument(
        "--source-organization",
        required=True,
    )

    parser.add_argument(
        "--authority",
        choices=[
            authority.value
            for authority in SourceAuthority
        ],
        required=True,
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=25,
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
    )

    parser.add_argument(
        "--allowed-host",
        action="append",
        default=None,
        help=(
            "Allowed hostname. May be supplied multiple times. "
            "Defaults to the seed hostname."
        ),
    )

    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        help=(
            "Disable robots.txt enforcement. Do not use for "
            "normal institutional acquisition."
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    web_service = WebAcquisitionService(
        args.storage_root,
    )

    manifest = AcquisitionManifest(
        args.manifest
    )

    runner = WebAcquisitionRunner(
        web_service=web_service,
        manifest=manifest,
        request_delay_seconds=args.delay,
    )

    allowed_hosts = args.allowed_host

    if not allowed_hosts:
        allowed_hosts = [
            urlparse(args.seed_url).netloc
        ]

    report = runner.run(
        seed_url=args.seed_url,
        source_organization=args.source_organization,
        authority=SourceAuthority(args.authority),
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        allowed_hosts=allowed_hosts,
        respect_robots=not args.ignore_robots,
    )

    if args.json:
        print(
            json.dumps(
                report.to_dict(),
                indent=2,
                sort_keys=True,
            )
        )
        return

    print()
    print("ISO Distributed Institutional Observation")
    print("=" * 64)
    print(f"Seed URL:              {report.seed_url}")
    print(f"Pages attempted:       {report.pages_attempted}")
    print(f"Pages acquired:        {report.pages_acquired}")
    print(f"New:                   {report.new_documents}")
    print(f"Unchanged:             {report.unchanged_documents}")
    print(f"Changed:               {report.changed_documents}")
    print(f"Duplicate content:     {report.duplicate_documents}")
    print(f"Robots denied:         {report.robots_denied}")
    print(f"Offsite links skipped: {report.offsite_links_skipped}")
    print(f"Duplicate URLs skipped:{report.duplicate_urls_skipped}")
    print(f"Failed pages:          {report.failed_pages}")
    print(f"Elapsed seconds:       {report.elapsed_seconds:.3f}")
    print(f"Manifest:              {args.manifest}")

    if report.failures:
        print()
        print("Failures")
        print("-" * 64)

        for failure in report.failures:
            print(
                f"{failure.url}: "
                f"{failure.error_type}: "
                f"{failure.message}"
            )


if __name__ == "__main__":
    main()
