from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class DomainAssessment:
    """
    Structured assessment of one decision domain.

    The evaluator records both the conclusion and the observable support used
    to reach it. Scores are expressed on a 0–100 scale.
    """

    name: str
    score: float
    status: str

    supporting_sources: int = 0
    keyword_breadth: int = 0

    matched_keywords: List[str] = field(
        default_factory=list
    )
    source_titles: List[str] = field(
        default_factory=list
    )

    strengths: List[str] = field(
        default_factory=list
    )
    limitations: List[str] = field(
        default_factory=list
    )
    missing_requirements: List[str] = field(
        default_factory=list
    )
    recommendations: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, object] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class DecisionReadinessAssessment:
    """
    Composite result produced by the Decision Readiness subsystem.
    """

    decision_type: str
    decision_type_label: str
    classification_confidence: float

    overall_score: float
    domain_score: float
    authority_fit_score: float
    evidence_role_fit_score: float

    domains: List[DomainAssessment] = field(
        default_factory=list
    )

    strengths: List[str] = field(
        default_factory=list
    )
    limitations: List[str] = field(
        default_factory=list
    )
    recommendations: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, object] = field(
        default_factory=dict
    )
