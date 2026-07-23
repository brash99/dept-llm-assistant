#!/usr/bin/env python3
"""Explain analytical-workforce review cases without changing decisions."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path


UNIT_REASONS = {"no_safe_analytical_unit", "multiple_current_unit_candidates"}
MEMBERSHIP_REASONS = {
    "senior_administrator_with_faculty_rank",
    "dean_with_possible_instructional_role",
    "current_directory_without_instructional_title",
    "conflicting_status_evidence",
    "insufficient_current_evidence",
    "visiting_policy_uncertain",
    "unusual_title",
    "externally_governed_instructional_role",
}
INCLUSION_CONTEXT = {
    "current_directory_instructional_title",
    "current_directory_and_recent_teaching",
    "governed_instructional_faculty_category",
}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path):
    return tuple(
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _review_scope(reasons):
    values = set(reasons)
    membership = bool(values.intersection(MEMBERSHIP_REASONS))
    unit = bool(values.intersection(UNIT_REASONS))
    if membership and unit:
        return "both"
    if membership:
        return "workforce_membership"
    if unit:
        return "department_assignment_only"
    return "unclassified_review"


def _review_triggers(reasons):
    values = [reason for reason in reasons if reason not in INCLUSION_CONTEXT]
    return values or list(reasons)


def build_matrix(run_root: Path) -> dict:
    population = _json(run_root / "workforce_1/analytical_workforce_population.json")
    decisions = _jsonl(run_root / "workforce_1/analytical_workforce_decisions.jsonl")
    appointment_context = _appointment_context(run_root)
    reviews = [item for item in decisions if (
        item["workforce_disposition"] == "review_required"
        or item["department_assignment_disposition"] == "review_required"
    )]
    rows = []
    for item in sorted(reviews, key=lambda value: (value["display_name"].casefold(), value["faculty_identity_id"])):
        workforce_reasons = tuple(item["workforce_reason_codes"])
        department_reasons = tuple(item["department_assignment_reason_codes"])
        reasons = workforce_reasons + department_reasons
        teaching = item["teaching_assignment_summary"]
        membership_review = item["workforce_disposition"] == "review_required"
        unit_review = item["department_assignment_disposition"] == "review_required"
        scope = "both" if membership_review and unit_review else (
            "workforce_membership" if membership_review else "department_assignment_only"
        )
        context = appointment_context.get(item["faculty_identity_id"], {})
        departments = sorted({
            *item["published_academic_units"],
            *context.get("departments", ()),
        })
        rows.append({
            "faculty_identity_id": item["faculty_identity_id"],
            "display_name": item["display_name"],
            "review_scope": scope,
            "published_positions": context.get("faculty_positions", []),
            "administrative_positions": context.get("administrative_positions", []),
            "departments": departments,
            "workforce_disposition": item["workforce_disposition"],
            "workforce_primary_reason": item["workforce_primary_reason_code"],
            "workforce_reason_codes": list(workforce_reasons),
            "department_assignment_disposition": item["department_assignment_disposition"],
            "department_assignment_primary_reason": item["department_assignment_primary_reason_code"],
            "department_assignment_reason_codes": list(department_reasons),
            "actual_review_triggers": list(
                (workforce_reasons if membership_review else ())
                + (department_reasons if unit_review else ())
            ),
            "published_academic_units": item["published_academic_units"],
            "analytical_academic_unit_id": item["analytical_academic_unit_id"],
            "analytical_unit_method": item["analytical_unit_method"],
            "recent_teaching_assignments": teaching["recent_assignment_count"],
            "total_teaching_assignments": teaching["total_assignment_count"],
            "most_recent_term": teaching["most_recent_term"],
            "subject_prefixes": teaching["subject_prefixes"],
            "evidence_fitness": item["evidence_fitness"],
            "limitations": item["limitations"],
            "governed_override": item["governed_override"],
            "review_question": _review_question(scope, reasons),
        })
    scopes = Counter(row["review_scope"] for row in rows)
    trigger_counts = Counter(
        trigger for row in rows for trigger in row["actual_review_triggers"]
    )
    included = population["workforce_included_count"]
    unit_only = scopes["department_assignment_only"]
    visiting = sum("visiting_policy_uncertain" in row["workforce_reason_codes"] for row in rows)
    senior = sum("senior_administrator_with_faculty_rank" in row["workforce_reason_codes"] for row in rows)
    membership_review = sum(row["review_scope"] in {"workforce_membership", "both"} for row in rows)
    scenarios = [
        _scenario("strict_workforce_included_only", included, "Includes all workforce-included identities; department review does not remove membership."),
        _scenario("include_visiting_reviews", included + visiting, "Adds visiting workforce-review cases."),
        _scenario("include_senior_administrator_reviews", included + senior, "Adds senior-administrator workforce-review cases."),
        _scenario("include_all_workforce_reviews", population["maximum_plausible_workforce_population"], "Adds every workforce-membership review case."),
    ]
    primary_mismatch = [row for row in rows if (
        row["workforce_disposition"] == "review_required"
        and row["workforce_primary_reason"] in INCLUSION_CONTEXT
    ) or (
        row["department_assignment_disposition"] == "review_required"
        and row["department_assignment_primary_reason"] not in UNIT_REASONS
    )]
    diagnosis = {
        "review_primary_reason_mismatch_count": len(primary_mismatch),
        "current_directory_instructional_title_review_count": sum(
            row["workforce_disposition"] == "include"
            and row["workforce_primary_reason"] == "current_directory_instructional_title"
            and row["department_assignment_disposition"] == "review_required"
            for row in rows),
        "department_assignment_only_review_count": unit_only,
        "workforce_membership_review_count": scopes["workforce_membership"],
        "both_membership_and_unit_review_count": scopes["both"],
        "unclassified_review_count": scopes["unclassified_review"],
        "rule_correction_candidates": [],
        "classification_changes_applied": True,
    }
    return {
        "source_population_fingerprint": population["deterministic_fingerprint"],
        "starting_population": population["starting_population_count"],
        "workforce_included": population["workforce_included_count"],
        "workforce_excluded": population["workforce_excluded_count"],
        "workforce_review_required": population["workforce_review_required_count"],
        "department_assignment_review_required": population["department_assignment_review_required_count"],
        "review_scope_counts": dict(sorted(scopes.items())),
        "review_trigger_counts": dict(sorted(trigger_counts.items())),
        "policy_interpretations": scenarios,
        "diagnosis": diagnosis,
        "review_matrix": rows,
    }


def _appointment_context(run_root):
    appointment_root = run_root / "appointments"
    faculty_path = appointment_root / "faculty_appointment_observations.jsonl"
    admin_path = appointment_root / "administrative_appointment_observations.jsonl"
    if not faculty_path.is_file() or not admin_path.is_file():
        return {}
    values = {}
    for item in _jsonl(faculty_path):
        identity_id = item.get("faculty_identity_id")
        if not identity_id:
            continue
        target = values.setdefault(identity_id, {
            "faculty_positions": set(), "administrative_positions": set(),
            "departments": set(),
        })
        target["faculty_positions"].update(item.get("published_titles") or ())
        if item.get("appointment_category_published"):
            target["faculty_positions"].add(item["appointment_category_published"])
        if item.get("published_academic_unit_label"):
            target["departments"].add(item["published_academic_unit_label"])
    for item in _jsonl(admin_path):
        identity_id = item.get("faculty_identity_id")
        if not identity_id:
            continue
        target = values.setdefault(identity_id, {
            "faculty_positions": set(), "administrative_positions": set(),
            "departments": set(),
        })
        if item.get("published_administrative_title"):
            target["administrative_positions"].add(item["published_administrative_title"])
    return {
        identity_id: {key: sorted(items) for key, items in context.items()}
        for identity_id, context in values.items()
    }


def _scenario(name, count, rule):
    return {"name": name, "population_count": count, "distance_from_275": count - 275, "rule": rule}


def _review_question(scope, reasons):
    if scope == "department_assignment_only":
        return "Which governed academic unit should receive this otherwise instructional identity?"
    if "senior_administrator_with_faculty_rank" in reasons:
        return "Should this senior administrator remain in the instructional-faculty scenario population?"
    if "visiting_policy_uncertain" in reasons:
        return "Should visiting instructional faculty be included in Quentin's working population?"
    if "current_directory_without_instructional_title" in reasons:
        return "Does the current published role represent instructional faculty membership?"
    return "Should this identity be included, and is its analytical unit safely established?"


def write_reports(payload, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "analytical_workforce_review_matrix.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    columns = (
        "display_name", "faculty_identity_id", "review_scope",
        "published_positions", "administrative_positions", "departments",
        "workforce_disposition", "workforce_primary_reason",
        "department_assignment_disposition", "department_assignment_primary_reason",
        "actual_review_triggers",
        "published_academic_units", "analytical_academic_unit_id",
        "recent_teaching_assignments", "most_recent_term", "limitations",
        "review_question",
    )
    with (output_dir / "analytical_workforce_review_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in payload["review_matrix"]:
            writer.writerow({key: json.dumps(row[key]) if isinstance(row[key], list) else row[key] for key in columns})
    (output_dir / "analytical_workforce_review_matrix.md").write_text(
        _markdown(payload), encoding="utf-8"
    )


def _markdown(payload):
    lines = [
        "# Analytical Workforce Review Matrix", "",
        "> Read-only review aid. No classifications or source observations were changed.", "",
        f"- Starting population: {payload['starting_population']}",
        f"- Workforce included: {payload['workforce_included']}",
        f"- Workforce excluded: {payload['workforce_excluded']}",
        f"- Workforce review required: {payload['workforce_review_required']}",
        f"- Department-assignment review required: {payload['department_assignment_review_required']}", "",
        "## Policy interpretations", "", "| Interpretation | Population | Distance from 275 |", "|---|---:|---:|",
    ]
    lines.extend(f"| {item['name']} | {item['population_count']} | {item['distance_from_275']} |" for item in payload["policy_interpretations"])
    for heading, scope in (("Workforce membership review", {"workforce_membership", "both"}), ("Department assignment review", {"department_assignment_only", "both"})):
        lines += ["", f"## {heading}", "", "| Person | Positions | Departments | Scope | Actual trigger | Recent teaching |", "|---|---|---|---|---|---:|"]
        for row in payload["review_matrix"]:
            if row["review_scope"] not in scope:
                continue
            positions = sorted({*row['published_positions'], *row['administrative_positions']})
            lines.append(f"| {row['display_name']} | {', '.join(positions)} | {', '.join(row['departments'])} | {row['review_scope']} | {', '.join(row['actual_review_triggers'])} | {row['recent_teaching_assignments']} |")
    lines += ["", "## Rule diagnosis", ""]
    lines.extend(f"- {key}: {value}" for key, value in payload["diagnosis"].items())
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    payload = build_matrix(args.run_root)
    output = args.output_dir or args.run_root / "review_matrix"
    write_reports(payload, output)
    compact = {key: value for key, value in payload.items() if key != "review_matrix"}
    compact["review_people"] = [{
        "name": row["display_name"],
        "positions": sorted({
            *row["published_positions"], *row["administrative_positions"],
        }),
        "departments": row["departments"],
        "review_scope": row["review_scope"],
        "review_triggers": row["actual_review_triggers"],
    } for row in payload["review_matrix"]]
    compact["review_matrix_path"] = str(output)
    print(json.dumps(compact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
