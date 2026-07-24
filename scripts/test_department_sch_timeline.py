from __future__ import annotations

import json

import pytest

from scripts.build_department_sch_timeline import (
    _write_json,
    _write_term_csv,
    _write_year_csv,
    build_timeline,
)


def _profile(unit="academic_unit:test", faculty=2):
    return {
        "academic_unit_id": unit,
        "department_name": "Test Department",
        "analytical_workforce_count": faculty,
        "faculty_identity_ids": ["faculty:one", "faculty:two"],
    }


def _row(observation, term, enrollment, credits=3, instructor="faculty:one"):
    return {
        "observation_id": observation,
        "section_key": f"{term}|{observation}",
        "term": term,
        "subject": "TEST",
        "course_code": "TEST 101",
        "course_number": "101",
        "section": observation,
        "course_title": "Test",
        "instructor_identity_id": instructor,
        "instructor_raw": instructor,
        "home_unit_id": "academic_unit:test",
        "owned_unit_id": "academic_unit:test",
        "credits": credits,
        "enrollment": enrollment,
        "sch_repairs": (),
    }


def test_terms_academic_years_and_grand_total_reconcile():
    rows = (
        _row("fall", "2022_fall", 10),
        _row("spring", "2023_spring", 20),
        _row("may", "2023_may", 5, instructor="faculty:two"),
        _row("summer", "2023_summer_1", 4, instructor="faculty:two"),
    )
    result = build_timeline((_profile(),), rows)
    department = result["departments"][0]
    assert [item["academic_year"] for item in result["terms"]] == ["2022-23"] * 4
    assert department["academic_years"][0]["sch"] == 117
    assert department["academic_years"][0]["sections"] == 4
    assert department["academic_years"][0]["enrollment"] == 39
    assert department["academic_years"][0]["distinct_instructors"] == 2
    assert department["grand_total"]["sch"] == 117
    assert department["academic_years"][0]["sch_per_faculty"] == 58.5


def test_each_section_contributes_to_exactly_one_term_and_year():
    rows = (
        _row("fall", "2022_fall", 10),
        _row("spring", "2023_spring", 20),
        _row("next-fall", "2023_fall", 30),
    )
    department = build_timeline((_profile(),), rows)["departments"][0]
    assert sum(item["sections"] for item in department["terms"]) == 3
    assert sum(item["sections"] for item in department["academic_years"]) == 3
    assert department["grand_total"]["sections"] == 3


def test_fall_only_scope_excludes_every_non_fall_term():
    rows = (
        _row("fall-22", "2022_fall", 10),
        _row("spring-23", "2023_spring", 20),
        _row("summer-23", "2023_summer_1", 30),
        _row("fall-23", "2023_fall", 40),
    )
    result = build_timeline((_profile(),), rows, fall_only=True)
    department = result["departments"][0]
    assert result["reporting_scope"] == "fall_only"
    assert [item["academic_term"] for item in result["terms"]] == [
        "2022_fall", "2023_fall",
    ]
    assert [item["sch"] for item in department["academic_years"]] == [30, 120]
    assert department["grand_total"]["sch"] == 150
    assert department["grand_total"]["sections"] == 2


def test_timeline_uses_governed_subject_owner_not_faculty_home():
    home_only = {
        **_row("outside", "2022_fall", 10),
        "owned_unit_id": "academic_unit:other",
    }
    result = build_timeline((_profile(),), (home_only,))
    department = result["departments"][0]
    assert department["grand_total"]["sections"] == 0
    assert department["grand_total"]["sch"] == 0


def test_incomplete_sch_is_not_inferred():
    with pytest.raises(ValueError, match="SCH-complete"):
        build_timeline((_profile(),), (_row("missing", "2022_fall", 10, credits=None),))


def test_repeated_outputs_are_byte_identical(tmp_path):
    rows = (
        _row("spring", "2023_spring", 20),
        _row("fall", "2022_fall", 10),
    )
    first = build_timeline((_profile(),), rows)
    second = build_timeline((_profile(),), tuple(reversed(rows)))
    assert first == second
    for number, payload in ((1, first), (2, second)):
        root = tmp_path / str(number)
        root.mkdir()
        _write_json(root / "department_sch_timeline.json", payload)
        _write_term_csv(root / "department_sch_by_term.csv", payload)
        _write_year_csv(root / "department_sch_by_academic_year.csv", payload)
    assert {
        path.name: path.read_bytes() for path in (tmp_path / "1").iterdir()
    } == {
        path.name: path.read_bytes() for path in (tmp_path / "2").iterdir()
    }
    assert json.loads(
        (tmp_path / "1/department_sch_timeline.json").read_text()
    )["deterministic_fingerprint"] == first["deterministic_fingerprint"]
