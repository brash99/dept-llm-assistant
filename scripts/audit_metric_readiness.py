#!/usr/bin/env python3
"""Audit institutional-unit, faculty-observer, and SCH evidence readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.metric_readiness_audit import (  # noqa: E402
    MetricReadinessAuditService,
    load_normalized_objects,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--normalized-root", type=Path, default=Path("storage/normalized"),
        help="Canonical normalized Knowledge Object root.",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    return parser.parse_args(argv)


def _markdown(report: dict, integrity: dict) -> str:
    units = report["institutional_units"]
    faculty = report["faculty_observation"]
    sch = report["sch_readiness"]
    denominators = report["denominator_readiness"]
    lines = [
        "# ISO Metric Readiness Audit",
        "",
        f"- Deterministic fingerprint: `{report['deterministic_fingerprint']}`",
        f"- Normalized objects inspected: {report['provenance']['normalized_object_count']}",
        f"- Invalid JSON: {integrity['invalid_json_count']}",
        f"- Governed academic units: {units['governed_unit_count']}",
        f"- Referenced but not governed unit IDs: {len(units['referenced_but_not_governed'])}",
        f"- Unresolved published unit labels: {len(units['unresolved_published_unit_labels'])}",
        f"- Schedule observations: {sch['schedule_observation_count']}",
        f"- SCH readiness: {sch['readiness_status']}",
        "",
        "## Institutional units",
        "",
        "| Unit | Formal type | Parent | Operational roles |",
        "|---|---|---|---|",
    ]
    for unit in units["governed_academic_units"]:
        lines.append(
            f"| {unit['published_name']} (`{unit['unit_id']}`) | "
            f"{unit['formal_unit_type']} | {unit['parent_unit_id'] or ''} | "
            f"{', '.join(unit['operational_roles'])} |"
        )
    lines += ["", "## Faculty evidence sources", "", "| Source | Object type | Observed objects |", "|---|---|---:|"]
    for source, value in faculty["evidence_sources"].items():
        object_type = value["object_type"]
        observed = faculty["observed_field_coverage"][object_type]["object_count"]
        lines.append(f"| {source} | {object_type} | {observed} |")
    lines += ["", "## SCH input coverage", "", "| Input | Observations |", "|---|---:|"]
    for name, count in sch["input_coverage_counts"].items():
        lines.append(f"| {name} | {count} |")
    lines += ["", "## Denominator readiness", "", "| Denominator | Status |", "|---|---|"]
    for name, value in denominators.items():
        lines.append(f"| {name} | {value['status']} |")
    lines += ["", "## Prioritized backlog", ""]
    for category, items in report["backlog"].items():
        lines.append(f"### {category.replace('_', ' ').title()}")
        lines.append("")
        lines.extend(f"- {item}" for item in items)
        lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict, integrity: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metric_readiness_audit.json").write_text(
        json.dumps({"integrity": integrity, "audit": report}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "metric_readiness_audit.md").write_text(
        _markdown(report, integrity), encoding="utf-8"
    )


def main(argv=None) -> int:
    args = parse_args(argv)
    objects, integrity = load_normalized_objects(args.normalized_root)
    if integrity["invalid_json_count"]:
        print(json.dumps({
            "error": "invalid_normalized_json",
            "invalid_json_count": integrity["invalid_json_count"],
        }, sort_keys=True))
        return 2
    report = MetricReadinessAuditService().audit(
        objects, normalized_root=args.normalized_root
    ).to_dict()
    if args.output_dir:
        write_outputs(report, integrity, args.output_dir)
    if args.json:
        print(json.dumps({"integrity": integrity, "audit": report}, indent=2, sort_keys=True))
    else:
        summary = {
            "fingerprint": report["deterministic_fingerprint"],
            "normalized_objects": report["provenance"]["normalized_object_count"],
            "governed_units": report["institutional_units"]["governed_unit_count"],
            "referenced_but_not_governed": len(report["institutional_units"]["referenced_but_not_governed"]),
            "unresolved_published_unit_labels": len(report["institutional_units"]["unresolved_published_unit_labels"]),
            "schedule_observations": report["sch_readiness"]["schedule_observation_count"],
            "sch_readiness": report["sch_readiness"]["readiness_status"],
            "invalid_json": integrity["invalid_json_count"],
            "reports": str(args.output_dir) if args.output_dir else None,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
