"""Deterministic execution-type classification for institutional questions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class QueryType(str, Enum):
    SELECTIVE_RETRIEVAL = "selective_retrieval"
    STRUCTURED_AGGREGATION = "structured_aggregation"
    COMPARISON = "comparison"
    TREND_ANALYSIS = "trend_analysis"
    SCENARIO_MODELING = "scenario_modeling"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class QueryTypeAssessment:
    query_type: QueryType
    rationale: str
    matched_rule: str


_SCENARIO_PATTERNS = (
    r"\bscenario\b",
    r"\bwhat (?:would|will) happen if\b",
    r"\bif .+\b(?:reduce[sd]?|remove[sd]?|reassign(?:s|ed)?|eliminate[sd]?|add[sd]?)\b",
    r"\bshould(?: .+)?\b(?:lose|gain|reduce|remove|reassign)\b",
    r"\bmodel (?:the )?(?:effect|impact|consequence)\b",
)
_TREND_PATTERNS = (
    r"\btrend(?:s|ed|ing)?\b",
    r"\bover time\b",
    r"\bchange(?:d|s)? (?:across|by|from|over) (?:term|semester|year)\b",
    r"\b(?:increase|decrease|growth|decline)(?:d|s)? (?:across|by|over)\b",
    r"\blongitudinal\b",
)
_COMPARISON_PATTERNS = (
    r"\bcompare\b",
    r"\bcomparison\b",
    r"\bversus\b|\bvs\.?\b",
    r"\bdifference(?:s)? between\b",
    r"\bmore .+ than\b|\bless .+ than\b",
)
_AGGREGATION_PATTERNS = (
    r"\bhow many\b",
    r"\bcount\b",
    r"\bnumber of\b",
    r"\bdistinct instructors?\b",
    r"\bunique instructors?\b",
    r"\btotal(?:s)? by\b",
    r"\b(?:share|percentage|rate) (?:of|by)\b",
    r"\badjunct (?:offering )?(?:share|dependence)\b",
    r"\bwhich .+ (?:highest|greatest|lowest)\b",
)
_SELECTIVE_PATTERNS = (
    r"\bwho (?:taught|teaches|instructed)\b",
    r"\bwhat does .+ say\b",
    r"\bwhich (?:instructor|faculty member|course|section|document)\b",
    r"\bfind (?:the )?(?:course|section|document|evidence|faculty)\b",
    r"\bfind .+\b(?:course offering|section)\b",
    r"\bwhat evidence\b",
    r"\bwhat was .+\b(?:course|section|crn)\b",
    r"\bwhat was .+\b[a-z]{2,4}\s*\d{3}\b",
)


def _normalized(request: str) -> str:
    return " ".join(str(request).casefold().split())


def _first_match(text: str, patterns: tuple[str, ...]) -> str | None:
    return next((pattern for pattern in patterns if re.search(pattern, text)), None)


def classify_query_type(request: str) -> QueryTypeAssessment:
    """Classify the required execution mode without using an LLM."""
    text = _normalized(request)
    if not text:
        return QueryTypeAssessment(
            QueryType.UNSUPPORTED, "The request is empty.", "empty_request"
        )

    ordered = (
        (QueryType.SCENARIO_MODELING, _SCENARIO_PATTERNS,
         "The request asks ISO to evaluate a hypothetical institutional change."),
        (QueryType.TREND_ANALYSIS, _TREND_PATTERNS,
         "The request asks for temporal change across multiple periods."),
        (QueryType.COMPARISON, _COMPARISON_PATTERNS,
         "The request explicitly compares populations, entities, or periods."),
        (QueryType.STRUCTURED_AGGREGATION, _AGGREGATION_PATTERNS,
         "The request asks for a deterministic count or grouped aggregate."),
        (QueryType.SELECTIVE_RETRIEVAL, _SELECTIVE_PATTERNS,
         "The request asks for a bounded fact or evidence lookup."),
    )
    for query_type, patterns, rationale in ordered:
        matched = _first_match(text, patterns)
        if matched:
            return QueryTypeAssessment(query_type, rationale, matched)
    return QueryTypeAssessment(
        QueryType.UNSUPPORTED,
        "No registered deterministic execution-type rule matched the request.",
        "no_registered_rule",
    )


_NORMATIVE_PATTERNS = (
    r"\bshould\b",
    r"\bought\b",
    r"\brecommend(?:ation|ed|s)?\b",
    r"\bstrategic compass\b",
    r"\bmission\b",
    r"\binstitutional values?\b",
    r"\bconstitutional\b",
    r"\balign(?:ed|ment)? with\b",
    r"\bpriority|priorities\b",
    r"\blives of significance\b",
)


def constitutional_evidence_is_relevant(request: str) -> bool:
    """Return true only for explicit normative or constitutional language."""
    text = _normalized(request)
    return any(re.search(pattern, text) for pattern in _NORMATIVE_PATTERNS)


def constitutional_quota_for_query(request: str, requested_quota: int) -> int:
    """Prevent automatic constitutional allocation for descriptive questions."""
    if requested_quota < 0:
        raise ValueError("requested constitutional quota cannot be negative")
    return requested_quota if constitutional_evidence_is_relevant(request) else 0


__all__ = [
    "QueryType",
    "QueryTypeAssessment",
    "classify_query_type",
    "constitutional_evidence_is_relevant",
    "constitutional_quota_for_query",
]
