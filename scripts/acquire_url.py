#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from app.acquisition import (
    AcquisitionManifest,
    SourceAuthority,
    WebAcquisitionService,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Acquire one web URL into ISO Institutional Memory."
        )
    )

    parser.add_argument("url")

    parser.add_argument(
        "--storage-root",
        type=Path,
        default=Path("storage/raw_web"),
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "storage/manifests/web_acquisition.jsonl"
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
        "--title",
        default=None,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    service = WebAcquisitionService(
        args.storage_root
    )

    document = service.acquire(
        url=args.url,
        source_organization=args.source_organization,
        authority=SourceAuthority(args.authority),
        title=args.title,
    )

    manifest = AcquisitionManifest(args.manifest)
    decision = manifest.record(document)

    print()
    print("ISO Web Acquisition")
    print("=" * 60)
    print(f"Status:        {decision.status.value}")
    print(f"Title:         {document.title}")
    print(f"URL:           {document.source_url}")
    print(f"Stored path:   {document.relative_path}")
    print(f"Media type:    {document.media_type}")
    print(f"SHA-256:       {document.content_hash}")
    print(f"Manifest:      {args.manifest}")
    print()
    print(
        json.dumps(
            document.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
