#!/usr/bin/env python3
"""Build governed-owned versus faculty-delivered departmental SCH comparisons."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.department_profiles import _repair_sch_rows, _schedule_row  # noqa: E402
from app.faculty_delivered_sch import (  # noqa: E402
    DEFAULT_ACADEMIC_YEARS,
    build_faculty_delivered_sch_comparison,
    compare_with_quentin,
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
    parser.add_argument("--academic-year", action="append", dest="academic_years")
    parser.add_argument("--fall-only", action="store_true")
    parser.add_argument(
        "--quentin-table", type=Path,
        help="Optional CSV with exact columns: Department, Quentin SCH.",
    )
    args = parser.parse_args(argv)
    workforce = args.workforce_output.parent if args.workforce_output.is_file() else args.workforce_output
    profiles_root = args.profiles_output.parent if args.profiles_output.is_file() else args.profiles_output
    decisions = _jsonl(workforce / "analytical_workforce_decisions.jsonl")
    profiles = _jsonl(profiles_root / "department_profiles.jsonl")
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
        for item in decisions
        if item["workforce_disposition"] == "include"
    }
    mapper = AcademicUnitMappingService()
    rows, _ = _repair_sch_rows(tuple(
        _schedule_row(item, schedule_identity, home, mapper)
        for item in objects
        if item.get("object_type") == "course_offering_observation"
    ))
    report = build_faculty_delivered_sch_comparison(
        profiles, rows,
        academic_years=args.academic_years or DEFAULT_ACADEMIC_YEARS,
        fall_only=args.fall_only,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    _json(args.output_dir / "department_faculty_delivered_sch_comparison.json", payload)
    _csv(
        args.output_dir / "department_faculty_delivered_sch_comparison.csv",
        [item.to_dict() for item in report.rows],
    )
    _write_jsonl(
        args.output_dir / "faculty_sch_section_attributions.jsonl",
        [item.to_dict() for item in report.section_attributions],
    )
    by_term = _attribution_by_term(report)
    _csv(args.output_dir / "faculty_sch_attribution_by_term.csv", by_term)
    _json(args.output_dir / "faculty_sch_attribution_by_term.json", by_term)
    (args.output_dir / "faculty_sch_attribution_by_term.md").write_text(
        _attribution_by_term_markdown(by_term), encoding="utf-8"
    )
    (args.output_dir / "department_faculty_delivered_sch_comparison.md").write_text(
        _markdown(report), encoding="utf-8"
    )
    quentin_status = "not_supplied"
    if args.quentin_table:
        with args.quentin_table.open(newline="", encoding="utf-8-sig") as handle:
            source = tuple(csv.DictReader(handle))
        if not source or set(source[0]) != {"Department", "Quentin SCH"}:
            raise ValueError("Quentin CSV requires exactly: Department, Quentin SCH")
        comparison = compare_with_quentin(report, source)
        _csv(args.output_dir / "faculty_delivered_sch_vs_quentin.csv", comparison)
        quentin_payload = {
            "scope": "fall_only" if report.fall_only else "all_academic_year_terms",
            "academic_years": list(report.academic_years),
            "rows": comparison,
            "totals": _quentin_totals(comparison),
            "attribution_pathway_counts": dict(report.attribution_pathway_counts),
            "attribution_pathway_sch": dict(report.attribution_pathway_sch),
            "deterministic_fingerprint": report.deterministic_fingerprint,
        }
        _json(args.output_dir / "faculty_delivered_sch_vs_quentin.json", quentin_payload)
        (args.output_dir / "faculty_delivered_sch_vs_quentin.md").write_text(
            _quentin_markdown(quentin_payload), encoding="utf-8"
        )
        quentin_status = "generated"
    else:
        _json(args.output_dir / "faculty_delivered_sch_vs_quentin.json", {
            "status": "not_generated",
            "reason": "No Quentin table was supplied; values are never fabricated.",
            "required_columns": ["Department", "Quentin SCH"],
        })
    print(json.dumps({
        "department_count": len(report.rows),
        "academic_years": list(report.academic_years),
        "fall_only": report.fall_only,
        "quentin_comparison": quentin_status,
        "deterministic_fingerprint": report.deterministic_fingerprint,
    }, indent=2, sort_keys=True))
    return 0


def _jsonl(path):
    return tuple(
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text("".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ), encoding="utf-8")


def _csv(path, rows):
    rows = tuple(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _markdown(report):
    scope = "Fall semesters only" if report.fall_only else "All terms in each academic year"
    lines = [
        "# Department Curriculum-Owned and Workforce-Attributed SCH", "",
        f"- Academic years: {', '.join(report.academic_years)}",
        f"- Scope: {scope}",
        "- Aggregation: mean annual SCH across the selected years",
        "- Canonical governed-prefix ownership is unchanged.", "",
        "| Department | Curriculum-owned SCH | Workforce-attributed SCH | Difference | Instructor-home SCH | Prefix-owner fallback SCH |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {item.department_name} | {item.governed_prefix_owned_sch} | "
        f"{item.workforce_attributed_sch} | {item.difference} | "
        f"{item.instructor_home_sch} | {item.prefix_owner_fallback_sch} |"
        for item in report.rows
    ]
    lines += ["", "## Attribution pathways", "",
              "| Pathway | Sections | Mean fall SCH |", "|---|---:|---:|"]
    lines += [
        f"| {method} | {report.attribution_pathway_counts[method]} | "
        f"{report.attribution_pathway_sch[method]} |"
        for method in sorted(report.attribution_pathway_counts)
    ]
    return "\n".join(lines) + "\n"


def _quentin_totals(rows):
    fields = (
        "Quentin SCH", "Governed-Prefix-Owned SCH",
        "Workforce-Attributed SCH",
    )
    return {field: round(sum(float(row[field]) for row in rows), 6) for field in fields}


def _attribution_by_term(report):
    output = []
    terms = sorted({item.term for item in report.section_attributions})
    for term in terms:
        rows = tuple(item for item in report.section_attributions if item.term == term)
        instructor = tuple(
            item for item in rows if item.attribution_method == "instructor_home"
        )
        fallback = tuple(
            item for item in rows
            if item.attribution_method == "prefix_owner_fallback"
        )
        total_sch = sum(item.sch for item in rows)
        fallback_sch = sum(item.sch for item in fallback)
        output.append({
            "Term": term,
            "Total Sections": len(rows),
            "Instructor-Home Sections": len(instructor),
            "Prefix-Owner-Fallback Sections": len(fallback),
            "Prefix-Owner-Fallback Section Percent": round(
                100 * len(fallback) / len(rows), 6
            ) if rows else 0,
            "Total SCH": round(total_sch, 6),
            "Instructor-Home SCH": round(sum(item.sch for item in instructor), 6),
            "Prefix-Owner-Fallback SCH": round(fallback_sch, 6),
            "Prefix-Owner-Fallback SCH Percent": round(
                100 * fallback_sch / total_sch, 6
            ) if total_sch else 0,
            "No Active Workforce Home Sections": sum(
                item.fallback_reason == "no_active_workforce_home"
                for item in fallback
            ),
            "Multiple Active Workforce Homes Sections": sum(
                item.fallback_reason == "multiple_active_workforce_homes"
                for item in fallback
            ),
        })
    return tuple(output)


def _attribution_by_term_markdown(rows):
    lines = [
        "# Faculty SCH Attribution by Fall Term", "",
        "| Term | Sections | Instructor home | Prefix fallback | Fallback section % | SCH | Instructor-home SCH | Fallback SCH | Fallback SCH % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {row['Term']} | {row['Total Sections']} | "
        f"{row['Instructor-Home Sections']} | "
        f"{row['Prefix-Owner-Fallback Sections']} | "
        f"{row['Prefix-Owner-Fallback Section Percent']} | "
        f"{row['Total SCH']} | {row['Instructor-Home SCH']} | "
        f"{row['Prefix-Owner-Fallback SCH']} | "
        f"{row['Prefix-Owner-Fallback SCH Percent']} |"
        for row in rows
    ]
    return "\n".join(lines) + "\n"


def _quentin_markdown(payload):
    lines = [
        "# Fall-Only Quentin SCH Comparison", "",
        f"- Academic years: {', '.join(payload['academic_years'])}",
        "- Each value is the mean of Fall 2022, Fall 2023, and Fall 2024.",
        "- Curriculum ownership remains governed by course prefix.",
        "- Workforce attribution uses current analytical home, with governed "
        "prefix-owner fallback.", "",
        "| Department | Quentin | Curriculum-owned | Workforce-attributed | Owned − Quentin | Workforce − Quentin |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {row['Department']} | {row['Quentin SCH']} | "
        f"{row['Governed-Prefix-Owned SCH']} | "
        f"{row['Workforce-Attributed SCH']} | "
        f"{row['Difference (Governed - Quentin)']} | "
        f"{row['Difference (Workforce-Attributed - Quentin)']} |"
        for row in payload["rows"]
    ]
    totals = payload["totals"]
    lines += [
        f"| **Total** | **{totals['Quentin SCH']}** | "
        f"**{totals['Governed-Prefix-Owned SCH']}** | "
        f"**{totals['Workforce-Attributed SCH']}** |  |  |",
        "", "## Attribution pathways", "",
        "| Pathway | Sections | Mean fall SCH |", "|---|---:|---:|",
    ]
    lines += [
        f"| {method} | {payload['attribution_pathway_counts'][method]} | "
        f"{payload['attribution_pathway_sch'][method]} |"
        for method in sorted(payload["attribution_pathway_counts"])
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
