from dataclasses import replace

from app.estimated_graduates import EstimatedGraduatesBuilder
from app.institutional_units import AcademicUnitRegistry
from app.undergraduate_major_capstones import (
    UndergraduateMajorCapstoneRegistry,
)
from app.undergraduate_majors import UndergraduateMajorRegistry


def _section(identifier, term, subject, number, enrollment, instructor="One"):
    return {
        "object_type": "course_offering_observation",
        "id": identifier,
        "academic_term": term,
        "crn": identifier,
        "subject": subject,
        "course_number": number,
        "course_code": f"{subject} {number}",
        "section": "1",
        "enrollment": enrollment,
        "instructor_raw": instructor,
    }


def _build(objects):
    return EstimatedGraduatesBuilder().build(
        objects,
        UndergraduateMajorRegistry.load(),
        UndergraduateMajorCapstoneRegistry.load(),
        AcademicUnitRegistry.load(),
    )


def _row(result, major, year="2022-23"):
    return next(
        item for item in result.major_rows
        if item["major"] == major and item["academic_year"] == year
    )


def test_unique_single_capstone_uses_section_enrollment():
    result = _build((_section("one", "2023_spring", "ENGL", "490", 12),))
    row = _row(result, "English")
    assert row["estimated_graduates"] == 12
    assert row["estimation_method"] == "required_capstone_enrollment"


def test_required_sequence_counts_only_terminal_course():
    result = _build((
        _section("first", "2022_fall", "CPEN", "497", 10),
        _section("second", "2023_spring", "CPEN", "498", 9),
    ))
    row = _row(result, "Computer Engineering")
    assert row["estimated_graduates"] == 9
    assert row["estimation_course_ids"] == ["CPEN 498"]


def test_shared_capstone_is_excluded_instead_of_allocated():
    result = _build((_section("one", "2023_spring", "MLAN", "490", 20),))
    for major in ("French", "German", "Spanish"):
        row = _row(result, major)
        assert row["estimated_graduates"] is None
        assert row["estimation_status"] == "excluded_shared_capstone"


def test_multiple_required_capstones_use_unique_major_course():
    result = _build((
        _section("shared", "2023_spring", "BUSN", "418", 100),
        _section("finance", "2023_spring", "FINC", "428", 15),
    ))
    assert _row(result, "Finance")["estimated_graduates"] == 15
    assert _row(result, "Accounting")["estimated_graduates"] is None


def test_duplicate_instructor_observations_do_not_double_count_section():
    first = _section("same", "2023_spring", "ENGL", "490", 12, "One")
    second = {**first, "id": "other-observation", "instructor_raw": "Two"}
    result = _build((first, second))
    row = _row(result, "English")
    assert row["estimated_graduates"] == 12
    assert row["capstone_section_count"] == 1


def test_missing_enrollment_and_absent_section_are_not_zero():
    result = _build((_section("one", "2023_spring", "ENGL", "490", None),))
    assert _row(result, "English")["estimation_status"] == "incomplete_enrollment"
    assert _row(result, "History")["estimation_status"] == "not_observed"
    assert _row(result, "History")["estimated_graduates"] is None


def test_department_total_is_partial_when_a_major_is_excluded():
    result = _build((_section("one", "2023_spring", "ENGL", "490", 12),))
    english = next(
        item for item in result.department_rows
        if item["department"] == "Department of English"
        and item["academic_year"] == "2022-23"
    )
    assert english["estimated_graduates"] == 12
    assert english["estimate_complete_for_department"]


def test_repeated_builds_are_identical():
    objects = (_section("one", "2023_spring", "ENGL", "490", 12),)
    first = _build(objects)
    second = _build(objects)
    assert first.major_rows == second.major_rows
    assert first.department_rows == second.department_rows
    assert first.deterministic_fingerprint == second.deterministic_fingerprint
