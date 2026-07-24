"""Minimal typed plan for analytical, retrieval, and hybrid reasoning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from app.reasoning.query import QueryType
from app.reasoning.router import ReasoningRouter
from app.reasoning.schedule_analysis import ScheduleAnalysisService


@dataclass(frozen=True)
class RetrievedEvidenceRequest:
    query: str
    purpose: str
    constitutional_required: bool


@dataclass(frozen=True)
class HybridReasoningResult:
    request: str
    query_type: str
    execution_service: str
    analytical_result: Mapping[str, Any] | None
    retrieved_evidence_request: RetrievedEvidenceRequest | None
    response_sections: tuple[str, ...]
    unresolved_limitations: tuple[str, ...]
    supported: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "retrieved_evidence_request": (
                asdict(self.retrieved_evidence_request)
                if self.retrieved_evidence_request else None
            ),
        }


class ScheduleReasoningService:
    """Execute supported schedule analytics and expose optional evidence needs."""

    def __init__(
        self,
        analysis_service: ScheduleAnalysisService | None = None,
        router: ReasoningRouter | None = None,
    ):
        self.analysis_service = analysis_service or ScheduleAnalysisService()
        self.router = router or ReasoningRouter()

    def execute(
        self,
        request: str,
        *,
        metric: str | None = None,
        group_by: tuple[str, ...] | None = None,
        trend: bool | None = None,
        **filters: Any,
    ) -> HybridReasoningResult:
        route = self.router.route(request)
        if route.execution_service != "schedule_analysis":
            limitations = (
                "Scenario Modeling is required; schedule adjunct shares alone cannot support staffing recommendations."
                if route.query_type == QueryType.SCENARIO_MODELING else
                "No registered deterministic analytical capability supports this request."
            )
            return HybridReasoningResult(
                request, route.query_type.value, route.execution_service, None,
                None, ("Unsupported analysis",), (limitations,), False,
            )
        selected_grouping = group_by or infer_schedule_grouping(request)
        wants_trend = route.query_type == QueryType.TREND_ANALYSIS if trend is None else trend
        if wants_trend:
            selected_metric = metric or infer_schedule_metric(request)
            result = self.analysis_service.analyze_trend(
                request, metric=selected_metric,
                group_by=tuple(field for field in selected_grouping if field != "academic_term"),
                **filters,
            )
        else:
            result = self.analysis_service.analyze(
                request, metric=metric, group_by=selected_grouping, **filters
            )
        evidence_request = None
        sections = ["Deterministic schedule analysis", "Evidence Fitness and limitations"]
        if route.constitutional_retrieval:
            evidence_request = RetrievedEvidenceRequest(
                query=request,
                purpose="Provide constitutional context separately from computed schedule facts.",
                constitutional_required=True,
            )
            sections.append("Selected constitutional context")
        return HybridReasoningResult(
            request=request, query_type=route.query_type.value,
            execution_service=route.execution_service,
            analytical_result=result.to_dict(),
            retrieved_evidence_request=evidence_request,
            response_sections=tuple(sections),
            unresolved_limitations=tuple(result.source_aggregation.limitations if wants_trend else result.limitations),
            supported=True,
        )


def infer_schedule_metric(request: str) -> str:
    text = " ".join(request.casefold().split())
    if "unresolved" in text and any(word in text for word in ("share", "rate", "percentage")):
        return "unresolved_offering_share"
    if "adjunct" in text and any(word in text for word in ("share", "dependence", "percentage", "rate")):
        return "adjunct_offering_share"
    if "full time" in text and any(word in text for word in ("share", "percentage", "rate")):
        return "full_time_offering_share"
    if "distinct instructor" in text or "unique instructor" in text:
        return "distinct_instructors"
    return "course_offerings"


def infer_schedule_grouping(request: str) -> tuple[str, ...]:
    text = " ".join(request.casefold().split())
    grouping = []
    if "academic unit" in text:
        grouping.append("academic_unit")
    elif "subject" in text:
        grouping.append("subject")
    if any(value in text for value in ("by term", "each term", "over time", "trend")):
        grouping.append("academic_term")
    if (
        any(value in text for value in ("adjunct", "full time", "instructor type"))
        and not any(value in text for value in ("share", "percentage", "rate", "dependence"))
    ):
        grouping.append("normalized_instructor_type")
    if not grouping:
        grouping.append("academic_term")
    return tuple(grouping)


__all__ = [
    "HybridReasoningResult", "RetrievedEvidenceRequest",
    "ScheduleReasoningService", "infer_schedule_grouping",
    "infer_schedule_metric",
]
