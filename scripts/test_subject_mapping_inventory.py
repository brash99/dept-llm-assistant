from __future__ import annotations

import csv
import json

from app.institutional_units import AcademicUnitRegistry
from app.subject_ownership import SubjectOwnershipEvidence, SubjectOwnershipRecord, SubjectOwnershipRegistry
from app.reasoning import AcademicUnitMappingService
from app.reasoning.subject_mapping_inventory import (
    ScheduleSubjectMappingInventoryService,
    compare_subject_mapping_reports,
)
from scripts.audit_schedule_subject_mappings import _selected_rows, _write_outputs


def _rule(rule_id, subject, status, unit_id=None, review="governed"):
    target = unit_id or "academic_unit:faculty_arts_humanities"
    return SubjectOwnershipRecord(
        rule_id, subject, subject, target, target, "owns_instructional_subject",
        status, "governed_registry_lookup", 1.0, review,
        (SubjectOwnershipEvidence("config/institutional_units.yaml", "governed_registry", "Synthetic assertion."),),
        "Reviewed synthetic mapping.",
    )


def _service(*rules):
    base = AcademicUnitRegistry.load()
    registry = SubjectOwnershipRegistry(rules, registry_id="inventory-test")
    return ScheduleSubjectMappingInventoryService(AcademicUnitMappingService(base, registry))


def _offering(identifier, subject, term, instructor):
    return {
        "id": identifier, "object_type": "course_offering_observation",
        "subject": subject, "academic_term": term, "instructor_raw": instructor,
        "instructor_type": {"normalized_value": "full_time", "conflicting": False},
    }


def test_inventory_counts_coverage_and_review_priority_are_deterministic(tmp_path):
    service = _service(
        _rule("direct", "ARTX", "mapped", "academic_unit:department_fine_art_art_history"),
        _rule("grouped", "CPSC", "intentionally_grouped_department_equivalent", "academic_unit:sec"),
        _rule("inter", "INTD", "interdisciplinary"),
        _rule("service", "SERV", "service_subject"),
        _rule("nonwork", "NOWK", "non_workforce_unit"),
    )
    observations = [
        _offering("1", "ARTX", "2023_fall", "Doe, Jane"),
        _offering("2", "ARTX", "2024_spring", "Jane Doe"),
        _offering("3", "CPSC", "2024_fall", "A Person"),
        _offering("4", "INTD", "2024_fall", "B Person"),
        _offering("5", "SERV", "2024_fall", "C Person"),
        _offering("6", "NOWK", "2024_fall", "D Person"),
        _offering("7", "ZZZZ", "2024_fall", "E Person"),
        _offering("8", "ZZZZ", "2025_spring", "F Person"),
        _offering("9", "YYYY", "2024_fall", "G Person"),
    ]
    first = service.build(observations)
    second = service.build(reversed(observations))
    assert first.deterministic_report_fingerprint == second.deterministic_report_fingerprint
    rows = {row.subject_code: row for row in first.subject_inventory}
    assert rows["ARTX"].course_offering_count == 2
    assert rows["ARTX"].distinct_instructor_count == 1
    assert rows["ARTX"].first_supported_term == "2023_fall"
    assert rows["ARTX"].last_supported_term == "2024_spring"
    assert rows["ARTX"].owning_academic_unit_id == "academic_unit:department_fine_art_art_history"
    coverage = first.coverage
    assert coverage.mapped_observations == 2
    assert coverage.intentionally_grouped_observations == 1
    assert coverage.interdisciplinary_observations == 1
    assert coverage.service_subject_observations == 1
    assert coverage.non_workforce_unit_observations == 1
    assert coverage.unmapped_observations == 3
    assert coverage.governed_classified_observations == 6
    assert coverage.observation_level_coverage_percent == 66.666667
    assert [item.subject_code for item in first.review_queue] == ["ZZZZ", "YYYY"]

    _write_outputs(first, tmp_path)
    payload = json.loads((tmp_path / "subject_mapping_audit.json").read_text())
    assert payload["deterministic_report_fingerprint"] == first.deterministic_report_fingerprint
    with (tmp_path / "subject_inventory.csv").open() as handle:
        assert len(list(csv.DictReader(handle))) == 7
    assert (tmp_path / "subject_mapping_audit.md").read_text().startswith("# Schedule Subject Mapping Audit")


def test_provisional_and_ambiguous_are_not_governed_coverage():
    service = _service(
        _rule("provisional", "PROV", "mapped", "academic_unit:department_fine_art_art_history", "provisional"),
        _rule("amb-one", "AMBG", "mapped", "academic_unit:department_fine_art_art_history"),
        _rule("amb-two", "AMBG", "mapped", "academic_unit:department_music_theatre_dance"),
    )
    report = service.build([
        _offering("1", "PROV", "2024_fall", "A"),
        _offering("2", "AMBG", "2024_fall", "B"),
    ])
    assert report.coverage.governed_classified_observations == 0
    assert report.coverage.mapped_observations == 0
    assert report.coverage.provisional_observations == 1
    assert report.coverage.ambiguous_observations == 1
    assert report.coverage.observation_level_coverage_percent == 0.0


def test_comparison_reports_semantic_changes_but_ignores_timestamps():
    old = {
        "registry_fingerprint": "old",
        "subject_inventory": [
            {"subject_code": "AAAA", "mapping_status": "unmapped", "academic_unit_id": None, "authoritative_source": None, "review_status": None},
            {"subject_code": "BBBB", "mapping_status": "ambiguous", "academic_unit_id": None, "authoritative_source": "old-source", "review_status": "requires_review"},
        ],
        "coverage": {"observation_level_coverage_percent": 0, "subject_code_level_coverage_percent": 0},
        "generated_at": "yesterday",
    }
    new = {
        "registry_fingerprint": "new",
        "subject_inventory": [
            {"subject_code": "AAAA", "mapping_status": "mapped", "academic_unit_id": "unit:a", "authoritative_source": "config/a.yaml", "review_status": "governed"},
            {"subject_code": "BBBB", "mapping_status": "mapped", "academic_unit_id": "unit:b", "authoritative_source": "config/b.yaml", "review_status": "governed"},
        ],
        "coverage": {"observation_level_coverage_percent": 75, "subject_code_level_coverage_percent": 100},
        "generated_at": "today",
    }
    comparison = compare_subject_mapping_reports(old, new)
    assert comparison.newly_mapped_subjects == ("AAAA", "BBBB")
    assert comparison.changed_unit_subjects == ("AAAA", "BBBB")
    assert comparison.changed_status_subjects == ("AAAA", "BBBB")
    assert comparison.resolved_ambiguities == ("BBBB",)
    assert comparison.observation_coverage_change_percentage_points == 75
    assert comparison.semantic_changes

    unchanged_old = {**new, "generated_at": "one"}
    unchanged_new = {**new, "generated_at": "two"}
    clean = compare_subject_mapping_reports(unchanged_old, unchanged_new)
    assert clean.semantic_changes is False


def test_subject_and_sec_filters_are_deterministic():
    report = ScheduleSubjectMappingInventoryService().build([
        _offering("1", "PCSE", "2024_fall", "A"),
        _offering("2", "CPSC", "2023_fall", "B"),
        _offering("3", "ZZZZ", "2025_spring", "C"),
    ])
    assert [row.subject_code for row in _selected_rows(report, ["pcse"])] == ["PCSE"]
    assert [row.subject_code for row in _selected_rows(report, sec=True)] == ["CPSC", "PCSE"]
    pcse = _selected_rows(report, ["PCSE"])[0]
    assert pcse.analytical_academic_unit_id == "academic_unit:sec"
    assert pcse.course_offering_count == 1
