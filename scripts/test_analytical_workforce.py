from __future__ import annotations

import copy
import json

from app.analytical_workforce import (
    AnalyticalWorkforceBuilder, AnalyticalWorkforceOverride,
    AnalyticalWorkforcePolicy,
)
from scripts.build_analytical_workforce import main


def _directory(identifier, name, title="Professor", unit="History", email=None, date="2026-07-21"):
    return {
        "id": identifier, "object_type": "faculty_observation",
        "display_name": name, "published_titles": [title] if title else [],
        "published_department": unit, "email": email,
        "snapshot_date": date, "provenance": {"source": "synthetic-directory"},
    }


def _schedule(identifier, name, term="2025_fall", subject="HIST"):
    return {
        "id": identifier, "object_type": "course_offering_observation",
        "instructor_raw": name, "academic_term": term, "subject": subject,
        "course_code": f"{subject} 101", "provenance": {"source": "synthetic-schedule"},
    }


def _policy():
    return AnalyticalWorkforcePolicy.load()


def _by_name(decisions):
    return {item.display_name: item for item in decisions}


def test_current_directory_is_population_and_teaching_alone_is_not_membership():
    objects = (
        _directory("prof", "Paula Professor"),
        _schedule("prof-teach", "Paula Professor"),
        _schedule("only", "Sam Scheduleonly"),
        _directory("old", "Old Directory", date="2025-01-01"),
    )
    decisions, population = AnalyticalWorkforceBuilder(_policy()).build(objects)
    assert population.starting_population_count == 1
    assert [item.display_name for item in decisions] == ["Paula Professor"]
    assert population.workforce_included_count == 1
    assert decisions[0].teaching_assignment_summary["recent_assignment_count"] == 1


def test_instructional_titles_include_without_requiring_recent_teaching():
    objects = (
        _directory("prof", "Priya Professor", "Professor"),
        _directory("lect", "Lena Lecturer", "Senior Lecturer"),
        _directory("inst", "Ivan Instructor", "Instructor"),
        _schedule("old", "Ivan Instructor", "2020_fall"),
    )
    decisions, population = AnalyticalWorkforceBuilder(_policy()).build(objects)
    assert {item.workforce_disposition for item in decisions} == {"include"}
    assert population.workforce_included_count == 3
    ivan = _by_name(decisions)["Ivan Instructor"]
    assert "historical_teaching_only" in ivan.evidence_fitness
    assert "no_recent_teaching_observed" in ivan.limitations


def test_explicit_emeritus_retired_and_adjunct_exclude():
    objects = (
        _directory("emerita", "Emma Emerita", "Professor Emerita"),
        _directory("retired", "Rita Retired", "Retired Professor"),
        _directory("adjunct", "Adam Adjunct", "Adjunct Professor"),
    )
    decisions, population = AnalyticalWorkforceBuilder(_policy()).build(objects)
    assert population.workforce_excluded_count == 3
    reasons = {item.workforce_primary_reason_code for item in decisions}
    assert {"explicit_emerita", "explicit_retired", "explicit_adjunct_only"} == reasons


def test_chairs_and_program_directors_include_but_senior_administrators_review():
    objects = (
        _directory("chair", "Casey Chair", "Professor and Department Chair"),
        _directory("director", "Dana Director", "Professor; Program Director"),
        _directory("dean", "Drew Dean", "Professor and Dean"),
        _directory("provost", "Vera Provost", "Professor and Vice Provost"),
    )
    decisions, _ = AnalyticalWorkforceBuilder(_policy()).build(objects)
    values = _by_name(decisions)
    assert values["Casey Chair"].workforce_disposition == "include"
    assert values["Dana Director"].workforce_disposition == "include"
    assert values["Drew Dean"].workforce_disposition == "review_required"
    assert values["Vera Provost"].workforce_disposition == "review_required"
    assert values["Drew Dean"].department_assignment_disposition == "resolved"


def test_staff_administrative_only_visiting_and_missing_unit_are_conservative():
    objects = (
        _directory("staff", "Sally Worker", "Staff Coordinator"),
        _directory("office", "Oscar Office", "Office Director", "Office of the Provost"),
        _directory("visit", "Vicky Visiting", "Visiting Professor"),
        _directory("unit", "Uma Unitless", "Professor", "Unknown Synthetic Unit"),
    )
    decisions, _ = AnalyticalWorkforceBuilder(_policy()).build(objects)
    values = _by_name(decisions)
    assert values["Sally Worker"].workforce_disposition == "exclude"
    assert values["Sally Worker"].department_assignment_disposition == "not_applicable"
    assert values["Oscar Office"].workforce_disposition == "exclude"
    assert values["Vicky Visiting"].workforce_disposition == "review_required"
    assert values["Uma Unitless"].workforce_disposition == "include"
    assert values["Uma Unitless"].workforce_primary_reason_code == "current_directory_instructional_title"
    assert values["Uma Unitless"].department_assignment_disposition == "review_required"
    assert values["Uma Unitless"].department_assignment_primary_reason_code == "no_safe_analytical_unit"
    assert values["Oscar Office"].analytical_academic_unit_id is None


def test_current_directory_unit_outranks_historical_and_multiple_current_units_review():
    objects = (
        _directory("current", "Maya Multiple", unit="History", email="maya@example.edu"),
        _directory("other", "Maya Multiple", unit="English", email="maya@example.edu"),
        {
            "id": "catalog", "object_type": "catalog_faculty_observation",
            "published_name": "Maya Multiple", "published_title": "Professor",
            "academic_unit": "Psychology", "catalog_year": "2020-21",
            "provenance": {"source": "synthetic-catalog"},
        },
    )
    decisions, _ = AnalyticalWorkforceBuilder(_policy()).build(objects)
    assert len(decisions) == 1
    assert decisions[0].workforce_disposition == "include"
    assert decisions[0].department_assignment_disposition == "review_required"
    assert decisions[0].department_assignment_primary_reason_code == "multiple_current_unit_candidates"
    assert set(decisions[0].analytical_academic_unit_candidates) == {
        "academic_unit:department_english", "academic_unit:department_history"}
    assert decisions[0].analytical_academic_unit_id is None


def test_governed_override_is_visible_and_deterministic():
    objects = (_directory("dean", "Drew Dean", "Professor and Dean"),)
    identity_id = FacultyIdentityFor(objects)
    override = AnalyticalWorkforceOverride(
        faculty_identity_id=identity_id, decision="include",
        analytical_academic_unit_id="academic_unit:department_history",
        reason="reviewed analytical inclusion", source="institutional_review:test",
        source_type="institutional_expert", reviewer="Test Reviewer",
        review_date="2026-07-22",
    )
    first = AnalyticalWorkforceBuilder(_policy(), (override,)).build(objects)
    second = AnalyticalWorkforceBuilder(_policy(), (override,)).build(reversed(objects))
    decision = first[0][0]
    assert decision.workforce_disposition == "include"
    assert decision.department_assignment_disposition == "resolved"
    assert decision.analytical_unit_method == "governed_override"
    assert "governed_override_applied" in decision.evidence_fitness
    assert first[1].deterministic_fingerprint == second[1].deterministic_fingerprint


def FacultyIdentityFor(objects):
    from app.faculty_identity import FacultyIdentityService
    return FacultyIdentityService().audit(objects).identities[0].identity_id


def test_population_reconciles_and_source_objects_are_not_mutated():
    objects = [
        _directory("include", "Ina Include"),
        _directory("exclude", "Erin Exclude", "Professor Emerita"),
        _directory("review", "Rae Review", "Professor and Dean"),
    ]
    before = copy.deepcopy(objects)
    decisions, population = AnalyticalWorkforceBuilder(_policy()).build(objects)
    assert len(decisions) == 3
    assert population.workforce_included_count + population.workforce_excluded_count + population.workforce_review_required_count == 3
    assert population.department_assignment_resolved_count + population.department_assignment_review_required_count + population.department_assignment_not_applicable_count == 3
    assert population.minimum_plausible_workforce_population == population.workforce_included_count
    assert population.maximum_plausible_workforce_population == population.workforce_included_count + population.workforce_review_required_count
    assert population.central_working_population is None
    assert objects == before
    assert len({item.decision_id for item in decisions}) == len(decisions)
    assert "appointment_fte" not in json.dumps([item.to_dict() for item in decisions])


def test_cli_outputs_are_byte_identical(tmp_path):
    root = tmp_path / "normalized"
    root.mkdir()
    values = (_directory("one", "Ina Include"), _schedule("teach", "Ina Include"))
    for index, value in enumerate(values):
        (root / f"{index}.json").write_text(json.dumps(value), encoding="utf-8")
    outputs = (tmp_path / "first", tmp_path / "second")
    for output in outputs:
        assert main(["--normalized-root", str(root), "--output-dir", str(output)]) == 0
    assert {path.name for path in outputs[0].iterdir()} == {path.name for path in outputs[1].iterdir()}
    for path in outputs[0].iterdir():
        assert path.read_bytes() == (outputs[1] / path.name).read_bytes()
    assert (outputs[0] / "analytical_workforce_membership_review_queue.jsonl").is_file()
    assert (outputs[0] / "analytical_workforce_department_review_queue.jsonl").is_file()
