from app.observatory.decision_readiness.base import DomainEvaluatorSpec
from app.observatory.decision_readiness.evaluators.keyword import (
    KeywordDomainEvaluator,
)

StrategicPlanningEvaluator = KeywordDomainEvaluator(
    DomainEvaluatorSpec(
        name="Strategic Planning",
        keywords=(
            "strategic",
            "planning",
            "initiative",
            "program review",
            "mission",
        ),
    )
)
