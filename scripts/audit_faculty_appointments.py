#!/usr/bin/env python3
"""Audit explicit appointment-related evidence without deriving employment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.faculty_appointments import FacultyAppointmentObservationService  # noqa: E402
from app.metric_readiness_audit import load_normalized_objects  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--normalized-root", type=Path, default=Path("storage/normalized")
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Faculty Appointment Evidence Audit",
        "",
        "> These are source-scoped observations, not derived workforce records.",
        "",
        f"- Deterministic fingerprint: `{payload['deterministic_fingerprint']}`",
        f"- Candidate source objects: {summary['candidate_source_object_count']}",
        f"- Faculty appointment observations: {summary['faculty_appointment_observation_count']}",
        f"- Administrative appointment observations: {summary['administrative_appointment_observation_count']}",
        f"- Employment-status observations: {summary['employment_status_observation_count']}",
        f"- Teaching assignments not converted to appointments: {summary['teaching_assignment_not_appointment_count']}",
        f"- Identity-link coverage: {summary['identity_link_coverage_percent']}%",
        f"- Unit-resolution coverage: {summary['unit_resolution_coverage_percent']}%",
        f"- Duplicate observation IDs: {summary['duplicate_observation_id_count']}",
        "",
        "## Denominator readiness",
        "",
        "| Denominator | Status | Reason |",
        "|---|---|---|",
    ]
    for denominator, value in payload["denominator_readiness"].items():
        lines.append(
            f"| {denominator} | {value['status']} | {value['reason']} |"
        )
    lines += [
        "",
        "## Ambiguous or unlinked examples",
        "",
        "| Person | Source | Reason |",
        "|---|---|---|",
    ]
    for item in summary["ambiguous_or_unlinked_examples"][:20]:
        lines.append(
            f"| {item['observed_person_name']} | {item['source_system']} | "
            f"{item['reason']} |"
        )
    lines += [
        "",
        "No appointment FTE, teaching FTE, tenure-line status, faculty-home "
        "assignment, current employment, or denominator was inferred.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    args = parse_args(argv)
    objects, integrity = load_normalized_objects(args.normalized_root)
    if integrity["invalid_json_count"]:
        print(json.dumps({
            "error": "invalid_normalized_json",
            "invalid_json_count": integrity["invalid_json_count"],
        }, sort_keys=True))
        return 2
    result = FacultyAppointmentObservationService().audit(objects)
    payload = result.summary_dict()
    payload["integrity"] = integrity
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "faculty_appointment_audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "faculty_appointment_audit.md").write_text(
        _markdown(payload), encoding="utf-8"
    )
    manifests = (
        ("faculty_appointment_observations.jsonl", result.faculty_appointments),
        ("administrative_appointment_observations.jsonl", result.administrative_appointments),
        ("employment_status_observations.jsonl", result.employment_statuses),
    )
    for filename, observations in manifests:
        with (args.output_dir / filename).open("w", encoding="utf-8") as handle:
            for observation in observations:
                handle.write(json.dumps(observation.to_dict(), sort_keys=True) + "\n")
    compact = {
        "fingerprint": result.deterministic_fingerprint,
        **result.summary,
        "denominator_readiness": result.denominator_readiness,
        "invalid_json": integrity["invalid_json_count"],
        "reports": str(args.output_dir),
    }
    print(json.dumps(payload if args.json else compact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
