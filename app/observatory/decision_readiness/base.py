from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence, Tuple

from app.evidence import Evidence
from app.observatory.decision_readiness.assessment import (
    DomainAssessment,
)
from app.observatory.decision_readiness.context import (
    DecisionContext,
)


@dataclass(frozen=True)
class DomainEvaluatorSpec:
    """
    Declarative configuration shared by deterministic domain evaluators.
    """

    name: str
    keywords: Tuple[str, ...]
    weight: float = 1.0

    adequacy_indicators: Tuple[str, ...] = ()
    required_evidence: Tuple[str, ...] = ()

    minimum_sources_for_partial: int = 1
    minimum_sources_for_strong: int = 3


class DomainEvaluator(ABC):
    """
    Contract implemented by every Decision Readiness domain evaluator.

    Evaluators receive both the evidence collection and the context of the
    institutional decision being assessed.
    """

    spec: DomainEvaluatorSpec

    @abstractmethod
    def evaluate(
        self,
        evidence_items: Sequence[Evidence],
        context: DecisionContext,
    ) -> DomainAssessment:
        raise NotImplementedError
