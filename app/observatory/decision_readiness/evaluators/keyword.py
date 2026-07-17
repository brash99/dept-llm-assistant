from __future__ import annotations

from typing import Dict, List, Sequence, Set

from app.evidence import Evidence, EvidenceClass
from app.observatory.decision_readiness.assessment import (
    DomainAssessment,
)
from app.observatory.decision_readiness.base import (
    DomainEvaluator,
    DomainEvaluatorSpec,
)
from app.observatory.decision_readiness.context import (
    DecisionContext,
)


EVIDENCE_CLASS_STRENGTH: Dict[
    EvidenceClass,
    float,
] = {
    EvidenceClass.CONSTITUTIONAL: 0.55,
    EvidenceClass.INSTITUTIONAL: 1.00,
    EvidenceClass.PLANNING: 0.65,
    EvidenceClass.HISTORICAL: 0.60,
    EvidenceClass.EXTERNAL_STANDARD: 0.90,
    EvidenceClass.EXTERNAL_COMPARATOR: 0.55,
    EvidenceClass.BACKGROUND: 0.30,
}


def _source_text(item: Evidence) -> str:
    citation = item.result.citation or {}

    parts = [
        citation.get("title") or "",
        citation.get("relative_path") or "",
        citation.get("source_path") or "",
        item.result.text or "",
    ]

    return " ".join(
        str(part)
        for part in parts
        if part
    ).casefold()


def _source_title(item: Evidence) -> str:
    citation = item.result.citation or {}

    return str(
        citation.get("title")
        or citation.get("relative_path")
        or "Untitled source"
    )


class KeywordDomainEvaluator(DomainEvaluator):
    """
    Deterministic evaluator preserving the current graded-domain algorithm.

    DR-001 deliberately moves existing behavior into a reusable evaluator
    without introducing new adequacy rules.
    """

    def __init__(
        self,
        spec: DomainEvaluatorSpec,
    ) -> None:
        self.spec = spec

    def evaluate(
        self,
        evidence_items: Sequence[Evidence],
        context: DecisionContext,
    ) -> DomainAssessment:
        supporting_items: List[Evidence] = []
        matched_keywords: Set[str] = set()

        for item in evidence_items:
            text = _source_text(item)

            item_matches = {
                keyword
                for keyword in self.spec.keywords
                if keyword.casefold() in text
            }

            if not item_matches:
                continue

            supporting_items.append(item)
            matched_keywords.update(item_matches)

        source_count = len(supporting_items)
        keyword_count = len(matched_keywords)

        if not supporting_items:
            return DomainAssessment(
                name=self.spec.name,
                score=0.0,
                status="missing",
                missing_requirements=list(
                    self.spec.required_evidence
                ),
                recommendations=[
                    (
                        "Acquire or retrieve direct evidence "
                        f"for {self.spec.name}."
                    )
                ],
                metadata={
                    "best_class_strength": 0.0,
                    "mean_class_strength": 0.0,
                },
            )

        class_strengths = [
            EVIDENCE_CLASS_STRENGTH.get(
                item.evidence_class,
                0.30,
            )
            for item in supporting_items
        ]

        best_strength = max(class_strengths)
        mean_strength = (
            sum(class_strengths)
            / len(class_strengths)
        )

        breadth_score = min(
            1.0,
            keyword_count / 3.0,
        )

        source_score = min(
            1.0,
            source_count / 3.0,
        )

        class_score = (
            0.60 * best_strength
            + 0.40 * mean_strength
        )

        support_score = (
            0.35 * breadth_score
            + 0.35 * source_score
            + 0.30 * class_score
        )

        if (
            source_count == 1
            and keyword_count == 1
        ):
            support_score = min(
                support_score,
                0.34,
            )

        if support_score >= 0.78:
            status = "strong"
        elif support_score >= 0.52:
            status = "partial"
        elif support_score > 0:
            status = "weak"
        else:
            status = "missing"

        limitations: List[str] = []
        recommendations: List[str] = []

        if status == "weak":
            limitations.append(
                "The domain is mentioned, but the retrieved "
                "support is thin."
            )
            recommendations.append(
                f"Strengthen direct evidence for {self.spec.name}."
            )

        if status == "partial":
            limitations.append(
                "Meaningful evidence exists, but important "
                "aspects remain unresolved."
            )

        return DomainAssessment(
            name=self.spec.name,
            score=round(
                100.0 * support_score,
                1,
            ),
            status=status,
            supporting_sources=source_count,
            keyword_breadth=keyword_count,
            matched_keywords=sorted(
                matched_keywords
            ),
            source_titles=[
                _source_title(item)
                for item in supporting_items
            ],
            limitations=limitations,
            missing_requirements=(
                list(self.spec.required_evidence)
                if status in {"missing", "weak"}
                else []
            ),
            recommendations=recommendations,
            metadata={
                "best_class_strength": round(
                    best_strength,
                    3,
                ),
                "mean_class_strength": round(
                    mean_strength,
                    3,
                ),
            },
        )
