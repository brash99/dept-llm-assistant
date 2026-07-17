from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from app.observatory.evidence_fitness import DecisionType


@dataclass(frozen=True)
class DecisionContext:
    """
    Context shared with Decision Readiness domain evaluators.

    The initial contract is deliberately small. Additional institutional,
    constitutional, and scenario context can be added later without changing
    every evaluator interface.
    """

    question: str
    decision_type: DecisionType
    metadata: Dict[str, object] = field(
        default_factory=dict
    )
