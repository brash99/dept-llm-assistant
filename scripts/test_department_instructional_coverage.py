from __future__ import annotations

from types import SimpleNamespace

from app.institutional_units import AcademicUnitRegistry
from scripts.audit_department_instructional_coverage import _department_matrix, _prefix_matrix


def _row(subject, owned=None, home=None, identity="faculty:one", observation="one", enrollment=10, credits=3):
    return {
        "subject": subject, "owned_unit_id": owned, "home_unit_id": home,
        "instructor_identity_id": identity, "instructor_raw": "One Person",
        "observation_id": observation, "section_key": observation,
        "term": "2025_fall", "course_code": f"{subject} 101",
        "enrollment": enrollment, "credits": credits,
    }


class Mapper:
    def __init__(self, values):
        self.values = values

    def map_subject(self, subject, term=None):
        return self.values[subject]


def _mapping(status="mapped", owner=None, analytical=None, owner_name=None):
    return SimpleNamespace(
        status=status, owning_academic_unit_id=owner,
        owning_academic_unit_name=owner_name,
        analytical_academic_unit_id=analytical,
    )


def test_prefix_diagnostic_distinguishes_mapped_missing_and_non_department():
    units = AcademicUnitRegistry.load()
    profiles = {
        "academic_unit:sec": {"department_profile_id": "profile:sec"},
        "academic_unit:department_music_theatre_dance": {"department_profile_id": "profile:music"},
    }
    mapper = Mapper({
        "PHYS": _mapping(owner="academic_unit:sec", analytical="academic_unit:sec", owner_name="School of Engineering and Computing"),
        "NONE": _mapping(status="unmapped"),
        "HONR": _mapping(owner="academic_unit:honors_program", analytical="academic_unit:honors_program", owner_name="Honors Program"),
        "OLDM": _mapping(owner="academic_unit:department_music_historical", analytical="academic_unit:department_music_theatre_dance", owner_name="Department of Music"),
    })
    rows = (
        _row("PHYS", "academic_unit:sec"),
        _row("NONE", observation="two"),
        _row("HONR", "academic_unit:honors_program", observation="three"),
        _row("OLDM", "academic_unit:department_music_theatre_dance", observation="four"),
    )
    result = {item["subject_prefix"]: item for item in _prefix_matrix(rows, mapper, units, profiles)}
    assert result["PHYS"]["mapping_result"] == "mapped"
    assert result["NONE"]["mapping_result"] == "missing_owner"
    assert result["HONR"]["mapping_result"] == "non_department_owner"
    assert result["OLDM"]["mapping_result"] == "mapped_through_governed_successor"


def test_department_diagnostic_keeps_home_and_owned_activity_independent():
    profiles = ({
        "academic_unit_id": "academic_unit:sec", "department_name": "SEC",
        "faculty_identity_ids": ["faculty:one"], "teaching_assignment_count": 2,
        "section_count": 2,
    },)
    rows = (
        _row("NONE", home="academic_unit:sec"),
        _row("PHYS", owned="academic_unit:sec", identity=None, observation="two"),
    )
    result = _department_matrix(rows, profiles, {"faculty:one": "academic_unit:sec"})[0]
    assert result["home_faculty_teaching_assignment_count"] == 1
    assert result["owned_subject_teaching_assignment_count"] == 1
    assert result["unmapped_home_faculty_assignment_count"] == 1
