#!/usr/bin/env python3
"""Audit governed subject mappings against normalized schedule observations."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_config
from app.reasoning.schedule_analysis import ScheduleAnalysisService
from app.reasoning.subject_crosswalk_audit import SubjectCrosswalkAuditService
from app.reasoning.subject_mapping_inventory import (
    ScheduleSubjectMappingInventoryService,
    compare_subject_mapping_reports,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory production schedule subjects using governed registry mappings only."
    )
    parser.add_argument("--schedule-root", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/settings.yaml"))
    parser.add_argument("--output-dir", type=Path, help="Write JSON, CSV, review queue, and Markdown in one pass.")
    parser.add_argument("--json", action="store_true", help="Print the complete report as JSON.")
    parser.add_argument("--csv", action="store_true", help="Print subject inventory as CSV.")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("OLD_REPORT", "NEW_REPORT"))
    parser.add_argument("--subject", action="append", help="Show one governed or observed subject (repeatable).")
    parser.add_argument("--sec", action="store_true", help="Show the seven governed SEC subject prefixes.")
    return parser.parse_args()


def _schedule_root(args) -> Path:
    if args.schedule_root:
        return args.schedule_root
    configured = Path(load_config(args.config)["schedule_ingestion"]["normalized_output"])
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


def _write_csv(rows, destination) -> None:
    dictionaries = [row.to_dict() for row in rows]
    if not dictionaries:
        destination.write("") if hasattr(destination, "write") else None
        return
    writer = csv.DictWriter(destination, fieldnames=list(dictionaries[0]))
    writer.writeheader(); writer.writerows(dictionaries)


def _selected_rows(report, subjects=None, sec=False):
    selected = {value.strip().upper() for value in (subjects or ())}
    if sec:
        from app.reasoning.subject_crosswalk_audit import SEC_SUBJECTS
        selected.update(SEC_SUBJECTS)
    return tuple(row for row in report.subject_inventory if not selected or row.subject_code in selected)


def _markdown(report, rows=None) -> str:
    coverage = report.coverage
    lines = [
        "# Schedule Subject Mapping Audit", "",
        f"- Schedule observations: {coverage.total_schedule_observations:,}",
        f"- Subject codes: {coverage.total_subject_codes:,}",
        f"- Observation coverage: {coverage.observation_level_coverage_percent:.3f}%",
        f"- Subject-code coverage: {coverage.subject_code_level_coverage_percent:.3f}%",
        f"- Registry fingerprint: `{report.registry_fingerprint}`", "",
        "## Subject inventory", "",
        "| Subject | Offerings | Instructors | Terms | Status | Academic unit | Review |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for row in rows if rows is not None else report.subject_inventory:
        lines.append(
            f"| {row.subject_code} | {row.course_offering_count} | "
            f"{row.distinct_instructor_count} | {row.term_count} | "
            f"{row.mapping_status} | {row.academic_unit_name or ''} | "
            f"{row.review_status or ''} |"
        )
    lines.extend(["", "## Prioritized review queue", ""])
    for index, row in enumerate(report.review_queue, 1):
        lines.append(
            f"{index}. **{row.subject_code}** — {row.course_offering_count} offerings; "
            f"{row.term_count} terms; {row.distinct_instructor_count} published instructor identities."
        )
    return "\n".join(lines) + "\n"


def _write_outputs(report, output_dir: Path, rows=None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "subject_mapping_audit.json").write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output_dir / "subject_inventory.csv").open("w", encoding="utf-8", newline="") as handle:
        _write_csv(rows if rows is not None else report.subject_inventory, handle)
    with (output_dir / "subject_review_queue.csv").open("w", encoding="utf-8", newline="") as handle:
        _write_csv(report.review_queue, handle)
    (output_dir / "subject_mapping_audit.md").write_text(_markdown(report, rows), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.compare:
        old = json.loads(args.compare[0].read_text(encoding="utf-8"))
        new = json.loads(args.compare[1].read_text(encoding="utf-8"))
        print(json.dumps(compare_subject_mapping_reports(old, new).to_dict(), indent=2, sort_keys=True))
        return 0

    registry_audit = SubjectCrosswalkAuditService().audit()
    registry_audit.raise_for_errors()
    analysis = ScheduleAnalysisService(_schedule_root(args))
    report = ScheduleSubjectMappingInventoryService(analysis.mapping_service).build(
        analysis.load_observations()
    )
    rows = _selected_rows(report, args.subject, args.sec)
    if args.output_dir:
        _write_outputs(report, args.output_dir, rows)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    elif args.csv:
        _write_csv(rows, sys.stdout)
    else:
        coverage = report.coverage
        print("Schedule subject mapping audit")
        print(f"Observations: {coverage.total_schedule_observations}")
        print(f"Subject codes: {coverage.total_subject_codes}")
        print(f"Observation coverage: {coverage.observation_level_coverage_percent:.3f}%")
        print(f"Subject-code coverage: {coverage.subject_code_level_coverage_percent:.3f}%")
        print(f"Review queue: {len(report.review_queue)}")
        if args.subject or args.sec:
            print(f"Selected subject rows present: {len(rows)}")
            for row in rows:
                print(f"  {row.subject_code}: {row.course_offering_count} offerings; {row.distinct_instructor_count} instructors; {row.first_supported_term or '-'} to {row.last_supported_term or '-'}; {row.mapping_status}; {row.analytical_academic_unit_id or '-'}")
        print(f"Fingerprint: {report.deterministic_report_fingerprint}")
        if args.output_dir:
            print(f"Reports: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
