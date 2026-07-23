#!/usr/bin/env python3
"""Audit schedule-to-department instructional-activity coverage."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.academic_terms import academic_term_sort_key  # noqa: E402
from app.department_profiles import _repair_sch_rows, _schedule_row, _unique_sections  # noqa: E402
from app.faculty_identity import FacultyIdentityService  # noqa: E402
from app.institutional_units import AcademicUnitRegistry  # noqa: E402
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
    profiles_root = args.profiles_output.parent if args.profiles_output.is_file() else args.profiles_output
    decisions = _jsonl(workforce / "analytical_workforce_decisions.jsonl")
    profiles = _jsonl(profiles_root / "department_profiles.jsonl")
    units = AcademicUnitRegistry.load()
    mapper = AcademicUnitMappingService(units)
    identities = FacultyIdentityService().audit(objects).identities
    schedule_identity = {
        source.knowledge_object_id: identity.identity_id
        for identity in identities for source in identity.source_observations
        if source.source_system == "schedule"
    }
    home = {
        item["faculty_identity_id"]: item["analytical_academic_unit_id"]
        for item in decisions if item["workforce_disposition"] == "include"
    }
    schedules = tuple(item for item in objects if item.get("object_type") == "course_offering_observation")
    rows, _ = _repair_sch_rows(tuple(_schedule_row(item, schedule_identity, home, mapper) for item in schedules))
    profile_by_unit = {item["academic_unit_id"]: item for item in profiles}
    prefix_rows = _prefix_matrix(rows, mapper, units, profile_by_unit)
    department_rows = _department_matrix(rows, profiles, home)
    unmapped = [row for row in rows if not row["owned_unit_id"]]
    non_department = [item for item in prefix_rows if item["mapping_result"] == "non_department_owner"]
    semantic = {
        "total_discovered_teaching_assignments": len(rows),
        "teaching_assignments_mapped_through_subject_ownership": sum(bool(row["owned_unit_id"]) for row in rows),
        "teaching_assignments_linked_through_home_faculty": sum(bool(row["home_unit_id"]) for row in rows),
        "unmapped_teaching_assignments": len(unmapped),
        "subject_prefixes_with_governed_owners": sum(item["mapping_result"] in {"mapped", "mapped_through_governed_successor", "non_department_owner", "owner_without_profile"} for item in prefix_rows),
        "subject_prefixes_without_governed_owners": sum(item["mapping_result"] in {"missing_owner", "otherwise_unmapped"} for item in prefix_rows),
        "subject_prefix_coverage": prefix_rows,
        "department_instructional_coverage": department_rows,
    }
    semantic["deterministic_fingerprint"] = hashlib.sha256(json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _csv(args.output_dir / "subject_prefix_coverage.csv", prefix_rows)
    _csv(args.output_dir / "department_instructional_coverage.csv", department_rows)
    _csv(args.output_dir / "enrollment_credit_coverage.csv", prefix_rows, fields=(
        "subject_prefix", "section_count", "sections_with_enrollment", "sections_with_credits", "sch_ready_section_count",
    ))
    _jsonl_write(args.output_dir / "unmapped_teaching_assignments.jsonl", unmapped)
    _jsonl_write(args.output_dir / "non_department_subject_owners.jsonl", non_department)
    (args.output_dir / "department_instructional_coverage.json").write_text(json.dumps(semantic, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "department_instructional_coverage.md").write_text(_markdown(semantic), encoding="utf-8")
    print(json.dumps({key: value for key, value in semantic.items() if key not in {"subject_prefix_coverage", "department_instructional_coverage"}}, indent=2, sort_keys=True))
    return 0


def _prefix_matrix(rows, mapper, units, profiles):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["subject"]].append(row)
    result = []
    for subject in sorted(grouped):
        values = tuple(grouped[subject])
        sections = _unique_sections(values)
        signatures = {(row.get("original_owner_unit_id"), row.get("owned_unit_id"), row.get("subject_mapping_status")) for row in values}
        mapping = mapper.map_subject(subject, values[-1]["term"])
        owner_id = mapping.owning_academic_unit_id if len(signatures) == 1 else None
        owner = units.get(owner_id) if owner_id else None
        target_id = mapping.analytical_academic_unit_id if len(signatures) == 1 else None
        target = units.get(target_id) if target_id else None
        if not owner:
            outcome = "missing_owner" if len(signatures) == 1 and mapping.status == "unmapped" else "otherwise_unmapped"
        elif target and not target.is_department_workforce_unit:
            outcome = "non_department_owner"
        elif target_id not in profiles:
            outcome = "owner_without_profile"
        elif owner.deprecated and target_id in owner.successor_unit_ids:
            outcome = "mapped_through_governed_successor"
        else:
            outcome = "mapped"
        terms = sorted({row["term"] for row in values if row["term"]}, key=academic_term_sort_key)
        result.append({
            "subject_prefix": subject, "teaching_assignment_count": len(values),
            "section_count": len(sections), "earliest_term": terms[0] if terms else None,
            "latest_term": terms[-1] if terms else None,
            "governed_owner_unit_id": owner_id,
            "governed_owner_display_name": mapping.owning_academic_unit_name if owner_id else None,
            "owner_unit_type": owner.formal_unit_type if owner else None,
            "owner_current_status": "historical" if owner and owner.deprecated else "current" if owner else None,
            "mapped_profile_unit_id": target_id if target_id in profiles else None,
            "mapped_department_profile_id": profiles[target_id]["department_profile_id"] if target_id in profiles else None,
            "mapping_result": outcome,
            "sections_with_enrollment": sum(_valid(row["enrollment"], integer=True) for row in sections),
            "sections_with_credits": sum(_valid(row["credits"]) for row in sections),
            "sch_ready_section_count": sum(_valid(row["enrollment"], integer=True) and _valid(row["credits"]) for row in sections),
        })
    return result


def _department_matrix(rows, profiles, home):
    result = []
    for profile in sorted(profiles, key=lambda item: item["academic_unit_id"]):
        unit_id = profile["academic_unit_id"]
        member_ids = set(profile["faculty_identity_ids"])
        home_rows = [row for row in rows if row["instructor_identity_id"] in member_ids]
        owned_rows = [row for row in rows if row["owned_unit_id"] == unit_id]
        result.append({
            "academic_unit_id": unit_id, "department_name": profile["department_name"],
            "home_faculty_count": len(member_ids),
            "home_faculty_teaching_assignment_count": len(home_rows),
            "owned_subject_prefixes": sorted({row["subject"] for row in owned_rows}),
            "owned_subject_teaching_assignment_count": len(owned_rows),
            "activity_excluded_by_filters": 0,
            "unmapped_home_faculty_assignment_count": sum(not row["owned_unit_id"] for row in home_rows),
            "profile_teaching_assignment_count": profile["teaching_assignment_count"],
            "profile_section_count": profile["section_count"],
        })
    return result


def _valid(value, integer=False):
    expected = int if integer else (int, float)
    return isinstance(value, expected) and not isinstance(value, bool) and value >= 0


def _jsonl(path):
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _jsonl_write(path, values):
    path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in values), encoding="utf-8")


def _csv(path, rows, fields=None):
    fields = fields or tuple(rows[0]) if rows else ()
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        if fields:
            writer.writeheader()
            for row in rows:
                writer.writerow({key: json.dumps(value) if isinstance(value, list) else value for key, value in row.items()})


def _markdown(value):
    lines = ["# Department Instructional Coverage", ""] + [
        f"- {key}: {item}" for key, item in value.items()
        if key not in {"subject_prefix_coverage", "department_instructional_coverage"}
    ] + ["", "| Department | Home faculty | Home assignments | Owned assignments | Profile assignments |", "|---|---:|---:|---:|---:|"]
    lines += [f"| {item['department_name']} | {item['home_faculty_count']} | {item['home_faculty_teaching_assignment_count']} | {item['owned_subject_teaching_assignment_count']} | {item['profile_teaching_assignment_count']} |" for item in value["department_instructional_coverage"]]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
