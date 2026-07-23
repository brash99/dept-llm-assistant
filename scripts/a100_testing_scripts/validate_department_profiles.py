#!/usr/bin/env python3
"""Validate production department-profile artifacts compactly."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.institutional_units import AcademicUnitRegistry


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path):
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def validate(root, expected_workforce_count=282):
    first_root, second_root = root / "profiles_1", root / "profiles_2"
    for path in first_root.iterdir():
        other = second_root / path.name
        if not other.is_file() or path.read_bytes() != other.read_bytes():
            raise ValueError(f"nondeterministic department-profile output: {path.name}")
    first = _json(first_root / "department_profile_summary.json")
    second = _json(second_root / "department_profile_summary.json")
    if first["deterministic_fingerprint"] != second["deterministic_fingerprint"]:
        raise ValueError("department-profile fingerprints differ")
    population = _json(root / "workforce/analytical_workforce_population.json")
    decisions = _jsonl(root / "workforce/analytical_workforce_decisions.jsonl")
    profiles = _jsonl(first_root / "department_profiles.jsonl")
    if population["workforce_review_required_count"] != 0 or population["department_assignment_review_required_count"] != 0:
        raise ValueError("analytical workforce review remains")
    if population["workforce_included_count"] != expected_workforce_count:
        raise ValueError(f"expected {expected_workforce_count} included identities")
    included = {item["faculty_identity_id"] for item in decisions if item["workforce_disposition"] == "include"}
    members = [identity_id for profile in profiles for identity_id in profile["faculty_identity_ids"]]
    if len(members) != len(set(members)) or set(members) != included:
        raise ValueError("included workforce identities do not appear exactly once")
    if sum(item["analytical_workforce_count"] for item in profiles) != len(included):
        raise ValueError("department workforce total does not reconcile")
    units = {item.unit_id: item for item in AcademicUnitRegistry.load().units}
    if any(item["academic_unit_id"] not in units or not units[item["academic_unit_id"]].is_department_workforce_unit for item in profiles):
        raise ValueError("unknown or non-department unit in profiles")
    if first["analytical_workforce_denominator_ready"] is not True:
        raise ValueError("analytical workforce denominator is not ready")
    if first["authoritative_hr_denominator_ready"] is not False:
        raise ValueError("authoritative HR readiness was overstated")
    counts = sorted(
        ((item["department_name"], item["analytical_workforce_count"], item["section_count"]) for item in profiles),
        key=lambda item: item[0].casefold(),
    )
    return {
        "status": "passed", "deterministic_fingerprint": first["deterministic_fingerprint"],
        "department_profile_count": len(profiles), "analytical_workforce_count": len(included),
        "department_workforce_total": sum(item["analytical_workforce_count"] for item in profiles),
        "workforce_review_remaining": 0, "department_assignment_review_remaining": 0,
        "analytical_workforce_denominator_ready": True,
        "authoritative_hr_denominator_ready": False,
        "departments_with_teaching_history": sum(bool(item["teaching_assignment_count"]) for item in profiles),
        "departments_with_complete_enrollment": first["departments_with_enrollment"],
        "departments_with_complete_sch": first["departments_with_sch"],
        "department_counts": counts,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    summary = validate(args.run_root)
    (args.run_root / "production_validation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Department Profile Production Validation", ""] + [
        f"- {key}: {value}" for key, value in summary.items() if key != "department_counts"
    ] + ["", "| Department | Workforce | Sections |", "|---|---:|---:|"] + [
        f"| {name} | {workforce} | {sections} |" for name, workforce, sections in summary["department_counts"]
    ]
    (args.run_root / "production_validation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    compact = {key: value for key, value in summary.items() if key != "department_counts"}
    compact["department_counts"] = summary["department_counts"]
    print(json.dumps(compact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
