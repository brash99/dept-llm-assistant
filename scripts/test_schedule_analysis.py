from __future__ import annotations

from pathlib import Path

import pytest

from app.reasoning import (
    QueryType,
    ReasoningRouter,
    ScheduleAnalysisMetric,
    ScheduleAnalysisService,
    classify_query_type,
    constitutional_evidence_is_relevant,
    constitutional_quota_for_query,
)
from app.source_presentation import repository_relative_path


def _offering(
    object_id: str,
    term: str,
    instructor: str | None,
    normalized_type: str = "full_time",
    *,
    conflicting: bool = False,
    resolved: bool = False,
) -> dict:
    return {
        "id": object_id,
        "object_type": "course_offering_observation",
        "academic_term": term,
        "instructor_raw": instructor,
        "instructor_type": {
            "published_values": ["Full Time", "Adjunct"]
            if conflicting else [normalized_type.replace("_", " ").title()],
            "normalized_value": normalized_type,
            "conflicting": conflicting,
            "resolution": {
                "resolved": resolved,
                "method": "same_instructor_same_term_consensus" if resolved else None,
            },
        },
    }


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Who taught PHIL 215?", QueryType.SELECTIVE_RETRIEVAL),
        ("How many adjunct instructors taught each term?", QueryType.STRUCTURED_AGGREGATION),
        ("Compare adjunct and full-time sections", QueryType.COMPARISON),
        ("Show the instructional workload trend over time", QueryType.TREND_ANALYSIS),
        ("What would happen if CNU removed 25 positions?", QueryType.SCENARIO_MODELING),
        ("Tell me something interesting", QueryType.UNSUPPORTED),
    ],
)
def test_query_type_rules(query, expected):
    assert classify_query_type(query).query_type == expected


def test_distinct_instructors_deduplicates_within_group():
    observations = [
        _offering("a", "2024_fall", "Davis, Kimberly", "full_time"),
        _offering("b", "2024_fall", "Kimberly Davis", "full_time"),
        _offering("c", "2024_fall", "Alex Smith", "adjunct"),
    ]
    result = ScheduleAnalysisService().analyze_observations(
        "How many distinct instructors taught each term?", observations
    )
    values = {
        (group.academic_term, group.instructor_type): group.value
        for group in result.grouped_results
    }
    assert values[("2024_fall", "Full Time")] == 1
    assert values[("2024_fall", "Adjunct")] == 1
    assert result.included_object_count == 3


def test_course_offerings_counts_sections_separately():
    observations = [
        _offering("a", "2024_fall", "Kimberly Davis"),
        _offering("b", "2024_fall", "Kimberly Davis"),
    ]
    result = ScheduleAnalysisService().analyze_observations(
        "How many course offerings were taught each term?",
        observations,
        metric=ScheduleAnalysisMetric.COURSE_OFFERINGS,
    )
    assert result.totals["Full Time"] == 2


def test_uncertainty_and_missing_instructors_are_explicit():
    observations = [
        _offering("a", "2024_fall", "A Person", "unknown", conflicting=True),
        _offering("b", "2024_fall", None, "unknown"),
        _offering("c", "2024_fall", "B Person", "adjunct", conflicting=True, resolved=True),
    ]
    result = ScheduleAnalysisService().analyze_observations(
        "Count course offerings by term and instructor type",
        observations,
        metric="course_offerings",
    )
    assert result.totals["Unresolved Conflict"] == 1
    assert result.totals["Missing Instructor"] == 1
    assert result.totals["Adjunct"] == 1
    assert result.uncertainty_summary == {
        "source_conflicted_observations": 2,
        "unresolved_conflict_observations": 1,
        "repaired_instructor_type_observations": 1,
        "missing_instructor_observations": 1,
        "unknown_instructor_type_observations": 0,
    }


def test_distinct_metric_excludes_missing_instructor():
    result = ScheduleAnalysisService().analyze_observations(
        "Count distinct instructors by term",
        [_offering("a", "2024_fall", None, "unknown")],
    )
    assert result.included_object_count == 0
    assert result.excluded_object_count == 1
    assert result.totals["Missing Instructor"] == 0


def test_result_is_deterministic_across_input_order():
    observations = [
        _offering("a", "2023_fall", "A Person", "adjunct"),
        _offering("b", "2024_spring", "B Person", "full_time"),
    ]
    service = ScheduleAnalysisService()
    first = service.analyze_observations("Count sections by term", observations, metric="course_offerings")
    second = service.analyze_observations("Count sections by term", reversed(observations), metric="course_offerings")
    assert first.to_dict() == second.to_dict()


def test_router_selects_analysis_without_constitutional_evidence():
    route = ReasoningRouter().route("How many adjunct instructors taught each term?")
    assert route.execution_service == "schedule_analysis"
    assert route.constitutional_retrieval is False
    assert ReasoningRouter().route("Who taught PHIL 215?").execution_service == "retrieval"
    assert ReasoningRouter().route(
        "Show instructional workload trends over time"
    ).execution_service == "unsupported"


def test_constitutional_evidence_is_reserved_for_normative_requests():
    assert not constitutional_evidence_is_relevant("Count adjunct sections by term")
    assert constitutional_quota_for_query("Count adjunct sections by term", 2) == 0
    assert constitutional_evidence_is_relevant(
        "How should faculty allocation align with the Strategic Compass?"
    )
    assert constitutional_quota_for_query(
        "How should faculty allocation align with the Strategic Compass?", 2
    ) == 2


def test_repository_paths_are_machine_independent():
    assert repository_relative_path(
        "/Users/brash/dept-llm-assistant/storage/normalized/example.json"
    ) == "storage/normalized/example.json"
    assert repository_relative_path(
        "/work/brash/dept-llm-assistant/data/source.csv"
    ) == "data/source.csv"
    assert repository_relative_path("https://example.edu/report") == "https://example.edu/report"
    assert repository_relative_path(Path("storage/normalized/example.json")) == (
        "storage/normalized/example.json"
    )
