from __future__ import annotations

from app.faculty_delivered_sch import (
    build_faculty_delivered_sch_comparison,
    compare_with_quentin,
)
from scripts.build_faculty_delivered_sch import _attribution_by_term


def _profile(unit, name):
    return {"academic_unit_id": unit, "department_name": name}


def _row(
    identifier, owner, home, enrollment, term="2022_fall", llc_area_raw=None,
    subject="TEST",
):
    return {
        "observation_id": identifier,
        "section_key": f"{term}|{identifier}",
        "term": term,
        "owned_unit_id": owner,
        "home_unit_id": home,
        "subject": subject,
        "course_code": f"{subject} 101",
        "llc_area_raw": llc_area_raw,
        "credits": 3,
        "enrollment": enrollment,
        "instructor_raw": "Fixture Instructor",
        "sch_repairs": (),
    }


def test_faculty_delivery_and_governed_ownership_remain_independent():
    rows = (
        _row("english-owned", "department:english", "department:english", 10),
        _row("honors", "program:honors", "department:english", 20),
        _row("psych-owned", "department:psychology", "department:english", 5),
    )
    report = build_faculty_delivered_sch_comparison(
        (
            _profile("department:english", "English"),
            _profile("department:psychology", "Psychology"),
        ),
        rows,
        academic_years=("2022-23",),
    )
    by_name = {item.department_name: item for item in report.rows}
    assert by_name["English"].governed_prefix_owned_sch == 30
    assert by_name["English"].workforce_attributed_sch == 105
    assert by_name["English"].cross_unit_contribution == 75
    assert by_name["English"].workforce_attributed_outside_owned_sch == 75
    assert by_name["Psychology"].governed_prefix_owned_sch == 15
    assert by_name["Psychology"].workforce_attributed_sch == 0
    assert by_name["Psychology"].cross_unit_contribution == -15


def test_three_year_average_and_fall_scope_are_explicit():
    rows = (
        _row("f22", "department:english", "department:english", 10, "2022_fall"),
        _row("s23", "department:english", "department:english", 100, "2023_spring"),
        _row("f23", "department:english", "department:english", 20, "2023_fall"),
        _row("f24", "department:english", "department:english", 30, "2024_fall"),
    )
    report = build_faculty_delivered_sch_comparison(
        (_profile("department:english", "English"),),
        rows,
        fall_only=True,
    )
    row = report.rows[0]
    assert row.governed_prefix_owned_sch == 60
    assert row.workforce_attributed_sch == 60
    assert report.fall_only is True


def test_unlinked_instructor_falls_back_to_governed_prefix_owner():
    report = build_faculty_delivered_sch_comparison(
        (_profile("department:english", "English"),),
        (_row("unlinked", "department:english", None, 10),),
        academic_years=("2022-23",),
    )
    assert report.rows[0].governed_prefix_owned_sch == 30
    assert report.rows[0].workforce_attributed_sch == 30
    assert report.rows[0].prefix_owner_fallback_sch == 30
    assert report.section_attributions[0].attribution_method == (
        "prefix_owner_fallback"
    )
    assert report.section_attributions[0].fallback_reason == (
        "no_active_workforce_home"
    )
    assert report.unassigned_instructor_section_count == 1


def test_quentin_comparison_reports_workforce_attributed_metric():
    report = build_faculty_delivered_sch_comparison(
        (_profile("academic_unit:department_english", "Department of English"),),
        (_row("one", "program:honors", "academic_unit:department_english", 10),),
        academic_years=("2022-23",),
    )
    comparison = compare_with_quentin(
        report, ({"Department": "English", "Quentin SCH": "25"},)
    )
    assert comparison[0]["Workforce-Attributed SCH"] == 30
    assert comparison[0]["Governed-Prefix-Owned SCH"] == 0
    assert comparison[0]["Difference (Governed - Quentin)"] == -25
    assert comparison[0]["Difference (Workforce-Attributed - Quentin)"] == 5
    assert comparison[0]["Absolute Difference Improvement"] == 20
    assert comparison[0]["Percent Difference (Workforce-Attributed)"] == 20


def test_instructor_home_precedes_prefix_owner_fallback():
    report = build_faculty_delivered_sch_comparison(
        (
            _profile("department:english", "English"),
            _profile("department:psychology", "Psychology"),
        ),
        (_row("cross-unit", "department:psychology", "department:english", 10),),
        academic_years=("2022-23",),
    )
    attribution = report.section_attributions[0]
    assert attribution.attribution_method == "instructor_home"
    assert attribution.workforce_attributed_unit_id == "department:english"
    assert attribution.governed_prefix_owner_unit_id == "department:psychology"


def test_multiple_active_homes_fall_back_without_double_counting():
    rows = (
        _row("team-a", "department:english", "department:english", 10),
        {
            **_row("team-b", "department:english", "department:psychology", 10),
            "section_key": "2022_fall|team-a",
        },
    )
    report = build_faculty_delivered_sch_comparison(
        (
            _profile("department:english", "English"),
            _profile("department:psychology", "Psychology"),
        ),
        rows,
        academic_years=("2022-23",),
    )
    attribution = report.section_attributions[0]
    assert attribution.attribution_method == "prefix_owner_fallback"
    assert attribution.fallback_reason == "multiple_active_workforce_homes"
    assert attribution.sch == 30
    assert report.multi_home_section_count == 1


def test_quentin_codes_resolve_without_changing_unit_ontology():
    report = build_faculty_delivered_sch_comparison(
        (_profile("academic_unit:department_english", "Department of English"),),
        (_row("one", "academic_unit:department_english", "academic_unit:department_english", 10),),
        academic_years=("2022-23",),
    )
    comparison = compare_with_quentin(
        report, ({"Department": "ENGL", "Quentin SCH": "30"},)
    )
    assert comparison[0]["Department"] == "Department of English"
    assert comparison[0]["Quentin Department Code"] == "ENGL"


def test_repeated_execution_is_deterministic():
    profiles = (_profile("department:english", "English"),)
    rows = (
        _row("one", "department:english", "department:english", 10),
        _row("two", "program:honors", "department:english", 20),
    )
    first = build_faculty_delivered_sch_comparison(
        profiles, rows, academic_years=("2022-23",)
    )
    second = build_faculty_delivered_sch_comparison(
        reversed(profiles), reversed(rows), academic_years=("2022-23",)
    )
    assert first.to_dict() == second.to_dict()


def test_attribution_strategy_is_reported_for_each_term():
    report = build_faculty_delivered_sch_comparison(
        (_profile("department:english", "English"),),
        (
            _row("home", "department:english", "department:english", 10),
            _row("fallback", "department:english", None, 20),
        ),
        academic_years=("2022-23",),
        fall_only=True,
    )
    rows = _attribution_by_term(report)
    assert rows == ({
        "Term": "2022_fall",
        "Total Sections": 2,
        "Instructor-Home Sections": 1,
        "Prefix-Owner-Fallback Sections": 1,
        "Prefix-Owner-Fallback Section Percent": 50.0,
        "Total SCH": 90.0,
        "Instructor-Home SCH": 30.0,
        "Prefix-Owner-Fallback SCH": 60.0,
        "Prefix-Owner-Fallback SCH Percent": 66.666667,
        "No Active Workforce Home Sections": 1,
        "Multiple Active Workforce Homes Sections": 0,
    },)


def test_llc_scope_requires_only_a_nonblank_published_designation():
    report = build_faculty_delivered_sch_comparison(
        (_profile("department:english", "English"),),
        (
            _row(
                "llc", "department:english", "department:english", 10,
                llc_area_raw="AIWT, GE, LETR",
            ),
            _row(
                "blank", "department:english", "department:english", 20,
                llc_area_raw="",
            ),
            _row(
                "none", "department:english", "department:english", 30,
                llc_area_raw=None,
            ),
        ),
        academic_years=("2022-23",),
        fall_only=True,
        llc_only=True,
    )
    assert report.llc_only is True
    assert report.rows[0].governed_prefix_owned_sch == 30
    assert report.rows[0].workforce_attributed_sch == 30
    assert len(report.section_attributions) == 1
    assert report.section_attributions[0].llc_area_raw == "AIWT, GE, LETR"


def test_honors_and_idst_are_an_explicit_combined_quentin_bucket():
    report = build_faculty_delivered_sch_comparison(
        (_profile("department:english", "English"),),
        (
            _row(
                "honors-home", "program:honors", "department:english", 10,
                llc_area_raw="HON", subject="HONR",
            ),
            _row(
                "idst-fallback", "unit:provost", None, 20,
                llc_area_raw="AIII", subject="IDST",
            ),
        ),
        academic_years=("2022-23",),
        fall_only=True,
        llc_only=True,
    )
    comparison = compare_with_quentin(
        report, ({"Department": "HONOR & IDST", "Quentin SCH": "75"},)
    )
    assert comparison[0]["Department"] == "Honors and IDST"
    assert comparison[0]["Governed-Prefix-Owned SCH"] == 90
    assert comparison[0]["Workforce-Attributed SCH"] == 60
    assert comparison[0]["Difference (Governed - Quentin)"] == 15
    assert comparison[0]["Difference (Workforce-Attributed - Quentin)"] == -15
