"""Deterministic Reasoning Layer services."""

from app.reasoning.query import (
    QueryType,
    QueryTypeAssessment,
    classify_query_type,
    constitutional_evidence_is_relevant,
    constitutional_quota_for_query,
)
from app.reasoning.router import ReasoningRoute, ReasoningRouter
from app.reasoning.schedule_analysis import (
    INSTRUCTOR_TYPE_ADJUNCT,
    INSTRUCTOR_TYPE_FULL_TIME,
    INSTRUCTOR_TYPE_MISSING_INSTRUCTOR,
    INSTRUCTOR_TYPE_UNKNOWN,
    INSTRUCTOR_TYPE_UNRESOLVED_CONFLICT,
    ScheduleAggregationGroup,
    ScheduleAggregationResult,
    ScheduleAnalysisMetric,
    ScheduleAnalysisService,
)

__all__ = [
    "INSTRUCTOR_TYPE_ADJUNCT",
    "INSTRUCTOR_TYPE_FULL_TIME",
    "INSTRUCTOR_TYPE_MISSING_INSTRUCTOR",
    "INSTRUCTOR_TYPE_UNKNOWN",
    "INSTRUCTOR_TYPE_UNRESOLVED_CONFLICT",
    "QueryType",
    "QueryTypeAssessment",
    "ReasoningRoute",
    "ReasoningRouter",
    "ScheduleAggregationGroup",
    "ScheduleAggregationResult",
    "ScheduleAnalysisMetric",
    "ScheduleAnalysisService",
    "classify_query_type",
    "constitutional_evidence_is_relevant",
    "constitutional_quota_for_query",
]
