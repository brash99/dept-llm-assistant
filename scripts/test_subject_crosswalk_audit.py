from dataclasses import replace
from pathlib import Path

import pytest

from app.institutional_units import AcademicUnitRegistry
from app.reasoning import AcademicUnitMappingService, SubjectCrosswalkAuditService
from app.subject_ownership import (
    SubjectOwnershipEvidence, SubjectOwnershipRecord, SubjectOwnershipRegistry,
)


def _record(record_id="test.rule.v1", subject="TEST", unit="academic_unit:department_fine_art_art_history", **changes):
    value = SubjectOwnershipRecord(
        record_id, subject, subject, unit, unit, "owns_instructional_subject",
        "mapped", "governed_registry_lookup", 1.0, "governed",
        (SubjectOwnershipEvidence("config/institutional_units.yaml", "governed_registry", "Synthetic assertion."),),
        "Reviewed synthetic rule.",
    )
    return replace(value, **changes)


def _registry(*records):
    return SubjectOwnershipRegistry(records, registry_id="test")


def _codes(report):
    return {item.code for item in report.findings}


def test_default_registry_is_valid_stable_and_governs_all_sec_subjects():
    first = SubjectCrosswalkAuditService().audit()
    subject_registry = SubjectOwnershipRegistry.load()
    reversed_registry = SubjectOwnershipRegistry(
        reversed(subject_registry.records), subject_registry.schema_version,
        subject_registry.registry_id, subject_registry.description,
    )
    second = SubjectCrosswalkAuditService().audit(reversed_registry)
    assert first.valid
    assert first.registry_fingerprint == second.registry_fingerprint
    assert set(first.governed_subjects) == {"PHYS", "CPSC", "CYBR", "CPEN", "EENG", "PCSE"}
    for code in first.governed_subjects:
        result = AcademicUnitMappingService().map_subject(code)
        assert result.academic_unit_id == "academic_unit:sec"
        assert result.formal_unit_type == "dependent_school"
        assert "department_equivalent" in result.operational_roles


def test_pcse_evidence_is_explicit_institutional_expert_review():
    record = SubjectOwnershipRegistry.load().records_for_subject("pcse")[0]
    assert record.review_status == "governed"
    assert record.evidence[0].source_type == "institutional_expert"
    assert record.evidence[0].reviewer == "Edward Brash"
    assert "department" in record.rationale.lower()


@pytest.mark.parametrize(("changes", "expected"), [
    ({"owning_academic_unit_id": "academic_unit:not_real"}, "unknown_owning_unit"),
    ({"analytical_academic_unit_id": "academic_unit:not_real"}, "unknown_analytical_unit"),
    ({"evidence": ()}, "missing_evidence"),
    ({"rationale": ""}, "missing_rationale"),
    ({"mapping_status": "invented"}, "invalid_mapping_status"),
    ({"relationship_type": "invented"}, "invalid_relationship_type"),
    ({"review_status": "invented"}, "invalid_review_status"),
    ({"confidence": 2.0}, "invalid_confidence"),
])
def test_record_validation_failures(changes, expected):
    report = SubjectCrosswalkAuditService().audit(_registry(_record(**changes)))
    assert expected in _codes(report)


def test_institutional_expert_requires_reviewer():
    evidence = SubjectOwnershipEvidence("institutional_review:test", "institutional_expert", "Assertion")
    report = SubjectCrosswalkAuditService().audit(_registry(_record(evidence=(evidence,))))
    assert "institutional_expert_missing_reviewer" in _codes(report)


def test_duplicates_conflicts_and_effective_periods():
    duplicate = SubjectCrosswalkAuditService().audit(_registry(_record("one"), _record("two")))
    assert {"duplicate_subject_record", "overlapping_effective_ranges"} <= _codes(duplicate)
    conflict = SubjectCrosswalkAuditService().audit(_registry(
        _record("one"), _record("two", analytical_academic_unit_id="academic_unit:department_music_theatre_dance")
    ))
    assert "conflicting_governed_records" in _codes(conflict)
    separated = SubjectCrosswalkAuditService().audit(_registry(
        _record("old", effective_end_term="2023_fall"),
        _record("new", analytical_academic_unit_id="academic_unit:department_music_theatre_dance", effective_start_term="2024_spring"),
    ))
    assert "conflicting_governed_records" not in _codes(separated)


def test_legacy_embedded_subject_mappings_are_rejected(tmp_path):
    path = tmp_path / "units.yaml"
    original = Path("config/institutional_units.yaml").read_text()
    path.write_text(original + "\nsubject_mappings:\n  - legacy: true\n")
    report = SubjectCrosswalkAuditService().audit(
        _registry(_record()), AcademicUnitRegistry.load(), path
    )
    assert "legacy_embedded_subject_mappings" in _codes(report)
