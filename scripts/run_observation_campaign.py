#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from app.acquisition.campaign import (
    ObservationCampaign,
    ObservationCampaignRunner,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run a governed ISO observation campaign."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "config/observers_v2.yaml"
        ),
    )

    parser.add_argument(
        "--observer",
        action="append",
        default=None,
        help=(
            "Run only the named observer. "
            "May be supplied more than once."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "storage/campaigns/"
            "latest_campaign.json"
        ),
    )

    return parser.parse_args()


def print_campaign(
    campaign: ObservationCampaign,
) -> None:
    print()
    print("ISO Observation Campaign")
    print("=" * 76)
    print(f"Key:         {campaign.key}")
    print(f"Name:        {campaign.name}")
    print(
        f"Observers:   "
        f"{len(campaign.observers):,}"
    )
    print(
        f"Budget:      "
        f"{campaign.observation_budget:,}"
    )

    if campaign.description:
        print(
            f"Description: {campaign.description}"
        )

    print()
    print(
        f"{'Observer':32}"
        f"{'Budget':>10}"
        f"{'Media policy':>28}"
    )
    print("-" * 76)

    for observer in campaign.observers:
        media = []

        policy = observer.media_policy

        if policy.follow_html:
            media.append("HTML")
        if policy.follow_pdf:
            media.append("PDF")
        if policy.follow_docx:
            media.append("DOCX")
        if policy.follow_xlsx:
            media.append("XLSX")
        if policy.follow_csv:
            media.append("CSV")
        if policy.follow_text:
            media.append("TEXT")

        print(
            f"{observer.name:32}"
            f"{observer.budget:10,d}"
            f"{', '.join(media):>28}"
        )


def print_report(report) -> None:
    print()
    print("Campaign Results")
    print("=" * 76)
    print(
        f"Observed:    "
        f"{report.observations_acquired:,}"
        f" / {report.configured_budget:,}"
    )
    print(
        f"Completion:  "
        f"{100 * report.completion:.1f}%"
    )
    print(
        f"Attempted:   "
        f"{report.observations_attempted:,}"
    )
    print(
        f"Failures:    "
        f"{report.failed_resources:,}"
    )

    print()
    print("Media")
    print("-" * 76)

    for media_type, count in (
        report.media_counts.items()
    ):
        print(
            f"{media_type:56}"
            f"{count:10,d}"
        )

    print()
    print("Observer Results")
    print("-" * 76)
    print(
        f"{'Observer':32}"
        f"{'Observed':>10}"
        f"{'Budget':>10}"
        f"{'Complete':>12}"
        f"{'Failed':>10}"
    )

    for observer in report.observer_reports:
        print(
            f"{observer.observer_name:32}"
            f"{observer.observations_acquired:10,d}"
            f"{observer.budget:10,d}"
            f"{100 * observer.completion:11.1f}%"
            f"{observer.failed_resources:10,d}"
        )


def main():
    args = parse_args()

    project_root = Path.cwd().resolve()

    config_path = args.config

    if not config_path.is_absolute():
        config_path = (
            project_root / config_path
        )

    campaign = ObservationCampaign.from_yaml(
        config_path,
        project_root=project_root,
    )

    print_campaign(campaign)

    if args.dry_run:
        print()
        print("Dry run complete.")
        return

    runner = ObservationCampaignRunner(
        campaign
    )

    report = runner.run(
        observer_names=args.observer
    )

    print_report(report)

    report_path = args.report

    if not report_path.is_absolute():
        report_path = (
            project_root / report_path
        )

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path.write_text(
        json.dumps(
            report.to_dict(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(f"Campaign report: {report_path}")


if __name__ == "__main__":
    main()
