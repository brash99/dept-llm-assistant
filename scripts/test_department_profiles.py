from __future__ import annotations

import json

import pytest

from app.department_profiles import DepartmentProfileBuilder
from scripts.build_department_profiles import main


def _directory(identifier, name, unit="History", title="Professor"):
    return {
        "id": identifier, "object_type": "faculty_observation", "display_name": name,
        "published_titles": [title], "published_department": unit,
        "snapshot_date": "2026-07-22", "provenance": {"source": "synthetic"},
    }


def _schedule(identifier, name, subject="PHYS", term="2025_fall", enrollment=10, credits=3.0):
    return {
        "id": identifier, "object_type": "course_offering_observation",
        "instructor_raw": name, "academic_term": term, "subject": subject,
        "course_code": f"{subject} 201", "section": "01", "crn": identifier,
        "enrollment": enrollment, "credits": credits, "provenance": {"source": "synthetic"},
    }


def _decision(identity_id, unit_id, name, recent=0, disposition="include"):
    return {
        "faculty_identity_id": identity_id, "display_name": name,
        "workforce_disposition": disposition,
        "analytical_academic_unit_id": unit_id,
        "teaching_assignment_summary": {"recent_assignment_count": recent},
    }


def _population(count=2):
    return {
        "as_of_date": "2026-07-22", "policy_id": "fixture-policy",
        "deterministic_fingerprint": "fixture-workforce",
        "workforce_included_count": count, "workforce_review_required_count": 0,
        "department_assignment_review_required_count": 0,
    }


def test_profiles_reconcile_home_and_cross_unit_instruction():
    objects = (
        _directory("paula", "Paula Professor", unit="Accounting and Finance"),
        _directory("nora", "Nora Noteaching", unit="Accounting and Finance", title="Lecturer"),
        _directory("excluded", "Erin Excluded"),
        _schedule("section-1", "Paula Professor"),
    )
    from app.faculty_identity import FacultyIdentityService
    ids = {item.display_name: item.identity_id for item in FacultyIdentityService().audit(objects).identities}
    decisions = (
        _decision(ids["Paula Professor"], "academic_unit:department_accounting_finance", "Paula Professor", 1),
        _decision(ids["Nora Noteaching"], "academic_unit:department_accounting_finance", "Nora Noteaching"),
        _decision(ids["Erin Excluded"], None, "Erin Excluded", disposition="exclude"),
    )
    result = DepartmentProfileBuilder().build(objects, decisions, _population())
    profiles = {item.academic_unit_id: item for item in result.profiles}
    home_profile = profiles["academic_unit:department_accounting_finance"]
    sec = profiles["academic_unit:sec"]
    assert home_profile.analytical_workforce_count == 2
    assert "academic_unit:luter_school_business" == home_profile.parent_academic_unit_id
    assert home_profile.faculty_without_recent_teaching_count == 1
    assert home_profile.cross_unit_instruction["home_faculty_outside_department"]["teaching_assignment_count"] == 1
    assert sec.analytical_workforce_count == 0
    assert sec.department_owned_instruction["teaching_assignment_count"] == 1
    assert sec.cross_unit_instruction["department_subjects_taught_by_outside_faculty"]["teaching_assignment_count"] == 1
    assert sec.section_count == 1
    assert sec.enrollment_total == 10
    assert sec.student_credit_hours == 30.0
    assert result.summary["department_workforce_total"] == 2
    assert result.summary["analytical_workforce_denominator_ready"] is True
    assert result.summary["authoritative_hr_denominator_ready"] is False
    assert ids["Erin Excluded"] not in {identity_id for item in result.profiles for identity_id in item.faculty_identity_ids}


def test_missing_enrollment_is_marked_not_inferred():
    objects = (_directory("one", "One Professor", unit="School of Engineering and Computing"), _schedule("section", "One Professor", enrollment=None))
    from app.faculty_identity import FacultyIdentityService
    identity = FacultyIdentityService().audit(objects).identities[0]
    decisions = (_decision(identity.identity_id, "academic_unit:sec", identity.display_name, 1),)
    profile = DepartmentProfileBuilder().build(objects, decisions, _population(1)).profiles[0]
    assert profile.enrollment_total is None
    assert profile.student_credit_hours is None
    assert "enrollment_incomplete" in profile.evidence_fitness


def test_partial_sch_and_unlinked_instructor_preserve_owned_teaching():
    objects = (
        _directory("one", "One Professor", unit="School of Engineering and Computing"),
        _schedule("ready", "Unlinked Instructor", enrollment=10, credits=3.0),
        _schedule("missing", "Another Unlinked", term="2026_spring", enrollment=5, credits=None),
    )
    from app.faculty_identity import FacultyIdentityService
    identity = next(item for item in FacultyIdentityService().audit(objects).identities if item.display_name == "One Professor")
    decisions = (_decision(identity.identity_id, "academic_unit:sec", identity.display_name),)
    profile = DepartmentProfileBuilder().build(objects, decisions, _population(1)).profiles[0]
    assert profile.teaching_assignment_count == 2
    assert profile.section_count == 2
    assert profile.sections_with_enrollment == 2
    assert profile.sections_with_explicit_credits == 1
    assert profile.sch_ready_section_count == 1
    assert profile.student_credit_hours == 30.0
    assert profile.sch_complete is False
    assert profile.cross_unit_instruction["department_subjects_taught_by_outside_faculty"]["teaching_assignment_count"] == 2


def test_home_faculty_activity_never_substitutes_for_subject_ownership():
    objects = (
        _directory("one", "One Professor", unit="Accounting and Finance"),
        _schedule("outside", "One Professor", subject="PHYS"),
    )
    from app.faculty_identity import FacultyIdentityService
    identity = FacultyIdentityService().audit(objects).identities[0]
    profiles = {
        item.academic_unit_id: item for item in DepartmentProfileBuilder().build(
            objects,
            (_decision(
                identity.identity_id,
                "academic_unit:department_accounting_finance",
                identity.display_name,
                1,
            ),),
            _population(1),
        ).profiles
    }
    accounting = profiles["academic_unit:department_accounting_finance"]
    assert accounting.teaching_assignment_count == 0
    assert accounting.student_credit_hours is None
    assert accounting.home_faculty_instruction["teaching_assignment_count"] == 1
    assert accounting.cross_unit_instruction[
        "home_faculty_outside_department"
    ]["teaching_assignment_count"] == 1


def test_duplicate_schedule_rows_do_not_double_count_sections():
    objects = (
        _directory("one", "One Professor", unit="School of Engineering and Computing"),
        _schedule("row-one", "One Professor"),
        {**_schedule("row-two", "One Professor"), "crn": "row-one"},
    )
    from app.faculty_identity import FacultyIdentityService
    identity = next(item for item in FacultyIdentityService().audit(objects).identities if item.display_name == "One Professor")
    profile = DepartmentProfileBuilder().build(
        objects, (_decision(identity.identity_id, "academic_unit:sec", identity.display_name, 1),), _population(1)
    ).profiles[0]
    assert profile.teaching_assignment_count == 2
    assert profile.section_count == 1


def test_subject_prefix_normalization_is_deterministic():
    objects = (
        _directory("one", "One Professor", unit="School of Engineering and Computing"),
        {**_schedule("section", "One Professor"), "subject": " phys "},
    )
    from app.faculty_identity import FacultyIdentityService
    identity = next(item for item in FacultyIdentityService().audit(objects).identities if item.display_name == "One Professor")
    profile = DepartmentProfileBuilder().build(
        objects, (_decision(identity.identity_id, "academic_unit:sec", identity.display_name, 1),), _population(1)
    ).profiles[0]
    assert profile.department_owned_instruction["subject_prefixes"] == ["PHYS"]


def test_profiles_require_completed_review_and_governed_department():
    objects = (_directory("one", "One Professor"),)
    from app.faculty_identity import FacultyIdentityService
    identity = FacultyIdentityService().audit(objects).identities[0]
    decisions = (_decision(identity.identity_id, "academic_unit:office_provost", identity.display_name),)
    with pytest.raises(ValueError, match="Non-department"):
        DepartmentProfileBuilder().build(objects, decisions, _population(1))
    population = {**_population(1), "workforce_review_required_count": 1}
    with pytest.raises(ValueError, match="completed"):
        DepartmentProfileBuilder().build(objects, decisions, population)


def test_cli_outputs_are_byte_identical(tmp_path):
    objects = (_directory("one", "One Professor", unit="School of Engineering and Computing"), _schedule("section", "One Professor"))
    from app.faculty_identity import FacultyIdentityService
    identity = FacultyIdentityService().audit(objects).identities[0]
    normalized = tmp_path / "normalized"
    normalized.mkdir()
    for index, value in enumerate(objects):
        (normalized / f"{index}.json").write_text(json.dumps(value), encoding="utf-8")
    workforce = tmp_path / "workforce"
    workforce.mkdir()
    (workforce / "analytical_workforce_population.json").write_text(json.dumps(_population(1)), encoding="utf-8")
    (workforce / "analytical_workforce_decisions.jsonl").write_text(json.dumps(_decision(identity.identity_id, "academic_unit:sec", identity.display_name, 1)) + "\n", encoding="utf-8")
    outputs = (tmp_path / "first", tmp_path / "second")
    for output in outputs:
        assert main(["--normalized-root", str(normalized), "--workforce-output", str(workforce), "--output-dir", str(output)]) == 0
    assert {item.name for item in outputs[0].iterdir()} == {item.name for item in outputs[1].iterdir()}
    for item in outputs[0].iterdir():
        assert item.read_bytes() == (outputs[1] / item.name).read_bytes()
