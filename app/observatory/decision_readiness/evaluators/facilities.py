from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from app.evidence import Evidence
from app.observatory.decision_readiness.assessment import (
    DomainAssessment,
)
from app.observatory.decision_readiness.base import (
    DomainEvaluatorSpec,
)
from app.observatory.decision_readiness.context import (
    DecisionContext,
)
from app.observatory.decision_readiness.evaluators.keyword import (
    KeywordDomainEvaluator,
    _source_text,
)


FACILITIES_SPEC = DomainEvaluatorSpec(
    name="Facilities",
    keywords=(
        "serc",
        "science and engineering research center",
        "laboratory space",
        "lab space",
        "research laboratory",
        "teaching laboratory",
        "specialized laboratory",
        "research space",
        "teaching space",
        "facility capacity",
        "facilities capacity",
        "physical infrastructure",
        "laboratory infrastructure",
        "renovation",
        "construction",
        "square feet",
        "makerspace",
        "machine shop",
    ),
)


class SpecializedFacilitiesEvaluator(
    KeywordDomainEvaluator,
):
    """
    Question-aware first-stage Facilities evaluator.

    Generic campus-building references and routine syllabus boilerplate do
    not constitute evidence that facilities are suitable for an institutional
    proposal. A source must contain substantive evidence about relevant
    physical space, infrastructure, or capacity before it can contribute to
    the Facilities assessment.
    """

    def __init__(self) -> None:
        super().__init__(FACILITIES_SPEC)

    def evaluate(
        self,
        evidence_items: Sequence[Evidence],
        context: DecisionContext,
    ) -> DomainAssessment:
        qualified_items = [
            item
            for item in evidence_items
            if self._contains_substantive_facilities_evidence(
                item
            )
        ]

        assessment = super().evaluate(
            qualified_items,
            context,
        )

        metadata = dict(assessment.metadata)
        metadata.update(
            {
                "candidate_sources": len(evidence_items),
                "qualified_sources": len(qualified_items),
                "qualification_method": (
                    "substantive_facilities_v0.1"
                ),
            }
        )

        return replace(
            assessment,
            metadata=metadata,
        )

    def _contains_substantive_facilities_evidence(
        self,
        item: Evidence,
    ) -> bool:
        text = _source_text(item)

        return any(
            indicator in text
            for indicator in FACILITIES_SPEC.keywords
        )


FacilitiesEvaluator = SpecializedFacilitiesEvaluator()
