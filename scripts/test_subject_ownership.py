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
    for code in ("PHYS", "CPSC", "CYBR", "IS", "CPEN", "EENG", "PCSE"):
        result = service.map_subject(code)
        assert result.owning_academic_unit_id == "academic_unit:sec"
        assert result.analytical_academic_unit_id == "academic_unit:sec"
        assert result.status == "intentionally_grouped_department_equivalent"
        assert result.review_status == "governed"
        assert result.formal_unit_type == "dependent_school"
        assert "department_equivalent" in result.operational_roles
    units = AcademicUnitRegistry.load().units
    assert not any(
        unit.formal_unit_type == "department" and
        any(name in unit.published_name.casefold() for name in ("physics", "computer science", "cybersecurity"))
        for unit in units
    )


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
