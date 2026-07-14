#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from app.acquisition import (
    AcquisitionManifest,
    AcquisitionMethod,
    DirectoryAcquisitionRunner,
    FilesystemAcquisitionService,
    SourceAuthority,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Acquire a directory tree into the ISO "
            "SourceDocument manifest."
        )
    )

    parser.add_argument(
        "directory",
        type=Path,
        help="Directory to scan.",
    )

    parser.add_argument(
        "--storage-root",
        type=Path,
        default=None,
        help=(
            "Root used for SourceDocument relative paths. "
            "Defaults to the scanned directory."
        ),
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "storage/manifests/acquisition.jsonl"
        ),
        help="JSONL acquisition manifest path.",
    )

    parser.add_argument(
        "--source-organization",
        required=True,
        help=(
            "Organization from which the files originated."
        ),
    )

    parser.add_argument(
        "--authority",
        choices=[
            item.value
            for item in SourceAuthority
        ],
        required=True,
    )

    parser.add_argument(
        "--method",
        choices=[
            item.value
            for item in AcquisitionMethod
        ],
        required=True,
    )

    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="Scan only the immediate directory.",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the report as JSON.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    directory = args.directory.resolve()
    storage_root = (
        args.storage_root.resolve()
        if args.storage_root is not None
        else directory
    )

    filesystem_service = FilesystemAcquisitionService(
        storage_root
    )

    manifest = AcquisitionManifest(args.manifest)

    runner = DirectoryAcquisitionRunner(
        filesystem_service=filesystem_service,
        manifest=manifest,
    )

    report = runner.run(
        directory=directory,
        source_organization=args.source_organization,
        authority=SourceAuthority(args.authority),
        acquisition_method=AcquisitionMethod(
            args.method
        ),
        recursive=not args.non_recursive,
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
    print("ISO Acquisition Summary")
    print("=" * 50)
    print(f"Directory:          {report.directory}")
    print(f"Files examined:     {report.files_examined}")
    print(f"New:                {report.new_documents}")
    print(f"Unchanged:          {report.unchanged_documents}")
    print(f"Changed:            {report.changed_documents}")
    print(f"Duplicate content:  {report.duplicate_documents}")
    print(f"Failed:             {report.failed_documents}")
    print(f"Elapsed seconds:    {report.elapsed_seconds:.3f}")

    if report.failures:
        print()
        print("Failures")
        print("-" * 50)

        for failure in report.failures:
            print(
                f"{failure.relative_path}: "
                f"{failure.error_type}: "
                f"{failure.message}"
            )


if __name__ == "__main__":
    main()
