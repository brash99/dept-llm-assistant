#!/usr/bin/env python3
"""Build capstone-enrollment estimates of graduates by major and department."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.estimated_graduates import EstimatedGraduatesBuilder  # noqa: E402
from app.institutional_units import AcademicUnitRegistry  # noqa: E402
from app.metric_readiness_audit import load_normalized_objects  # noqa: E402
from app.undergraduate_major_capstones import (  # noqa: E402
    UndergraduateMajorCapstoneRegistry,
)
from app.undergraduate_majors import UndergraduateMajorRegistry  # noqa: E402


def _write_json(path: Path, metadata, rows) -> None:
    path.write_text(json.dumps(
        {**metadata, "rows": list(rows)}, indent=2, sort_keys=True,
    ) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows, columns) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: json.dumps(value, sort_keys=True)
                if isinstance(value, (list, dict)) else value
                for key, value in row.items()
            })


def _methodology(result) -> str:
    rows = result.major_rows
    latest = result.summary["academic_years"][-1] if result.summary["academic_years"] else None
    latest_rows = [item for item in rows if item["academic_year"] == latest]
    excluded = sorted({
        (item["major"], item["estimation_status"], item["limitations"][0])
        for item in rows
        if item["estimation_status"].startswith("excluded")
    })
    pathways = sorted({
        item["major"] for item in rows
        if item["estimation_method"] in {
            "sum_governed_mutually_exclusive_alternatives",
            "unique_major_specific_required_capstone",
        }
    })
    lines = [
        "# Estimated Graduates by Major — Methodology",
        "",
        "> Independent semantic experiment based only on governed majors, "
        "governed capstones, and normalized schedule enrollment. These are not "
        "official graduation counts.",
        "",
        "## Method",
        "",
        "1. Normalize governed capstone course identifiers to schedule subject "
        "and course number.",
        "2. Deduplicate schedule observations to one section before enrollment "
        "is counted.",
        "3. Assign sections to academic years using Fall as the start; Spring, "
        "Maymester, and Summer belong to that Fall's academic year.",
        "4. For a single unique capstone, sum section enrollment.",
        "5. For a required sequence, count only the terminal course to avoid "
        "counting the same cohort twice.",
        "6. For multiple required capstones, use one major-specific required "
        "capstone when exactly one such course exists; never add the shared "
        "degree capstone.",
        "7. Sum alternative terminal capstones only when the alternatives are "
        "governed and do not also identify another major.",
        "8. Do not estimate when capstone enrollment cannot be allocated to one "
        "major, a pathway is unresolved, enrollment is incomplete, or no "
        "section is observed.",
        "",
        "## Assumptions",
        "",
        "- Enrollment in a required terminal capstone is a proxy for students "
        "approaching completion of that major.",
        "- Governed alternatives are mutually exclusive for counting purposes.",
        "- The terminal course of a governed sequence is the least duplicative "
        "proxy for completion.",
        "- Duplicate instructor observations for one section describe one "
        "enrolled class, not multiple student cohorts.",
        "",
        "## Unsupported assumptions deliberately not made",
        "",
    ]
    lines.extend(
        f"- {item}" for item in result.summary["unsupported_assumptions"]
    )
    lines.extend([
        "",
        "## Evidence Fitness",
        "",
        "- **High:** a unique, explicitly governed capstone or terminal "
        "sequence course with complete observed enrollment.",
        "- **Medium:** a unique major-specific capstone selected from multiple "
        "required capstones, or catalog evidence that identifies a culminating "
        "course without explicitly calling it a capstone.",
        "- **Unavailable:** shared capstone, unresolved pathway, no identifiable "
        "capstone, missing enrollment, or no observed section.",
        "- Even a high-confidence estimate remains a proxy and is not "
        "degree-conferral evidence.",
        "",
        "## Majors excluded by governed method",
        "",
    ])
    lines.extend(
        f"- **{major}** — `{status}`: {reason}"
        for major, status, reason in excluded
    )
    lines.extend([
        "",
        "## Pathway ambiguities and special handling",
        "",
    ])
    lines.extend(f"- {item}" for item in pathways)
    lines.extend([
        "- Music is excluded because its BA and BM pathways have different "
        "final assessments and at least one pathway lacks a uniquely governed "
        "schedule course.",
        "- Shared course examples include BUSN 418, MLAN 490, POLS 490, "
        "IDST 490, SOCL 490/498, and the Mathematics alternatives.",
        "",
        "## Coverage snapshot",
        "",
        f"- Academic years: {', '.join(result.summary['academic_years'])}",
        f"- Current majors: {result.summary['current_major_count']}",
        f"- Methodologically estimable majors: "
        f"{result.summary['estimable_major_count']}",
        f"- Excluded majors: {result.summary['excluded_major_count']}",
        f"- Latest observed academic-year rows ({latest}): {len(latest_rows)}",
        "",
        f"Deterministic fingerprint: `{result.deterministic_fingerprint}`",
        "",
    ])
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--normalized-root", type=Path, default=Path("storage/normalized")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    objects, integrity = load_normalized_objects(args.normalized_root)
    if integrity["invalid_json_count"]:
        raise ValueError("Normalized corpus contains invalid JSON")
    result = EstimatedGraduatesBuilder().build(
        objects,
        UndergraduateMajorRegistry.load(),
        UndergraduateMajorCapstoneRegistry.load(),
        AcademicUnitRegistry.load(),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        **result.summary,
        "deterministic_fingerprint": result.deterministic_fingerprint,
    }
    major_columns = (
        "academic_year", "major_id", "major",
        "owning_academic_unit_id", "owning_academic_unit_name",
        "department_aggregation_eligible", "estimation_status",
        "estimated_graduates", "capstone_section_count",
        "capstone_enrollment_observed", "estimation_course_ids",
        "estimation_method", "confidence", "limitations",
    )
    department_columns = (
        "academic_year", "academic_unit_id", "department",
        "governed_major_count", "estimated_major_count",
        "excluded_or_unobserved_major_count", "estimated_graduates",
        "estimate_complete_for_department", "included_major_ids",
        "excluded_or_unobserved_major_ids",
    )
    _write_csv(
        args.output_dir / "estimated_graduates_by_major.csv",
        result.major_rows, major_columns,
    )
    _write_json(
        args.output_dir / "estimated_graduates_by_major.json",
        metadata, result.major_rows,
    )
    _write_csv(
        args.output_dir / "estimated_graduates_by_department.csv",
        result.department_rows, department_columns,
    )
    _write_json(
        args.output_dir / "estimated_graduates_by_department.json",
        metadata, result.department_rows,
    )
    (args.output_dir / "estimated_graduates_methodology.md").write_text(
        _methodology(result), encoding="utf-8",
    )
    print(json.dumps({
        "academic_years": result.summary["academic_years"],
        "current_major_count": result.summary["current_major_count"],
        "estimable_major_count": result.summary["estimable_major_count"],
        "excluded_major_count": result.summary["excluded_major_count"],
        "fingerprint": result.deterministic_fingerprint,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
