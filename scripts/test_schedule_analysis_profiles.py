from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.academic_terms import academic_term_order, academic_term_sort_key
from app.institutional_units import AcademicUnitRegistry
from app.subject_ownership import SubjectOwnershipEvidence, SubjectOwnershipRecord, SubjectOwnershipRegistry
from app.reasoning import (
    AcademicUnitMappingService,
    ReasoningRouter,
    ScheduleAnalysisService,
    ScheduleReasoningService,
    infer_schedule_grouping,
)


def _offering(identifier, term, subject, instructor, status="full_time", *, conflict=False):
    return {
        "id": identifier,
        "object_type": "course_offering_observation",
        "academic_term": term,
        "subject": subject,
        "instructor_raw": instructor,
        "instructor_type": {
            "normalized_value": status,
            "conflicting": conflict,
            "resolution": {"resolved": False},
        },
    }


def _values(result):
    return {
        (row.subject, row.academic_term, row.instructor_type): row.value
        for row in result.grouped_results
    }


def _subject_record(record_id, subject, unit_id, status="mapped", review="governed"):
    return SubjectOwnershipRecord(
        record_id, subject, subject, unit_id, unit_id,
        "owns_instructional_subject", status, "governed_registry_lookup", 1.0,
        review, (SubjectOwnershipEvidence("config/institutional_units.yaml", "governed_registry", "Synthetic assertion."),),
        "Reviewed synthetic fixture.",
    )


def test_subject_counts_distinguish_people_from_offerings():
    observations = [
        _offering("1", "2024_fall", "PHYS", "Doe, Jane"),
        _offering("2", "2024_fall", "PHYS", "Jane Doe"),
        _offering("3", "2024_fall", "CPSC", "Jane Doe"),
        _offering("4", "2025_spring", "PHYS", "A Adjunct", "adjunct"),
    ]
    service = ScheduleAnalysisService()
    people = service.analyze_observations(
        "Count distinct instructors by subject and term", observations,
        metric="distinct_instructors", group_by=("subject", "academic_term"),
    )
    offerings = service.analyze_observations(
        "Count offerings by subject and term", observations,
        metric="course_offerings", group_by=("subject", "academic_term"),
    )
    assert _values(people)[("PHYS", "2024_fall", "")] == 1
    assert _values(offerings)[("PHYS", "2024_fall", "")] == 2
    assert _values(people)[("CPSC", "2024_fall", "")] == 1


def test_share_denominators_exclude_unresolved_from_status_shares():
    observations = [
        _offering("1", "2024_fall", "PHYS", "A", "adjunct"),
        _offering("2", "2024_fall", "PHYS", "B", "adjunct"),
        _offering("3", "2024_fall", "PHYS", "C", "full_time"),
        _offering("4", "2024_fall", "PHYS", "D", "unknown", conflict=True),
        _offering("5", "2024_fall", "PHYS", None, "unknown"),
        _offering("6", "2024_fall", "PHYS", "E", "unknown"),
    ]
    service = ScheduleAnalysisService()
    adjunct = service.analyze_observations(
        "Show adjunct share by subject", observations,
        metric="adjunct_offering_share", group_by=("subject",),
    ).grouped_results[0]
    unresolved = service.analyze_observations(
        "Show unresolved share by subject", observations,
        metric="unresolved_offering_share", group_by=("subject",),
    ).grouped_results[0]
    assert (adjunct.numerator, adjunct.denominator, adjunct.value) == (2, 3, 66.666667)
    assert "unresolved observations excluded" in adjunct.denominator_definition
    assert (unresolved.numerator, unresolved.denominator, unresolved.value) == (3, 6, 50.0)


def test_governed_sec_mapping_preserves_formal_school_type():
    result = AcademicUnitMappingService().map_subject("CPSC")
    assert result.status == "intentionally_grouped_department_equivalent"
    assert result.academic_unit_id == "academic_unit:sec"
    assert result.formal_unit_type == "dependent_school"
    assert "department_equivalent" in result.operational_roles
    assert result.academic_unit_name == "School of Engineering and Computing"


def test_formal_department_unmapped_and_ambiguous_mapping_contracts():
    base = AcademicUnitRegistry.load()
    department_rule = _subject_record("test.art.v1", "ARTX", "academic_unit:department_fine_art_art_history")
    direct = AcademicUnitMappingService(
        base, SubjectOwnershipRegistry((department_rule,), registry_id="test")
    ).map_subject("ARTX")
    assert direct.status == "mapped"
    assert direct.formal_unit_type == "department"
    assert AcademicUnitMappingService().map_subject("ZZZZ").status == "unmapped"

    competing = _subject_record("test.competing.v1", "ARTX", "academic_unit:department_music_theatre_dance")
    ambiguous = AcademicUnitMappingService(
        base, SubjectOwnershipRegistry((department_rule, competing), registry_id="test")
    ).map_subject("ARTX")
    assert ambiguous.status == "ambiguous"
    assert len(ambiguous.candidate_unit_ids) == 2


def test_academic_unit_grouping_combines_sec_specialties_without_inventing_departments():
    result = ScheduleAnalysisService().analyze_observations(
        "Count offerings by academic unit and term",
        [
            _offering("1", "2024_fall", "PHYS", "A"),
            _offering("2", "2024_fall", "CPSC", "B", "adjunct"),
            _offering("3", "2024_fall", "HIST", "C"),
        ],
        metric="course_offerings", group_by=("academic_unit", "academic_term"),
    )
    row = result.grouped_results[0]
    assert row.academic_unit_id == "academic_unit:sec"
    assert row.value == 2
    assert result.mapping_coverage.intentionally_grouped_observation_count == 2
    assert result.mapping_coverage.unmapped_observation_count == 1
    assert result.excluded_object_count == 1


def test_academic_term_order_is_chronological_and_explicit_about_malformed_values():
    terms = [
        "2024_fall", "2024_summer_2", "2024_spring", "2024_extended_summer",
        "2024_may", "2024_summer_1",
    ]
    assert sorted(terms, key=academic_term_sort_key) == [
        "2024_spring", "2024_may", "2024_summer_1",
        "2024_extended_summer", "2024_summer_2", "2024_fall",
    ]
    assert academic_term_order("Fall 2024").supported is False
    assert academic_term_order("Fall 2024").warning == "unsupported_or_malformed_academic_term"


def test_trend_reports_changes_missing_terms_and_zero_denominators():
    observations = [
        _offering("1", "2023_fall", "PHYS", "A", "adjunct"),
        _offering("2", "2024_fall", "PHYS", "B", "full_time"),
        _offering("3", "2024_spring", "CPSC", "C", "adjunct"),
        _offering("4", "2023_fall", "HIST", "D", "unknown", conflict=True),
        _offering("5", "2024_fall", "HIST", "E", "unknown", conflict=True),
    ]
    service = ScheduleAnalysisService()
    trend = service.analyze_trend(
        "How did adjunct offering share change over time by subject?",
        observations=observations, metric="adjunct_offering_share", group_by=("subject",),
    )
    physics = next(row for row in trend.trends if row.subject == "PHYS")
    assert physics.first_value == 100.0
    assert physics.last_value == 0.0
    assert physics.percentage_point_change == -100.0
    assert physics.missing_term_warnings == ("No comparable group observation for 2024_spring.",)
    history = next(row for row in trend.trends if row.subject == "HIST")
    assert history.absolute_change is None
    assert "zero denominator" in " ".join(history.comparability_limitations).lower()
    repeated = service.analyze_trend(
        "How did adjunct offering share change over time by subject?",
        observations=reversed(observations), metric="adjunct_offering_share", group_by=("subject",),
    )
    assert trend.deterministic_result_fingerprint == repeated.deterministic_result_fingerprint


def test_evidence_fitness_does_not_overstate_decision_utility():
    result = ScheduleAnalysisService().analyze_observations(
        "Count offerings by subject",
        [
            _offering("1", "2024_fall", "CPSC", "A"),
            _offering("2", "2024_fall", "HIST", None, "unknown"),
            _offering("3", "bad term", "", "C", "unknown", conflict=True),
        ], metric="course_offerings", group_by=("subject",),
    )
    fitness = result.evidence_fitness
    assert fitness.total_schedule_observations == 3
    assert fitness.mapped_observations == 1
    assert fitness.unmapped_observations == 2
    assert fitness.missing_instructor_rate == pytest.approx(100 / 3, rel=1e-5)
    assert fitness.suitability["descriptive_section_analysis"] == "suitable"
    assert fitness.suitability["staffing_recommendations"] == "insufficient"
    assert fitness.suitability["workload_inference"] == "insufficient"
    assert fitness.unsupported_terms == ("bad term",)


def test_evidence_fitness_separates_workforce_and_non_workforce_mappings():
    base = AcademicUnitRegistry.load()
    # Non-workforce classifications still reference a governed analytical unit;
    # their status prevents treatment as a department assignment.
    rules = (
        _subject_record("direct", "DIR", "academic_unit:department_fine_art_art_history"),
        _subject_record("inter", "INTD", "academic_unit:faculty_arts_humanities", "interdisciplinary"),
        _subject_record("nonwork", "NOWK", "academic_unit:faculty_arts_humanities", "non_workforce_unit"),
    )
    mapping = AcademicUnitMappingService(base, SubjectOwnershipRegistry(rules, registry_id="fitness"))
    result = ScheduleAnalysisService(mapping_service=mapping).analyze_observations(
        "Count offerings by subject",
        [
            _offering("1", "2024_fall", "DIR", "A"),
            _offering("2", "2024_fall", "INTD", "B"),
            _offering("3", "2024_fall", "NOWK", "C"),
            _offering("4", "2024_fall", "MISS", "D"),
        ], metric="course_offerings", group_by=("subject",),
    )
    fitness = result.evidence_fitness
    assert fitness.workforce_mappable_observation_count == 1
    assert fitness.workforce_mapping_coverage_percent == 25.0
    assert fitness.governed_interdisciplinary_observations == 1
    assert fitness.governed_non_workforce_observations == 1
    assert result.mapping_coverage.mapped_observations == 1
    assert result.mapping_coverage.classified_non_workforce_observations == 2
    assert fitness.suitability["academic_unit_comparison"] == "insufficient_mapping_coverage"


class _FakeAnalysis:
    limitations = ("Schedule data do not establish staffing recommendations.",)
    def to_dict(self):
        return {"metric": "adjunct_offering_share", "value": 50.0}


class _FakeAnalysisService:
    def analyze(self, *args, **kwargs):
        return _FakeAnalysis()
    def analyze_trend(self, *args, **kwargs):
        return SimpleNamespace(
            to_dict=lambda: {"metric": "adjunct_offering_share", "trends": []},
            source_aggregation=_FakeAnalysis(),
        )


def test_end_to_end_reasoning_plan_separates_analysis_retrieval_and_scenarios():
    service = ScheduleReasoningService(_FakeAnalysisService())
    descriptive = service.execute("Which subjects had the highest adjunct offering share?")
    assert descriptive.supported
    assert descriptive.analytical_result["value"] == 50.0
    assert descriptive.retrieved_evidence_request is None

    normative = service.execute(
        "Does adjunct dependence in a subject create tension with the Strategic Compass?"
    )
    assert normative.supported
    assert normative.retrieved_evidence_request.constitutional_required

    scenario = service.execute(
        "If CNU reduces faculty from 275 to 250, which units should lose positions?"
    )
    assert not scenario.supported
    assert scenario.execution_service == "scenario_modeling"
    assert scenario.analytical_result is None

    assert ReasoningRouter().route("Who taught PHIL 215 S07?").execution_service == "retrieval"
    assert ReasoningRouter().route("Find a Full Time course offering.").query_type.value == "selective_retrieval"
    assert ReasoningRouter().route("What was the Instructor Type for PHIL 215 S07?").execution_service == "retrieval"
    assert ReasoningRouter().route("Average class size by subject").execution_service == "unsupported"
    assert infer_schedule_grouping(
        "How many adjunct-taught course offerings were there by term?"
    ) == ("academic_term", "normalized_instructor_type")
