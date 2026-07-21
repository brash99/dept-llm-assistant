"""Classification orchestration and aggregate, non-persistent metrics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence

from app.classification.classifiers import (
    DeterministicSemanticClassifier,
    SemanticClassifier,
)
from app.classification.contracts import ClassificationResult, ProposalStage
from app.knowledge import KnowledgeObject


@dataclass
class ClassificationMetrics:
    """Basic service-run statistics; not an Evidence Fitness judgment."""

    number_classified: int = 0
    method_counts: Counter[str] = field(default_factory=Counter)
    confidence_total: float = 0.0
    number_requiring_review: int = 0
    number_automatically_accepted: int = 0

    @property
    def average_confidence(self) -> float:
        if not self.number_classified:
            return 0.0
        return self.confidence_total / self.number_classified

    def to_dict(self) -> Dict[str, object]:
        return {
            "number_classified": self.number_classified,
            "method_used": dict(sorted(self.method_counts.items())),
            "average_confidence": self.average_confidence,
            "number_requiring_review": self.number_requiring_review,
            "number_automatically_accepted": self.number_automatically_accepted,
        }


class SemanticClassificationService:
    """Produce proposals and optionally accept/apply them through explicit policy."""

    def __init__(
        self,
        classifiers: Optional[Sequence[SemanticClassifier]] = None,
        *,
        review_threshold: float = 0.8,
        automatic_acceptance_threshold: float = 0.95,
    ) -> None:
        if not 0.0 <= review_threshold <= 1.0:
            raise ValueError("review_threshold must be between 0 and 1")
        if not 0.0 <= automatic_acceptance_threshold <= 1.0:
            raise ValueError(
                "automatic_acceptance_threshold must be between 0 and 1"
            )
        self.classifiers = tuple(
            classifiers or (DeterministicSemanticClassifier(),)
        )
        self.review_threshold = review_threshold
        self.automatic_acceptance_threshold = automatic_acceptance_threshold
        self.metrics = ClassificationMetrics()

    def classify(
        self,
        knowledge_object: KnowledgeObject,
        *,
        auto_accept: bool = True,
        apply: bool = False,
    ) -> ClassificationResult:
        classifier = next(
            (
                candidate
                for candidate in self.classifiers
                if candidate.supports(knowledge_object)
            ),
            None,
        )
        if classifier is None:
            raise ValueError(
                "No semantic classifier supports Knowledge Object type "
                f"{knowledge_object.object_type!r}"
            )

        proposal = classifier.classify(knowledge_object)
        requires_review = proposal.requires_review(self.review_threshold)
        automatically_accepted = bool(
            auto_accept
            and proposal.minimum_confidence >= self.automatic_acceptance_threshold
        )
        if automatically_accepted:
            proposal.accept()

        applied = False
        if apply:
            if proposal.stage != ProposalStage.ACCEPTED:
                raise ValueError("A proposal must be accepted before it can be applied")
            proposal.apply_to_knowledge_object(knowledge_object)
            applied = True

        self.metrics.number_classified += 1
        self.metrics.confidence_total += proposal.average_confidence
        self.metrics.number_requiring_review += int(requires_review)
        self.metrics.number_automatically_accepted += int(automatically_accepted)
        for method in proposal.methods:
            self.metrics.method_counts[method.value] += 1

        return ClassificationResult(
            proposal=proposal,
            applied=applied,
            automatically_accepted=automatically_accepted,
        )


__all__ = ["ClassificationMetrics", "SemanticClassificationService"]
