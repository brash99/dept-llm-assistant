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
    reviews = [item for item in decisions if item["decision"] == "review_required"]
    rows = []
    for item in sorted(reviews, key=lambda value: (value["display_name"].casefold(), value["faculty_identity_id"])):
        reasons = tuple(item["all_reason_codes"])
        teaching = item["teaching_assignment_summary"]
        scope = _review_scope(reasons)
        rows.append({
            "faculty_identity_id": item["faculty_identity_id"],
            "display_name": item["display_name"],
            "review_scope": scope,
            "reported_primary_reason": item["primary_reason_code"],
            "actual_review_triggers": list(_review_triggers(reasons)),
            "all_reason_codes": list(reasons),
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
    included = population["included_count"]
    unit_only = scopes["department_assignment_only"]
    visiting = sum("visiting_policy_uncertain" in row["all_reason_codes"] for row in rows)
    senior = sum("senior_administrator_with_faculty_rank" in row["all_reason_codes"] for row in rows)
    title_uncertain = sum("current_directory_without_instructional_title" in row["all_reason_codes"] for row in rows)
    membership_review = sum(row["review_scope"] in {"workforce_membership", "both"} for row in rows)
    scenarios = [
        _scenario("strict_included_only", included, "Includes no review-required identities."),
        _scenario("include_department_assignment_only", included + unit_only, "Treats unit-only review as workforce members while retaining unresolved department assignment."),
        _scenario("include_unit_only_and_visiting", included + len({row["faculty_identity_id"] for row in rows if row["review_scope"] == "department_assignment_only" or "visiting_policy_uncertain" in row["all_reason_codes"]}), "Adds unit-only and visiting cases; senior administrators and unusual titles remain in review."),
        _scenario("include_unit_only_and_senior_administrators", included + len({row["faculty_identity_id"] for row in rows if row["review_scope"] == "department_assignment_only" or "senior_administrator_with_faculty_rank" in row["all_reason_codes"]}), "Adds unit-only and senior-administrator cases."),
        _scenario("include_all_review_required", population["maximum_plausible_population"], "Includes every review-required identity."),
    ]
    primary_mismatch = [
        row for row in rows
        if row["reported_primary_reason"] in INCLUSION_CONTEXT
        and row["actual_review_triggers"]
    ]
    diagnosis = {
        "review_primary_reason_mismatch_count": len(primary_mismatch),
        "current_directory_instructional_title_review_count": sum(
            row["reported_primary_reason"] == "current_directory_instructional_title"
            for row in rows
        ),
        "department_assignment_only_review_count": unit_only,
        "workforce_membership_review_count": scopes["workforce_membership"],
        "both_membership_and_unit_review_count": scopes["both"],
        "unclassified_review_count": scopes["unclassified_review"],
        "rule_correction_candidates": [
            "Use the review-triggering reason rather than prior inclusion context as primary_reason_code.",
            "Represent workforce-membership review separately from department-assignment review.",
            "Consider retaining clearly instructional identities in the workforce population when only their analytical unit is unresolved.",
        ],
        "classification_changes_applied": False,
    }
    return {
        "source_population_fingerprint": population["deterministic_fingerprint"],
        "starting_population": population["starting_directory_identity_count"],
        "included": population["included_count"],
        "excluded": population["excluded_count"],
        "review_required": population["review_required_count"],
        "review_scope_counts": dict(sorted(scopes.items())),
        "review_trigger_counts": dict(sorted(trigger_counts.items())),
        "policy_interpretations": scenarios,
        "diagnosis": diagnosis,
        "review_matrix": rows,
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
        "reported_primary_reason", "actual_review_triggers",
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
        f"- Included: {payload['included']}",
        f"- Excluded: {payload['excluded']}",
        f"- Review required: {payload['review_required']}", "",
        "## Policy interpretations", "", "| Interpretation | Population | Distance from 275 |", "|---|---:|---:|",
    ]
    lines.extend(f"| {item['name']} | {item['population_count']} | {item['distance_from_275']} |" for item in payload["policy_interpretations"])
    lines += ["", "## Review cases", "", "| Person | Scope | Actual trigger | Unit | Recent teaching | Review question |", "|---|---|---|---|---:|---|"]
    for row in payload["review_matrix"]:
        lines.append(f"| {row['display_name']} | {row['review_scope']} | {', '.join(row['actual_review_triggers'])} | {row['analytical_academic_unit_id'] or ''} | {row['recent_teaching_assignments']} | {row['review_question']} |")
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
    compact["review_matrix_path"] = str(output)
    print(json.dumps(compact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
