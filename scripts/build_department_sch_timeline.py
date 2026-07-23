#!/usr/bin/env python3
"""Build deterministic departmental SCH term and academic-year reports."""

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

from app.academic_terms import academic_term_order, academic_term_sort_key  # noqa: E402
from app.department_profiles import (  # noqa: E402
    _repair_sch_rows,
    _schedule_row,
    _union_rows,
    _unique_sections,
    _valid_number,
)
from app.faculty_identity import FacultyIdentityService  # noqa: E402
from app.metric_readiness_audit import load_normalized_objects  # noqa: E402
from app.reasoning.academic_unit_mapping import AcademicUnitMappingService  # noqa: E402


ALGORITHM = "department_sch_timeline_report"
ALGORITHM_VERSION = "1.0"


def _academic_year(term):
    order = academic_term_order(term)
    if not order.supported:
        raise ValueError(f"Unsupported academic term in SCH timeline: {term}")
    start = order.year if order.period == "fall" else order.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def _term_label(term):
    order = academic_term_order(term)
    if not order.supported:
        raise ValueError(f"Unsupported academic term in SCH timeline: {term}")
    names = {
        "fall": "Fall",
        "spring": "Spring",
        "may": "Maymester",
        "summer_1": "Summer I",
        "extended_summer": "Extended Summer",
        "summer_2": "Summer II",
    }
    return f"{names[order.period]} {order.year}"


def _period(rows):
    sections = _unique_sections(rows)
    if any(
        not _valid_number(item["credits"])
        or not _valid_number(item["enrollment"], integer=True)
        for item in sections
    ):
        raise ValueError("SCH timeline requires SCH-complete Department Profiles")
    instructors = {
        row["instructor_identity_id"] or row["instructor_raw"]
        for row in rows
        if row["instructor_identity_id"] or row["instructor_raw"]
    }
    return {
        "sch": sum(float(item["credits"]) * int(item["enrollment"]) for item in sections),
        "sections": len(sections),
        "enrollment": sum(int(item["enrollment"]) for item in sections),
        "distinct_instructors": len(instructors),
    }


def build_timeline(profiles, rows):
    profiles = tuple(sorted(profiles, key=lambda item: item["academic_unit_id"]))
    terms = tuple(sorted({row["term"] for row in rows}, key=academic_term_sort_key))
    if not terms:
        raise ValueError("No schedule terms found")
    academic_years = tuple(dict.fromkeys(_academic_year(term) for term in terms))
    departments = []
    section_term_assignments = 0
    for profile in profiles:
        members = set(profile["faculty_identity_ids"])
        activity = _union_rows(
            tuple(row for row in rows if row["instructor_identity_id"] in members),
            tuple(row for row in rows if row["owned_unit_id"] == profile["academic_unit_id"]),
        )
        term_values = []
        for term in terms:
            period_rows = tuple(row for row in activity if row["term"] == term)
            values = _period(period_rows)
            term_values.append({
                "academic_term": term,
                "term_label": _term_label(term),
                "academic_year": _academic_year(term),
                **values,
            })
        year_values = []
        for year in academic_years:
            period_rows = tuple(row for row in activity if _academic_year(row["term"]) == year)
            values = _period(period_rows)
            faculty = profile["analytical_workforce_count"]
            year_values.append({
                "academic_year": year,
                **values,
                "sch_per_faculty": round(values["sch"] / faculty, 6) if faculty else None,
            })
        grand = _period(activity)
        faculty = profile["analytical_workforce_count"]
        for field in ("sch", "sections", "enrollment"):
            if sum(item[field] for item in term_values) != grand[field]:
                raise ValueError(
                    f"Term {field} reconciliation failed: "
                    f"{profile['academic_unit_id']}"
                )
            if sum(item[field] for item in year_values) != grand[field]:
                raise ValueError(
                    f"Academic-year {field} reconciliation failed: "
                    f"{profile['academic_unit_id']}"
                )
        section_term_assignments += grand["sections"]
        departments.append({
            "academic_unit_id": profile["academic_unit_id"],
            "department_name": profile["department_name"],
            "faculty": faculty,
            "terms": term_values,
            "academic_years": year_values,
            "grand_total": {
                **grand,
                "sch_per_faculty": round(grand["sch"] / faculty, 6) if faculty else None,
            },
        })
    payload = {
        "algorithm": ALGORITHM,
        "algorithm_version": ALGORITHM_VERSION,
        "academic_year_definition": (
            "Fall of the starting year plus Spring, Maymester, Summer I, "
            "Extended Summer, and Summer II of the following calendar year."
        ),
        "terms": [
            {
                "academic_term": term,
                "term_label": _term_label(term),
                "academic_year": _academic_year(term),
            }
            for term in terms
        ],
        "academic_years": list(academic_years),
        "department_count": len(departments),
        "section_term_assignment_count": section_term_assignments,
        "departments": departments,
    }
    payload["deterministic_fingerprint"] = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-root", type=Path, default=Path("storage/normalized"))
    parser.add_argument("--workforce-output", type=Path, required=True)
    parser.add_argument("--profiles-output", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    workforce_root = args.workforce_output.parent if args.workforce_output.is_file() else args.workforce_output
    profile_root = args.profiles_output.parent if args.profiles_output.is_file() else args.profiles_output
    decisions = _jsonl(workforce_root / "analytical_workforce_decisions.jsonl")
    profiles = _jsonl(profile_root / "department_profiles.jsonl")
    objects, integrity = load_normalized_objects(args.normalized_root)
    if integrity["invalid_json_count"]:
        raise ValueError("Normalized corpus contains invalid JSON")
    identities = FacultyIdentityService().audit(objects).identities
    schedule_identity = {
        source.knowledge_object_id: identity.identity_id
        for identity in identities
        for source in identity.source_observations
        if source.source_system == "schedule"
    }
    home = {
        item["faculty_identity_id"]: item["analytical_academic_unit_id"]
        for item in decisions if item["workforce_disposition"] == "include"
    }
    mapper = AcademicUnitMappingService()
    raw_rows = tuple(
        _schedule_row(item, schedule_identity, home, mapper)
        for item in objects
        if item.get("object_type") == "course_offering_observation"
    )
    rows, _ = _repair_sch_rows(raw_rows)
    payload = build_timeline(profiles, rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(args.output_dir / "department_sch_timeline.json", payload)
    _write_term_csv(args.output_dir / "department_sch_by_term.csv", payload)
    _write_year_csv(args.output_dir / "department_sch_by_academic_year.csv", payload)
    (args.output_dir / "department_sch_timeline.md").write_text(
        _markdown(payload), encoding="utf-8"
    )
    print(json.dumps({
        "department_count": payload["department_count"],
        "first_term": payload["terms"][0]["academic_term"],
        "last_term": payload["terms"][-1]["academic_term"],
        "term_count": len(payload["terms"]),
        "academic_year_count": len(payload["academic_years"]),
        "deterministic_fingerprint": payload["deterministic_fingerprint"],
    }, indent=2, sort_keys=True))
    return 0


def _jsonl(path):
    return tuple(
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _write_json(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_term_csv(path, payload):
    fields = (
        "academic_unit_id", "department_name", "faculty", "academic_term",
        "term_label", "academic_year", "sch", "sections", "enrollment",
        "distinct_instructors",
    )
    rows = (
        {
            "academic_unit_id": department["academic_unit_id"],
            "department_name": department["department_name"],
            "faculty": department["faculty"],
            **period,
        }
        for department in payload["departments"]
        for period in department["terms"]
    )
    _write_csv(path, fields, rows)


def _write_year_csv(path, payload):
    fields = (
        "academic_unit_id", "department_name", "faculty", "academic_year",
        "sch", "sections", "enrollment", "distinct_instructors",
        "sch_per_faculty",
    )
    rows = (
        {
            "academic_unit_id": department["academic_unit_id"],
            "department_name": department["department_name"],
            "faculty": department["faculty"],
            **period,
        }
        for department in payload["departments"]
        for period in department["academic_years"]
    )
    _write_csv(path, fields, rows)


def _write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _markdown(payload):
    terms = payload["terms"]
    years = payload["academic_years"]
    lines = [
        "# Department SCH Timeline",
        "",
        f"- Departments: {payload['department_count']}",
        f"- Terms: {len(terms)} ({terms[0]['term_label']} through {terms[-1]['term_label']})",
        f"- Academic-year definition: {payload['academic_year_definition']}",
        "",
        "## Institution-wide department summary",
        "",
    ]
    headers = (
        ["Department", "Faculty"]
        + [item["term_label"] for item in terms]
        + [f"AY {year}" for year in years]
        + ["Grand Total"]
        + [f"AY {year} SCH/Faculty" for year in years]
    )
    lines += [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] + ["---:"] * (len(headers) - 1)) + "|",
    ]
    for department in payload["departments"]:
        values = (
            [department["department_name"], str(department["faculty"])]
            + [str(item["sch"]) for item in department["terms"]]
            + [str(item["sch"]) for item in department["academic_years"]]
            + [str(department["grand_total"]["sch"])]
            + [
                "" if item["sch_per_faculty"] is None
                else str(item["sch_per_faculty"])
                for item in department["academic_years"]
            ]
        )
        lines.append("| " + " | ".join(values) + " |")
    for department in payload["departments"]:
        lines += [
            "",
            f"## {department['department_name']}",
            "",
            f"- Current analytical workforce: {department['faculty']}",
            "",
            "| Term | Academic year | SCH | Sections | Enrollment | Distinct instructors |",
            "|---|---|---:|---:|---:|---:|",
        ]
        lines += [
            f"| {item['term_label']} | {item['academic_year']} | {item['sch']} | "
            f"{item['sections']} | {item['enrollment']} | {item['distinct_instructors']} |"
            for item in department["terms"]
        ]
        lines += [
            "",
            "| Academic year | SCH | Sections | Enrollment | Distinct instructors | SCH/Faculty |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        lines += [
            f"| AY {item['academic_year']} | {item['sch']} | {item['sections']} | "
            f"{item['enrollment']} | {item['distinct_instructors']} | "
            f"{item['sch_per_faculty'] if item['sch_per_faculty'] is not None else ''} |"
            for item in department["academic_years"]
        ]
        grand = department["grand_total"]
        lines += [
            "",
            f"Grand Total: SCH {grand['sch']}; sections {grand['sections']}; "
            f"enrollment {grand['enrollment']}; distinct instructors "
            f"{grand['distinct_instructors']}.",
        ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
