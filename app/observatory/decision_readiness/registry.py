from __future__ import annotations

from typing import Dict, Iterable, List

from app.observatory.decision_readiness.base import (
    DomainEvaluator,
)


class EvaluatorRegistry:
    """
    Registry mapping decision-type identifiers to ordered domain evaluators.
    """

    def __init__(self) -> None:
        self._evaluators: Dict[
            str,
            List[DomainEvaluator],
        ] = {}

    def register(
        self,
        decision_type: str,
        evaluators: Iterable[DomainEvaluator],
    ) -> None:
        self._evaluators[decision_type] = list(
            evaluators
        )

    def get(
        self,
        decision_type: str,
    ) -> List[DomainEvaluator]:
        return list(
            self._evaluators.get(
                decision_type,
                [],
            )
        )

    def contains(
        self,
        decision_type: str,
    ) -> bool:
        return decision_type in self._evaluators

    def decision_types(self) -> List[str]:
        return sorted(self._evaluators)


registry = EvaluatorRegistry()


def register_default_evaluators() -> None:
    """
    Register the built-in evaluator collections.

    Imports are local to avoid package initialization cycles.
    """
    from app.observatory.decision_readiness.evaluators import (
        ACADEMIC_PROGRAM_EVALUATORS,
        ACADEMIC_WORKFORCE_PLANNING_EVALUATORS,
    )

    registry.register(
        "academic_program",
        ACADEMIC_PROGRAM_EVALUATORS,
    )

    registry.register(
        "academic_workforce_planning",
        ACADEMIC_WORKFORCE_PLANNING_EVALUATORS,
    )

    # General institutional questions currently use the same
    # deterministic domain suite as academic-program questions.
    # More specialized evaluator collections can be introduced
    # as additional decision types mature.
    registry.register(
        "general_institutional",
        ACADEMIC_PROGRAM_EVALUATORS,
    )


register_default_evaluators()
