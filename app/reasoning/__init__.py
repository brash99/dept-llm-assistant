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
from app.reasoning.subject_crosswalk_audit import (
    CrosswalkAuditFinding,
    SubjectCrosswalkAuditReport,
    SubjectCrosswalkAuditService,
)
from app.reasoning.subject_mapping_inventory import (
    ScheduleSubjectMappingInventoryService,
    ScheduleSubjectMappingReport,
    SubjectMappingComparison,
    compare_subject_mapping_reports,
)
from app.subject_ownership import (
    SubjectOwnershipEvidence,
    SubjectOwnershipRecord,
    SubjectOwnershipRegistry,
)

__all__ = [
    "AcademicUnitMappingResult",
    "AcademicUnitMappingService",
    "AcademicUnitMappingStatus",
    "CrosswalkAuditFinding",
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
    "ScheduleSubjectMappingInventoryService",
    "ScheduleSubjectMappingReport",
    "ScheduleTrendGroup",
    "ScheduleTrendResult",
    "SubjectCrosswalkAuditReport",
    "SubjectCrosswalkAuditService",
    "SubjectMappingComparison",
    "SubjectOwnershipEvidence",
    "SubjectOwnershipRecord",
    "SubjectOwnershipRegistry",
    "classify_query_type",
    "constitutional_evidence_is_relevant",
    "constitutional_quota_for_query",
    "compare_subject_mapping_reports",
    "infer_schedule_grouping",
    "infer_schedule_metric",
]
