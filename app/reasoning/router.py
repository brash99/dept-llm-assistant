"""Deterministic routing between retrieval and analytical services."""

from __future__ import annotations

from dataclasses import dataclass
import re

from app.reasoning.query import (
    QueryType,
    classify_query_type,
    constitutional_evidence_is_relevant,
)


_SUPPORTED_SCHEDULE_ANALYSIS = re.compile(
    r"\b(?:instructors?|sections?|offerings?|subjects?|academic units?|"
    r"adjunct dependence)\b",
    flags=re.IGNORECASE,
)
_ANALYTICAL_INTENT = re.compile(
    r"\b(?:count|average|mean|median|total|share|percentage|rate|trend|"
    r"compare|comparison|over time|how many|how much|highest|lowest)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ReasoningRoute:
    request: str
    query_type: QueryType
    execution_service: str
    constitutional_retrieval: bool
    rationale: str


class ReasoningRouter:
    """Choose a registered execution service without invoking it."""

    def route(self, request: str) -> ReasoningRoute:
        assessment = classify_query_type(request)
        schedule_request = bool(_SUPPORTED_SCHEDULE_ANALYSIS.search(request))
        if assessment.query_type in {
            QueryType.STRUCTURED_AGGREGATION,
            QueryType.COMPARISON,
            QueryType.TREND_ANALYSIS,
        } and schedule_request:
            service = "schedule_analysis"
        elif assessment.query_type == QueryType.SELECTIVE_RETRIEVAL:
            service = "retrieval"
        elif assessment.query_type == QueryType.SCENARIO_MODELING:
            service = "scenario_modeling"
        elif assessment.query_type == QueryType.UNSUPPORTED and not _ANALYTICAL_INTENT.search(request):
            service = "retrieval"
        else:
            service = "unsupported"
        return ReasoningRoute(
            request=request,
            query_type=assessment.query_type,
            execution_service=service,
            constitutional_retrieval=constitutional_evidence_is_relevant(request),
            rationale=assessment.rationale,
        )


__all__ = ["ReasoningRoute", "ReasoningRouter"]
