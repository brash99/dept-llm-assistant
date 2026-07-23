from app.institutional_units import AcademicUnitRegistry
from app.reasoning import AcademicUnitMappingService, ScheduleAnalysisService
from dataclasses import replace
import yaml

import pytest

from app.subject_ownership import SubjectOwnershipRegistry


def _offering(identifier, subject, instructor):
    return {
        "id": identifier, "object_type": "course_offering_observation",
        "subject": subject, "academic_term": "2024_fall", "instructor_raw": instructor,
        "instructor_type": {"normalized_value": "full_time", "conflicting": False},
    }


def test_default_registry_loads_normalizes_and_fingerprints_deterministically():
    registry = SubjectOwnershipRegistry.load()
    assert registry.records_for_subject(" pcse ")[0].subject_code == "PCSE"
    assert len(registry.fingerprint) == 64
    reordered = SubjectOwnershipRegistry(
        reversed(registry.records), registry.schema_version, registry.registry_id,
        registry.description,
    )
    assert reordered.fingerprint == registry.fingerprint
    assert registry.records_for_subject("UNKNOWN") == ()


def test_effective_term_lookup_selects_only_applicable_records():
    base = SubjectOwnershipRegistry.load().records_for_subject("PCSE")[0]
    old = replace(base, record_id="old", effective_end_term="2023_fall")
    new = replace(base, record_id="new", effective_start_term="2024_spring")
    registry = SubjectOwnershipRegistry((old, new), registry_id="effective-test")
    assert registry.records_for_subject("PCSE", "2023_fall") == (old,)
    assert registry.records_for_subject("PCSE", "2024_spring") == (new,)


def test_loader_rejects_unknown_institutional_unit(tmp_path):
    payload = SubjectOwnershipRegistry.load().to_dict()
    payload["subjects"][0]["owning_academic_unit_id"] = "academic_unit:not_real"
    path = tmp_path / "subjects.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False))
    with pytest.raises(ValueError, match="Unknown owning academic unit"):
        SubjectOwnershipRegistry.load(path)


def test_all_seven_sec_subjects_resolve_without_fictional_departments():
    service = AcademicUnitMappingService()
    for code in ("PHYS", "CPSC", "CYBR", "CPEN", "EENG", "PCSE"):
        result = service.map_subject(code)
        assert result.owning_academic_unit_id == "academic_unit:sec"
        assert result.analytical_academic_unit_id == "academic_unit:sec"
        assert result.status == "intentionally_grouped_department_equivalent"
        assert result.review_status == "governed"
        assert result.formal_unit_type == "dependent_school"
        assert "department_equivalent" in result.operational_roles
    units = AcademicUnitRegistry.load().units
    assert not any(
        unit.formal_unit_type == "department" and not unit.deprecated and
        any(name in unit.published_name.casefold() for name in ("physics", "computer science", "cybersecurity"))
        for unit in units
    )
    assert service.map_subject("IS").status == "unmapped"


def test_pcse_remains_subject_group_and_rolls_up_to_sec_deterministically():
    observations = [_offering("1", "PCSE", "Doe, Jane"), _offering("2", "PCSE", "Jane Doe")]
    service = ScheduleAnalysisService()
    subject = service.analyze_observations(
        "Count PCSE offerings", observations, metric="course_offerings", group_by=("subject",)
    )
    unit = service.analyze_observations(
        "Count PCSE instructors by unit", observations,
        metric="distinct_instructors", group_by=("academic_unit",),
    )
    repeated = service.analyze_observations(
        "Count PCSE instructors by unit", reversed(observations),
        metric="distinct_instructors", group_by=("academic_unit",),
    )
    assert subject.grouped_results[0].subject == "PCSE"
    assert subject.grouped_results[0].value == 2
    assert unit.grouped_results[0].academic_unit_id == "academic_unit:sec"
    assert unit.grouped_results[0].value == 1
    assert unit.deterministic_result_fingerprint == repeated.deterministic_result_fingerprint
    assert unit.evidence_fitness.workforce_mappable_observation_count == 2
    assert unit.evidence_fitness.suitability["staffing_recommendations"] == "insufficient"


def test_governed_operational_music_aliases_preserve_schedule_identity_and_roll_up():
    codes = (
        "BASN", "BASS", "BTMG", "CELL", "CLAR", "COMP", "COND", "EUPH",
        "FLUT", "GUIT", "HARP", "HORN", "IMPR", "OBOE", "ORGN", "PERC",
        "PIAN", "SAXO", "TRMB", "TRPT", "TUBA", "VIOL", "VOIC", "VOLA",
    )
    service = AcademicUnitMappingService()
    for code in codes:
        result = service.map_subject(code)
        assert result.subject_code == code
        assert result.relationship_type == "operational_schedule_alias"
        assert result.canonical_subject_code == "MUSC"
        assert result.catalog_visible_subject_code == "MUSC"
        assert result.academic_unit_id == "academic_unit:department_music_theatre_dance"
        assert result.formal_unit_type == "department"


def test_resolved_schedule_prefixes_use_canonical_units_without_false_equivalence():
    service = AcademicUnitMappingService()
    assert service.map_subject("MECH").academic_unit_id == "academic_unit:sec"
    assert service.map_subject("ENVS").academic_unit_id == "academic_unit:department_biology_chemistry_environmental_science"
    assert service.map_subject("NAVS").academic_unit_id == "academic_unit:department_military_science"
    assert service.map_subject("HBRW").academic_unit_id == "academic_unit:department_modern_classical_languages_literatures"
    assert service.map_subject("ENVS").subject_code == "ENVS"
    assert service.map_subject("EVST").subject_code == "EVST"
    registry = SubjectOwnershipRegistry.load()
    assert (
        registry.records_for_subject("EVST")[0].record_id
        != registry.records_for_subject("ENVS")[0].record_id
    )


def test_current_department_subject_crosswalk_is_governed_not_candidate_driven():
    service = AcademicUnitMappingService()
    expected = {
        "ACCT": "academic_unit:department_accounting_finance",
        "FINC": "academic_unit:department_accounting_finance",
        "MGMT": "academic_unit:department_management_marketing",
        "MKTG": "academic_unit:department_management_marketing",
        "PHIL": "academic_unit:department_philosophy_religion",
        "RSTD": "academic_unit:department_philosophy_religion",
        "MATH": "academic_unit:department_mathematics",
        "ENGL": "academic_unit:department_english",
        "POLS": "academic_unit:department_political_science",
        "PSYC": "academic_unit:department_psychology",
        "PMED": "academic_unit:department_biology_chemistry_environmental_science",
        "EVST": "academic_unit:department_biology_chemistry_environmental_science",
        "DTAN": "academic_unit:department_economics",
        "HEAL": "academic_unit:department_communication_studies",
        "CHLF": "academic_unit:department_psychology",
        "HUMN": "academic_unit:department_modern_classical_languages_literatures",
    }
    for prefix, unit_id in expected.items():
        result = service.map_subject(prefix)
        assert result.review_status == "governed"
        assert result.analytical_academic_unit_id == unit_id
