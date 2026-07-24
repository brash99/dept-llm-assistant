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


def _previous_profiles(root):
    candidates = sorted(
        (
            path for path in root.parent.glob("department_profiles_*")
            if path != root and (path / "profiles_1/department_profiles.jsonl").is_file()
        ),
        reverse=True,
    )
    return _jsonl(candidates[0] / "profiles_1/department_profiles.jsonl") if candidates else ()


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
    previous_profiles = _previous_profiles(root)
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
    coverage = _json(root / "coverage/department_instructional_coverage.json")
    department_coverage = coverage["department_instructional_coverage"]
    for item in department_coverage:
        if item["owned_subject_teaching_assignment_count"] and not item["profile_teaching_assignment_count"]:
            raise ValueError(f"lost governed owned-subject activity: {item['academic_unit_id']}")
    prefix_rows = coverage["subject_prefix_coverage"]
    philosophy = {
        item["subject_prefix"]: item for item in prefix_rows
        if item["subject_prefix"] in {"PHIL", "RSTD"}
    }
    if set(philosophy) != {"PHIL", "RSTD"} or any(
        item["mapped_profile_unit_id"] != "academic_unit:department_philosophy_religion"
        for item in philosophy.values()
    ):
        raise ValueError("PHIL/RSTD governed ownership did not reach Philosophy and Religion")
    if coverage["subject_prefixes_without_governed_owners"]:
        missing = sorted(
            item["subject_prefix"] for item in prefix_rows
            if item["mapping_result"] in {"missing_owner", "otherwise_unmapped"}
        )
        raise ValueError(f"production subject prefixes lack governed ownership: {missing}")
    sch_root = root / "sch_completeness_1"
    for path in sch_root.iterdir():
        other = root / "sch_completeness_2" / path.name
        if not other.is_file() or path.read_bytes() != other.read_bytes():
            raise ValueError(f"nondeterministic SCH audit output: {path.name}")
    sch_audit = _json(sch_root / "sch_completeness_audit.json")
    if len(sch_audit["missing_sections"]) != sch_audit["missing_section_count"]:
        raise ValueError("missing SCH section accounting does not reconcile")
    if any(not item["reason_codes"] for item in sch_audit["missing_sections"]):
        raise ValueError("an SCH-missing section lacks a forensic reason")
    if sch_audit["remaining_unrepaired_normalization_failure_count"]:
        raise ValueError("unrepaired SCH normalization failures remain")
    sch_by_unit = {item["academic_unit_id"]: item for item in sch_audit["departments"]}
    counts = sorted(({
        "department": item["department_name"], "faculty": item["analytical_workforce_count"],
        "sections": item["section_count"],
        "sch_ready_sections": sch_by_unit[item["academic_unit_id"]]["sch_ready_sections"],
        "sch_completeness_percent": sch_by_unit[item["academic_unit_id"]]["sch_completeness_percent"],
        "known_sch": sch_by_unit[item["academic_unit_id"]]["known_sch"],
        "missing_sch_sections": sch_by_unit[item["academic_unit_id"]]["missing_section_count"],
    } for item in profiles), key=lambda item: item["department"].casefold())
    previous_sch = {
        item["academic_unit_id"]: item.get("student_credit_hours")
        for item in previous_profiles
    }
    sch_changes = []
    for item in sorted(profiles, key=lambda value: value["department_name"].casefold()):
        if item["academic_unit_id"] not in previous_sch:
            continue
        before = previous_sch[item["academic_unit_id"]]
        after = item.get("student_credit_hours")
        if before != after:
            sch_changes.append({
                "academic_unit_id": item["academic_unit_id"],
                "department": item["department_name"],
                "before_sch": before,
                "after_sch": after,
                "change": (
                    round(float(after or 0) - float(before or 0), 6)
                    if before is not None or after is not None else 0.0
                ),
            })
    return {
        "status": "passed", "deterministic_fingerprint": first["deterministic_fingerprint"],
        "department_profile_count": len(profiles), "analytical_workforce_count": len(included),
        "department_workforce_total": sum(item["analytical_workforce_count"] for item in profiles),
        "workforce_review_remaining": 0, "department_assignment_review_remaining": 0,
        "analytical_workforce_denominator_ready": True,
        "authoritative_hr_denominator_ready": False,
        "total_discovered_teaching_assignments": coverage["total_discovered_teaching_assignments"],
        "teaching_assignments_mapped_through_subject_ownership": coverage["teaching_assignments_mapped_through_subject_ownership"],
        "teaching_assignments_linked_through_home_faculty": coverage["teaching_assignments_linked_through_home_faculty"],
        "unmapped_teaching_assignments": coverage["unmapped_teaching_assignments"],
        "subject_prefixes_with_governed_owners": coverage["subject_prefixes_with_governed_owners"],
        "subject_prefixes_without_governed_owners": coverage["subject_prefixes_without_governed_owners"],
        "unmapped_subject_prefixes": [
            item["subject_prefix"] for item in prefix_rows
            if item["mapping_result"] in {"missing_owner", "otherwise_unmapped"}
        ],
        "departments_with_teaching_history": first["departments_with_teaching_history"],
        "departments_with_enrollment_evidence": first["departments_with_enrollment"],
        "departments_with_complete_enrollment": first["departments_with_complete_enrollment"],
        "departments_with_any_known_sch": first["departments_with_sch"],
        "departments_with_complete_sch": first["departments_with_complete_sch"],
        "incomplete_departments": sch_audit["incomplete_departments"],
        "missing_sch_section_count": sch_audit["missing_section_count"],
        "automatic_sch_repair_count": sch_audit["automatic_repair_count"],
        "remaining_unrepaired_normalization_failures": sch_audit[
            "remaining_unrepaired_normalization_failure_count"
        ],
        "sch_reason_breakdown": sch_audit["reason_breakdown"],
        "top_affected_courses": list(sch_audit["systematic_patterns"]["by_course"].items())[:20],
        "top_affected_departments": list(sch_audit["systematic_patterns"]["by_department"].items())[:10],
        "department_counts": counts,
        "department_sch_changes_from_previous_run": sch_changes,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    summary = validate(args.run_root)
    (args.run_root / "production_validation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Department Profile Production Validation", ""] + [
        f"- {key}: {value}" for key, value in summary.items()
        if key not in {"department_counts", "department_sch_changes_from_previous_run"}
    ] + ["", "| Department | Faculty | Sections | SCH-ready | Complete | Known SCH | Missing |", "|---|---:|---:|---:|---:|---:|---:|"] + [
        f"| {item['department']} | {item['faculty']} | {item['sections']} | {item['sch_ready_sections']} | {item['sch_completeness_percent']}% | {item['known_sch']} | {item['missing_sch_sections']} |" for item in summary["department_counts"]
    ]
    if summary["department_sch_changes_from_previous_run"]:
        lines += [
            "", "## SCH changes from previous production profile run", "",
            "| Department | Before | After | Change |",
            "|---|---:|---:|---:|",
        ] + [
            f"| {item['department']} | {item['before_sch']} | {item['after_sch']} | {item['change']} |"
            for item in summary["department_sch_changes_from_previous_run"]
        ]
    (args.run_root / "production_validation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    compact = {key: value for key, value in summary.items() if key != "department_counts"}
    compact["department_counts"] = summary["department_counts"]
    print(json.dumps(compact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
