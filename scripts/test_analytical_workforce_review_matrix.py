from __future__ import annotations

import json

from scripts.a100_testing_scripts.build_analytical_workforce_review_matrix import (
    build_matrix, write_reports,
)


def _decision(identity, name, reasons, unit=None, recent=0):
    return {
        "decision_id": f"decision:{identity}",
        "faculty_identity_id": identity,
        "display_name": name,
        "decision": "review_required",
        "primary_reason_code": reasons[0],
        "all_reason_codes": reasons,
        "published_academic_units": [],
        "analytical_academic_unit_id": unit,
        "analytical_unit_method": None,
        "teaching_assignment_summary": {
            "recent_assignment_count": recent,
            "total_assignment_count": recent,
            "most_recent_term": "2025_fall" if recent else None,
            "subject_prefixes": ["TEST"] if recent else [],
        },
        "evidence_fitness": [], "limitations": [], "governed_override": None,
    }


def test_review_matrix_separates_membership_and_unit_review(tmp_path):
    root = tmp_path / "run"
    workforce = root / "workforce_1"
    workforce.mkdir(parents=True)
    population = {
        "deterministic_fingerprint": "fixture-fingerprint",
        "starting_directory_identity_count": 10,
        "included_count": 6, "excluded_count": 1,
        "review_required_count": 3, "maximum_plausible_population": 9,
    }
    (workforce / "analytical_workforce_population.json").write_text(json.dumps(population))
    decisions = (
        _decision("faculty:unit", "Unit Review", ["current_directory_instructional_title", "no_safe_analytical_unit"], recent=2),
        _decision("faculty:dean", "Dean Review", ["senior_administrator_with_faculty_rank"]),
        _decision("faculty:both", "Both Review", ["current_directory_instructional_title", "senior_administrator_with_faculty_rank", "multiple_current_unit_candidates"]),
    )
    (workforce / "analytical_workforce_decisions.jsonl").write_text(
        "".join(json.dumps(item) + "\n" for item in decisions)
    )
    appointments = root / "appointments"
    appointments.mkdir()
    (appointments / "faculty_appointment_observations.jsonl").write_text(
        json.dumps({
            "faculty_identity_id": "faculty:dean",
            "published_titles": ["Professor and Dean"],
            "appointment_category_published": None,
            "published_academic_unit_label": "Department of Examples",
        }) + "\n"
    )
    (appointments / "administrative_appointment_observations.jsonl").write_text(
        json.dumps({
            "faculty_identity_id": "faculty:dean",
            "published_administrative_title": "Professor and Dean",
        }) + "\n"
    )
    payload = build_matrix(root)
    assert payload["review_scope_counts"] == {
        "both": 1, "department_assignment_only": 1,
        "workforce_membership": 1,
    }
    unit = next(item for item in payload["review_matrix"] if item["display_name"] == "Unit Review")
    assert unit["actual_review_triggers"] == ["no_safe_analytical_unit"]
    assert payload["diagnosis"]["review_primary_reason_mismatch_count"] == 2
    dean = next(item for item in payload["review_matrix"] if item["display_name"] == "Dean Review")
    assert dean["published_positions"] == ["Professor and Dean"]
    assert dean["administrative_positions"] == ["Professor and Dean"]
    assert dean["departments"] == ["Department of Examples"]
    scenarios = {item["name"]: item["population_count"] for item in payload["policy_interpretations"]}
    assert scenarios["strict_included_only"] == 6
    assert scenarios["include_department_assignment_only"] == 7
    assert scenarios["include_all_review_required"] == 9


def test_review_reports_are_byte_identical(tmp_path):
    root = tmp_path / "run"
    workforce = root / "workforce_1"
    workforce.mkdir(parents=True)
    (workforce / "analytical_workforce_population.json").write_text(json.dumps({
        "deterministic_fingerprint": "same", "starting_directory_identity_count": 1,
        "included_count": 0, "excluded_count": 0, "review_required_count": 1,
        "maximum_plausible_population": 1,
    }))
    (workforce / "analytical_workforce_decisions.jsonl").write_text(json.dumps(
        _decision("faculty:one", "One Review", ["visiting_policy_uncertain"])
    ) + "\n")
    payload = build_matrix(root)
    first, second = tmp_path / "first", tmp_path / "second"
    write_reports(payload, first)
    write_reports(payload, second)
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()
