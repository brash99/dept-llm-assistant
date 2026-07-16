from app.observatory.decision_readiness.base import DomainEvaluatorSpec
from app.observatory.decision_readiness.evaluators.keyword import (
    KeywordDomainEvaluator,
)

EquipmentEvaluator = KeywordDomainEvaluator(
    DomainEvaluatorSpec(
        name="Equipment",
        keywords=(
            "equipment",
            "instrumentation",
            "machines",
            "lab equipment",
        ),
    )
)
