#!/usr/bin/env python3
"""Audit and deterministically repair department SCH completeness."""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.department_profiles import (  # noqa: E402
    _repair_sch_rows, _schedule_row, _unique_sections, _valid_number,
)
from app.faculty_identity import FacultyIdentityService  # noqa: E402
from app.metric_readiness_audit import load_normalized_objects  # noqa: E402
from app.reasoning.academic_unit_mapping import AcademicUnitMappingService  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-root", type=Path, default=Path("storage/normalized"))
    parser.add_argument("--workforce-output", type=Path, required=True)
    parser.add_argument("--profiles-output", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    objects, integrity = load_normalized_objects(args.normalized_root)
    if integrity["invalid_json_count"]:
        raise ValueError("Normalized corpus contains invalid JSON")
    workforce = args.workforce_output.parent if args.workforce_output.is_file() else args.workforce_output
    profile_root = args.profiles_output.parent if args.profiles_output.is_file() else args.profiles_output
    decisions = _jsonl(workforce / "analytical_workforce_decisions.jsonl")
    profiles = _jsonl(profile_root / "department_profiles.jsonl")
    identity_audit = FacultyIdentityService().audit(objects)
    schedule_identity = {
        source.knowledge_object_id: identity.identity_id
        for identity in identity_audit.identities for source in identity.source_observations
        if source.source_system == "schedule"
    }
    home = {item["faculty_identity_id"]: item["analytical_academic_unit_id"] for item in decisions if item["workforce_disposition"] == "include"}
    mapper = AcademicUnitMappingService()
    raw_rows = tuple(
        _schedule_row(item, schedule_identity, home, mapper)
        for item in objects if item.get("object_type") == "course_offering_observation"
    )
    repaired_rows, repairs = _repair_sch_rows(raw_rows)
    duplicate_repairs = tuple(
        {"section_key": row["section_key"], "method": method, "field": method.removeprefix("duplicate_section_")}
        for row in _unique_sections(repaired_rows)
        for method in row.get("sch_repairs") or ()
        if method.startswith("duplicate_section_") and not method.endswith("_conflict")
    )
    repairs = tuple(sorted((*repairs, *duplicate_repairs), key=lambda item: (item["section_key"], item["method"])))
    departments, missing = _audit_departments(profiles, raw_rows, repaired_rows)
    payload = {
        "department_count": len(departments),
        "complete_department_count": sum(item["status"] == "COMPLETE" for item in departments),
        "incomplete_department_count": sum(item["status"] == "INCOMPLETE" for item in departments),
        "incomplete_departments": [item["department_name"] for item in departments if item["status"] == "INCOMPLETE"],
        "missing_section_count": len(missing), "automatic_repair_count": len(repairs),
        "catalog_course_credit_evidence_available": False,
        "structured_cross_list_evidence_available": False,
        "departments": departments, "missing_sections": missing,
        "repairs": list(repairs),
    }
    payload["deterministic_fingerprint"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _csv(args.output_dir / "department_sch_completeness.csv", departments)
    _csv(args.output_dir / "missing_sch_sections.csv", missing)
    _jsonl_write(args.output_dir / "missing_sch_sections.jsonl", missing)
    _jsonl_write(args.output_dir / "sch_repairs.jsonl", repairs)
    (args.output_dir / "sch_completeness_audit.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "sch_completeness_audit.md").write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key not in {"departments", "missing_sections", "repairs"}}, indent=2, sort_keys=True))
    return 0


def _audit_departments(profiles, raw_rows, repaired_rows):
    departments, missing = [], []
    for profile in profiles:
        member_ids = set(profile["faculty_identity_ids"])
        raw_activity = _activity(raw_rows, member_ids, profile["academic_unit_id"])
        activity = _activity(repaired_rows, member_ids, profile["academic_unit_id"])
        raw_sections, sections = _unique_sections(raw_activity), _unique_sections(activity)
        missing_sections = [row for row in sections if not (_valid_number(row["enrollment"], integer=True) and _valid_number(row["credits"]))]
        known_enrollment = sum(row["enrollment"] for row in sections if _valid_number(row["enrollment"], integer=True))
        affected_enrollment = sum(row["enrollment"] for row in missing_sections if _valid_number(row["enrollment"], integer=True))
        section_pct = round(100 * len(missing_sections) / len(sections), 6) if sections else 0.0
        enrollment_pct = round(100 * affected_enrollment / known_enrollment, 6) if known_enrollment else None
        for row in missing_sections:
            missing.append(_missing_section(profile, row))
        item = {
            "academic_unit_id": profile["academic_unit_id"], "department_name": profile["department_name"],
            "total_unique_sections": len(sections),
            "sections_with_enrollment": sum(_valid_number(row["enrollment"], integer=True) for row in sections),
            "sections_with_explicit_credits": sum(_valid_number(row["credits"]) for row in sections),
            "sch_ready_sections": len(sections) - len(missing_sections),
            "sch_completeness_percent": round(100 * (len(sections) - len(missing_sections)) / len(sections), 6) if sections else 0.0,
            "known_sch": sum(float(row["credits"]) * int(row["enrollment"]) for row in sections if _valid_number(row["credits"]) and _valid_number(row["enrollment"], integer=True)),
            "missing_sch": None if missing_sections else 0.0,
            "missing_section_count": len(missing_sections),
            "status": "INCOMPLETE" if missing_sections else "COMPLETE",
            "sections_repaired": max(0, sum(_ready(row) for row in sections) - sum(_ready(row) for row in raw_sections)),
            "affected_section_percent": section_pct,
            "affected_known_enrollment_percent": enrollment_pct,
            "potential_sch_affected_percent": None,
            "comparison_impact": _impact(section_pct, enrollment_pct),
            "impact_basis": "maximum of affected-section percentage and affected-known-enrollment percentage; potential SCH is unbounded when an input is absent",
        }
        departments.append(item)
    departments.sort(key=lambda item: (item["status"] == "COMPLETE", item["sch_completeness_percent"], item["department_name"].casefold()))
    missing.sort(key=lambda item: (item["department_name"].casefold(), item["term"], item["subject_prefix"], item["course_number"], item["section"]))
    return departments, missing


def _activity(rows, member_ids, unit_id):
    values = {}
    for row in rows:
        if row["instructor_identity_id"] in member_ids or row["owned_unit_id"] == unit_id:
            key = row["observation_id"] or "|".join((row["section_key"], str(row["instructor_raw"] or "")))
            values.setdefault(key, row)
    return tuple(values[key] for key in sorted(values))


def _missing_section(profile, row):
    reasons = []
    if not _valid_number(row["enrollment"], integer=True):
        reasons.append("missing_enrollment" if row["enrollment"] is None else "invalid_normalization")
    if not _valid_number(row["credits"]):
        method = row.get("credit_resolution_method")
        if method == "legitimate_variable_credit":
            reasons.append("variable_credit")
        elif method == "unresolved_credit_conflict":
            reasons.append("cross_listed_ambiguity" if "cross" in str(row.get("credits_raw") or "").casefold() else "invalid_normalization")
        else:
            reasons.append("missing_credits" if row["credits"] is None else "invalid_normalization")
    reasons.extend(item for item in row.get("sch_repairs") or () if item.endswith("_conflict"))
    return {
        "academic_unit_id": profile["academic_unit_id"], "department_name": profile["department_name"],
        "term": row["term"], "subject_prefix": row["subject"],
        "course_number": row["course_number"] or row["course_code"], "section": row["section"],
        "course_title": row["course_title"], "instructors": list(row.get("instructors") or ((row["instructor_raw"],) if row["instructor_raw"] else ())),
        "enrollment": row["enrollment"], "enrollment_status": "explicit" if _valid_number(row["enrollment"], integer=True) else "missing_or_invalid",
        "credits": row["credits"], "credit_status": "explicit" if _valid_number(row["credits"]) else "missing_variable_or_invalid",
        "reason_codes": sorted(set(reasons)),
        "repairable_from_current_evidence": False,
        "repair_limitation": "no unique explicit scalar value remains in normalized schedule evidence",
        "source_observation_id": row["observation_id"],
    }


def _ready(row):
    return _valid_number(row["credits"]) and _valid_number(row["enrollment"], integer=True)


def _impact(section_pct, enrollment_pct):
    value = max(section_pct, enrollment_pct or 0.0)
    if value <= 1:
        return "negligible"
    if value <= 5:
        return "minor"
    if value <= 15:
        return "moderate"
    return "substantial"


def _jsonl(path):
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _jsonl_write(path, values):
    path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in values), encoding="utf-8")


def _csv(path, rows):
    fields = tuple(rows[0]) if rows else ()
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            for row in rows:
                writer.writerow({key: json.dumps(value) if isinstance(value, list) else value for key, value in row.items()})


def _markdown(payload):
    lines = [
        "# SCH Completeness Audit", "",
        f"- Complete departments: {payload['complete_department_count']}",
        f"- Incomplete departments: {payload['incomplete_department_count']}",
        f"- Missing sections: {payload['missing_section_count']}",
        f"- Automatic repairs: {payload['automatic_repair_count']}", "",
        "| Department | Sections | SCH-ready | Complete % | Known SCH | Missing sections | Status | Impact |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    lines += [f"| {item['department_name']} | {item['total_unique_sections']} | {item['sch_ready_sections']} | {item['sch_completeness_percent']} | {item['known_sch']} | {item['missing_section_count']} | {item['status']} | {item['comparison_impact']} |" for item in payload["departments"]]
    lines += ["", "## Every missing section", "", "| Department | Term | Course | Section | Instructors | Reasons |", "|---|---|---|---|---|---|"]
    lines += [f"| {item['department_name']} | {item['term']} | {item['course_number']} | {item['section']} | {', '.join(item['instructors'])} | {', '.join(item['reason_codes'])} |" for item in payload["missing_sections"]]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
