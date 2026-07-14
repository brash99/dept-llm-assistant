#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from app.acquisition import (
    AcquisitionManifest,
    WebAcquisitionRunner,
    WebAcquisitionService,
    WebObserverCatalog,
)
from app.config import load_config


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run configured ISO institutional web observers."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/web_observers.yaml"),
    )

    parser.add_argument(
        "--observer",
        action="append",
        default=None,
        help=(
            "Observer name to run. May be supplied more than once. "
            "Defaults to all enabled observers."
        ),
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List configured observers without running them.",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--json",
        action="store_true",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    app_config = load_config()
    project_root = Path(app_config["project"]["root"])

    config_path = args.config

    if not config_path.is_absolute():
        config_path = project_root / config_path

    catalog = WebObserverCatalog.from_yaml(
        config_path,
        project_root=project_root,
    )

    if args.list:
        for observer in catalog.all():
            status = (
                "enabled"
                if observer.enabled
                else "disabled"
            )

            governance = (
                observer.authorization.mode
                if observer.authorization is not None
                else (
                    "robots_policy"
                    if observer.respect_robots
                    else "UNAUTHORIZED"
                )
            )

            print(
                f"{observer.name:28} "
                f"{status:8} "
                f"{governance:24} "
                f"{', '.join(observer.purposes)}"
            )

        return

    if args.observer:
        observers = []

        for name in args.observer:
            observer = catalog.get(name)

            if observer is None:
                raise SystemExit(
                    f"Unknown observer: {name}"
                )

            observers.append(observer)
    else:
        observers = catalog.enabled()

    reports = []

    for observer in observers:
        print()
        print("=" * 72)
        print(f"Observer: {observer.name}")
        print("=" * 72)

        web_service = WebAcquisitionService(
            observer.storage_root,
        )

        manifest = AcquisitionManifest(
            observer.manifest_path
        )

        runner = WebAcquisitionRunner(
            web_service=web_service,
            manifest=manifest,
            request_delay_seconds=(
                observer.request_delay_seconds
            ),
        )

        observer_totals = {
            "observer": observer.name,
            "purposes": list(observer.purposes),
            "seed_reports": [],
        }

        for seed_url in observer.seed_urls:
            report = runner.run(
                seed_url=seed_url,
                source_organization=(
                    observer.source_organization
                ),
                authority=observer.authority,
                max_pages=(
                    args.max_pages
                    if args.max_pages is not None
                    else observer.max_pages
                ),
                max_depth=(
                    args.max_depth
                    if args.max_depth is not None
                    else observer.max_depth
                ),
                allowed_hosts=observer.allowed_hosts,
                allowed_prefixes=(
                    observer.allowed_prefixes
                ),
                respect_robots=(
                    observer.respect_robots
                ),
            )

            observer_totals["seed_reports"].append(
                report.to_dict()
            )

            print(f"Seed:             {report.seed_url}")
            print(
                f"Pages acquired:   "
                f"{report.pages_acquired}"
            )
            print(
                f"New / unchanged:  "
                f"{report.new_documents} / "
                f"{report.unchanged_documents}"
            )
            print(
                f"Robots denied:    "
                f"{report.robots_denied}"
            )
            print(
                f"Failed:           "
                f"{report.failed_pages}"
            )

        reports.append(observer_totals)

    if args.json:
        print(
            json.dumps(
                reports,
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
