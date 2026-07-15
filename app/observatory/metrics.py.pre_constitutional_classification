from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from math import log2
from typing import Dict, Iterable, List

from app.evidence import Evidence, EvidenceClass, EVIDENCE_CLASS_ORDER


@dataclass
class ObservatoryAssessment:
    """Version 0.1 observatory assessment for one retrieval/decision run.

    These metrics are intentionally simple and deterministic. They summarize
    the retrieved evidence landscape before the LLM writes the Decision Brief.
    """

    total_sources: int
    evidence_class_counts: Dict[str, int]
    evidence_class_percentages: Dict[str, float]
    dominant_evidence_class: str
    institutional_evidence_ratio: float
    planning_ratio: float
    external_ratio: float
    evidence_balance_score: float
    topic_coverage_score: float
    knowledge_completeness_score: float
    decision_readiness_score: float
    covered_topics: List[str] = field(default_factory=list)
    missing_topics: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "Curriculum": [
        "curriculum",
        "course",
        "courses",
        "major",
        "minor",
        "program learning outcomes",
        "credit hours",
    ],
    "Faculty": [
        "faculty",
        "faculty line",
        "faculty lines",
        "tenure",
        "adjunct",
        "instructor",
        "staffing",
    ],
    "Facilities": [
        "facility",
        "facilities",
        "space",
        "building",
        "serc",
        "science and engineering research center",
        "makerspace",
        "laboratory space",
    ],
    "Equipment": [
        "equipment",
        "machine shop",
        "machines",
        "instrumentation",
        "oscilloscope",
        "fpga",
        "lab equipment",
    ],
    "Accreditation": [
        "abet",
        "accreditation",
        "sacscoc",
        "sacs",
        "criterion",
        "criteria",
    ],
    "Budget": [
        "budget",
        "funding",
        "$",
        "cost",
        "costs",
        "allocation",
        "biennium",
    ],
    "Enrollment / Demand": [
        "enrollment",
        "recruitment",
        "prospective students",
        "demand",
        "college board",
        "admissions",
    ],
    "Strategic Planning": [
        "strategic",
        "planning",
        "initiative",
        "initiatives",
        "program review",
        "mission",
    ],
    "Historical Precedent": [
        "previously",
        "historical",
        "history",
        "precedent",
        "archive",
        "currently offer",
        "does not currently offer",
    ],
}


def _source_text(item: Evidence) -> str:
    result = item.result
    citation = result.citation or {}
    parts = [
        citation.get("title") or "",
        citation.get("relative_path") or "",
        citation.get("source_path") or "",
        result.text or "",
    ]
    return " ".join(parts).lower()


def _entropy_balance(counts: Iterable[int]) -> float:
    """Return normalized entropy on a 0-100 scale.

    0 means all evidence is in one class. 100 means evidence is distributed
    evenly across all non-empty evidence classes represented in this run.
    """
    values = [count for count in counts if count > 0]
    total = sum(values)

    if total == 0 or len(values) <= 1:
        return 0.0

    entropy = 0.0
    for count in values:
        p = count / total
        entropy -= p * log2(p)

    max_entropy = log2(len(values))
    if max_entropy == 0:
        return 0.0

    return round(100.0 * entropy / max_entropy, 1)


def _topic_coverage(evidence_items: List[Evidence]) -> tuple[List[str], List[str]]:
    text = "\n".join(_source_text(item) for item in evidence_items)

    covered: List[str] = []
    missing: List[str] = []

    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            covered.append(topic)
        else:
            missing.append(topic)

    return covered, missing


def build_observatory_assessment(evidence_items: List[Evidence]) -> ObservatoryAssessment:
    """Compute a deterministic v0.1 observatory assessment.

    The goal is not to produce final research-grade metrics. The goal is to
    expose the evidence landscape so the dashboard and Decision Brief can begin
    distinguishing confidence from knowledge completeness.
    """
    total = len(evidence_items)

    counter = Counter(item.evidence_class for item in evidence_items)
    class_counts = {
        evidence_class.value: counter.get(evidence_class, 0)
        for evidence_class in EVIDENCE_CLASS_ORDER
    }

    if total > 0:
        class_percentages = {
            label: round(count / total, 3)
            for label, count in class_counts.items()
        }
    else:
        class_percentages = {label: 0.0 for label in class_counts}

    dominant = max(class_counts.items(), key=lambda item: item[1])[0] if total else "None"

    institutional_ratio = class_percentages.get(EvidenceClass.INSTITUTIONAL.value, 0.0)
    planning_ratio = class_percentages.get(EvidenceClass.PLANNING.value, 0.0)
    external_ratio = (
        class_percentages.get(EvidenceClass.EXTERNAL_STANDARD.value, 0.0)
        + class_percentages.get(EvidenceClass.EXTERNAL_COMPARATOR.value, 0.0)
    )

    balance = _entropy_balance(class_counts.values())
    covered_topics, missing_topics = _topic_coverage(evidence_items)
    topic_coverage = round(100.0 * len(covered_topics) / len(TOPIC_KEYWORDS), 1)

    # Knowledge completeness is intentionally stricter than topic coverage.
    # Topic coverage asks: did retrieved evidence touch the expected domains?
    # Knowledge completeness asks: is the evidence landscape strong enough to
    # support institutional reasoning? Planning-heavy or externally-dependent
    # evidence lowers completeness even when all expected topics are mentioned.
    low_institutional_penalty = max(0.0, (0.35 - institutional_ratio) * 80.0)
    planning_completeness_penalty = max(0.0, (planning_ratio - 0.50) * 45.0)
    external_completeness_penalty = max(0.0, (external_ratio - 0.20) * 35.0)
    missing_topic_penalty = 4.0 * len(missing_topics)

    completeness = round(
        max(
            0.0,
            min(
                100.0,
                topic_coverage
                - low_institutional_penalty
                - planning_completeness_penalty
                - external_completeness_penalty
                - missing_topic_penalty,
            ),
        ),
        1,
    )

    # A deliberately transparent v0.2 heuristic. This should evolve into a
    # calibrated score after we collect more Decision Brief experiments.
    institutional_component = min(100.0, institutional_ratio * 200.0)
    planning_penalty = max(0.0, (planning_ratio - 0.60) * 50.0)
    external_penalty = max(0.0, (external_ratio - 0.30) * 40.0)
    readiness = round(
        max(
            0.0,
            min(
                100.0,
                0.45 * completeness
                + 0.20 * topic_coverage
                + 0.20 * balance
                + 0.15 * institutional_component
                - planning_penalty
                - external_penalty,
            ),
        ),
        1,
    )

    warnings: List[str] = []
    recommendations: List[str] = []

    if total == 0:
        warnings.append("No evidence was retrieved.")
        recommendations.append("Broaden retrieval or verify corpus availability.")
    if planning_ratio >= 0.60:
        warnings.append(
            "Evidence landscape is dominated by planning documents; proposed actions may not be approved institutional facts."
        )
        recommendations.append("Look for approved budgets, finalized policies, or implementation records.")
    if institutional_ratio < 0.25 and total > 0:
        warnings.append("Low proportion of direct institutional evidence in retrieved sources.")
        recommendations.append("Search for annual reports, official records, meeting minutes, or current policies.")
    if external_ratio > 0.30:
        warnings.append(
            "External evidence is a substantial part of the retrieved landscape; use it for standards or comparison only."
        )
    if missing_topics:
        warnings.append(
            "Potential knowledge gaps detected: " + ", ".join(missing_topics[:5]) + "."
        )
        recommendations.append("Add or locate evidence for missing semantic domains before high-stakes decisions.")

    return ObservatoryAssessment(
        total_sources=total,
        evidence_class_counts=class_counts,
        evidence_class_percentages=class_percentages,
        dominant_evidence_class=dominant,
        institutional_evidence_ratio=round(institutional_ratio, 3),
        planning_ratio=round(planning_ratio, 3),
        external_ratio=round(external_ratio, 3),
        evidence_balance_score=balance,
        topic_coverage_score=topic_coverage,
        knowledge_completeness_score=completeness,
        decision_readiness_score=readiness,
        covered_topics=covered_topics,
        missing_topics=missing_topics,
        warnings=warnings,
        recommendations=recommendations,
    )
