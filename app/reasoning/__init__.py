"""Deterministic Reasoning Layer services."""

from app.reasoning.query import (
    QueryType,
    QueryTypeAssessment,
    classify_query_type,
    constitutional_evidence_is_relevant,
    constitutional_quota_for_query,
)
from app.reasoning.router import ReasoningRoute, ReasoningRouter
from app.reasoning.academic_unit_mapping import (
    AcademicUnitMappingResult,
    AcademicUnitMappingService,
    AcademicUnitMappingStatus,
)
from app.reasoning.hybrid import (
    HybridReasoningResult,
    RetrievedEvidenceRequest,
    ScheduleReasoningService,
    infer_schedule_grouping,
    infer_schedule_metric,
)
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
    ScheduleEvidenceFitness,
    ScheduleTrendGroup,
    ScheduleTrendResult,
)

__all__ = [
    "AcademicUnitMappingResult",
    "AcademicUnitMappingService",
    "AcademicUnitMappingStatus",
    "HybridReasoningResult",
    "INSTRUCTOR_TYPE_ADJUNCT",
    "INSTRUCTOR_TYPE_FULL_TIME",
    "INSTRUCTOR_TYPE_MISSING_INSTRUCTOR",
    "INSTRUCTOR_TYPE_UNKNOWN",
    "INSTRUCTOR_TYPE_UNRESOLVED_CONFLICT",
    "QueryType",
    "QueryTypeAssessment",
    "ReasoningRoute",
    "ReasoningRouter",
    "RetrievedEvidenceRequest",
    "ScheduleAggregationGroup",
    "ScheduleAggregationResult",
    "ScheduleAnalysisMetric",
    "ScheduleAnalysisService",
    "ScheduleEvidenceFitness",
    "ScheduleReasoningService",
    "ScheduleTrendGroup",
    "ScheduleTrendResult",
    "classify_query_type",
    "constitutional_evidence_is_relevant",
    "constitutional_quota_for_query",
    "infer_schedule_grouping",
    "infer_schedule_metric",
]
