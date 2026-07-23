#!/usr/bin/env python3
"""Build deterministic department profiles from a finalized workforce artifact."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.department_profiles import DepartmentProfileBuilder  # noqa: E402
from app.metric_readiness_audit import load_normalized_objects  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-root", type=Path, default=Path("storage/normalized"))
    parser.add_argument("--workforce-output", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    workforce = _workforce_root(args.workforce_output)
    population = _json(workforce / "analytical_workforce_population.json")
    decisions = _jsonl(workforce / "analytical_workforce_decisions.jsonl")
    objects, integrity = load_normalized_objects(args.normalized_root)
    if integrity["invalid_json_count"]:
        raise ValueError("Normalized corpus contains invalid JSON")
    result = DepartmentProfileBuilder().build(objects, decisions, population)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(args.output_dir / "department_profiles.jsonl", [item.to_dict() for item in result.profiles])
    summary = {**result.summary, "deterministic_fingerprint": result.deterministic_fingerprint}
    _write_json(args.output_dir / "department_profile_summary.json", summary)
    _write_json(args.output_dir / "department_profile_manifest.json", {
        "deterministic_fingerprint": result.deterministic_fingerprint,
        "profile_fingerprints": {item.academic_unit_id: item.deterministic_fingerprint for item in result.profiles},
    })
    _write_workforce_csv(args.output_dir / "department_workforce.csv", result.profiles)
    _write_activity_csv(args.output_dir / "department_instructional_activity.csv", result.profiles)
    _write_cross_csv(args.output_dir / "department_cross_unit_instruction.csv", result.profiles)
    (args.output_dir / "department_profile_summary.md").write_text(_markdown(result), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _workforce_root(value):
    if value:
        path = Path(value)
        return path.parent if path.is_file() else path
    candidates = sorted(Path("storage/logs").glob("analytical_workforce_*/workforce_1"), reverse=True)
    if not candidates:
        raise ValueError("No analytical workforce output found; pass --workforce-output")
    return candidates[0]


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path):
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path, values):
    path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in values), encoding="utf-8")


def _csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_workforce_csv(path, profiles):
    columns = ("academic_unit_id", "department_name", "faculty_identity_id", "display_name", "published_titles", "normalized_ranks", "administrative_roles", "recent_teaching_observed")
    rows = []
    for profile in profiles:
        for member in profile.faculty_members:
            rows.append({
                "academic_unit_id": profile.academic_unit_id, "department_name": profile.department_name,
                **{key: json.dumps(member[key]) if isinstance(member[key], list) else member[key] for key in columns[2:]},
            })
    _csv(path, columns, rows)


def _write_activity_csv(path, profiles):
    columns = ("academic_unit_id", "department_name", "analytical_workforce_count", "teaching_assignment_count", "section_count", "distinct_instructors_observed", "enrollment_total", "student_credit_hours", "earliest_observed_term", "latest_observed_term")
    _csv(path, columns, ({key: getattr(profile, key) for key in columns} for profile in profiles))


def _write_cross_csv(path, profiles):
    columns = ("academic_unit_id", "department_name", "direction", "teaching_assignment_count", "section_count", "distinct_instructor_count", "subject_prefixes", "enrollment_total", "student_credit_hours")
    rows = []
    for profile in profiles:
        for direction, values in profile.cross_unit_instruction.items():
            rows.append({"academic_unit_id": profile.academic_unit_id, "department_name": profile.department_name, "direction": direction, **{key: json.dumps(value) if isinstance(value, list) else value for key, value in values.items()}})
    _csv(path, columns, rows)


def _markdown(result):
    summary = result.summary
    lines = [
        "# Department Profiles", "", "> Analytical baseline; not an authoritative HR roster.", "",
        f"- Profiles: {summary['department_profile_count']}",
        f"- Included analytical workforce: {summary['analytical_workforce_count']}",
        f"- Reconciled department workforce total: {summary['department_workforce_total']}",
        f"- Analytical workforce denominator ready: {str(summary['analytical_workforce_denominator_ready']).lower()}",
        f"- Authoritative HR denominator ready: {str(summary['authoritative_hr_denominator_ready']).lower()}", "",
    ]
    for profile in result.profiles:
        lines += [
            f"## {profile.department_name}", "",
            f"- Workforce: {profile.analytical_workforce_count}",
            f"- Parent: {profile.parent_academic_unit_name or 'Not governed'}",
            f"- Department-owned sections: {profile.section_count}",
            f"- Teaching assignments: {profile.teaching_assignment_count}",
            f"- Enrollment: {profile.enrollment_total if profile.enrollment_total is not None else 'incomplete'}",
            f"- SCH: {profile.student_credit_hours if profile.student_credit_hours is not None else 'incomplete'}",
            f"- Home-faculty outside assignments: {profile.cross_unit_instruction['home_faculty_outside_department']['teaching_assignment_count']}",
            f"- Outside-faculty assignments in owned subjects: {profile.cross_unit_instruction['department_subjects_taught_by_outside_faculty']['teaching_assignment_count']}", "",
        ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
