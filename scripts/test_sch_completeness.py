from __future__ import annotations

from app.department_profiles import _repair_sch_rows, _unique_sections
from scripts.audit_sch_completeness import (
    _audit_departments, _pattern_analysis, _pipeline_traces, _reason_breakdown,
)


def _row(observation, section, credits=3.0, enrollment=10, method=None, course="TEST 101"):
    return {
        "observation_id": observation, "section_key": section,
        "term": "2025_fall", "subject": "TEST", "course_code": course,
        "course_number": "101", "section": "01", "course_title": "Test Course",
        "instructor_identity_id": "faculty:one", "instructor_raw": "One Person",
        "home_unit_id": "academic_unit:test", "owned_unit_id": "academic_unit:test",
        "credits": credits, "enrollment": enrollment, "credits_raw": None,
        "credit_resolution_method": method, "sch_repairs": (),
    }


def _profile():
    return {
        "academic_unit_id": "academic_unit:test", "department_name": "Test Department",
        "faculty_identity_ids": ["faculty:one"],
    }


def test_course_term_credit_consensus_repairs_missing_credit_deterministically():
    rows = (_row("one", "section-one", credits=3.0), _row("two", "section-two", credits=None))
    first, first_repairs = _repair_sch_rows(rows)
    second, second_repairs = _repair_sch_rows(tuple(reversed(rows)))
    assert next(item for item in first if item["observation_id"] == "two")["credits"] == 3.0
    assert first_repairs == second_repairs
    assert len(first_repairs) == 1


def test_variable_credit_is_not_repaired():
    rows = (
        _row("one", "section-one", credits=3.0),
        _row("two", "section-two", credits=None, method="legitimate_variable_credit"),
    )
    repaired, repairs = _repair_sch_rows(rows)
    assert next(item for item in repaired if item["observation_id"] == "two")["credits"] is None
    assert repairs == ()


def test_duplicate_section_supplies_missing_explicit_value_without_double_counting():
    rows = (
        _row("one", "same", enrollment=None),
        _row("two", "same", enrollment=8),
    )
    section = _unique_sections(rows)[0]
    assert section["enrollment"] == 8
    assert section["duplicate_observation_count"] == 2
    assert "duplicate_section_enrollment" in section["sch_repairs"]


def test_missing_enrollment_and_credit_are_listed_with_partial_sch():
    rows = (
        _row("ready", "ready", credits=3, enrollment=10),
        _row("no-credit", "no-credit", credits=None, enrollment=5, method="legitimate_variable_credit"),
        _row("no-enrollment", "no-enrollment", credits=3, enrollment=None),
    )
    departments, missing = _audit_departments((_profile(),), rows, rows)
    department = departments[0]
    assert department["status"] == "INCOMPLETE"
    assert department["known_sch"] == 30.0
    assert department["missing_section_count"] == 2
    assert {reason for item in missing for reason in item["reason_codes"]} == {"variable_credit", "missing_enrollment"}
    assert department["potential_sch_affected_percent"] is None
    assert all(item["reason_codes"] for item in missing)
    assert all(item["computed_sch"] is None for item in missing)


def test_forensic_grouping_and_pipeline_traces_are_deterministic():
    rows = (
        _row("missing-credit", "missing-credit", credits=None, enrollment=7),
        _row("missing-enrollment", "missing-enrollment", credits=3, enrollment=None),
    )
    _, first = _audit_departments((_profile(),), rows, rows)
    _, second = _audit_departments((_profile(),), tuple(reversed(rows)), tuple(reversed(rows)))
    assert first == second
    breakdown = _reason_breakdown(first)
    assert {item["reason_code"] for item in breakdown} == {"missing_credit_hours", "missing_enrollment"}
    assert _pipeline_traces(first) == _pipeline_traces(second)
    assert _pattern_analysis(first) == _pattern_analysis(second)
