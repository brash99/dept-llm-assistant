from app.observatory.decision_readiness.base import DomainEvaluatorSpec
from app.observatory.decision_readiness.evaluators.keyword import (
    KeywordDomainEvaluator,
)

BudgetEvaluator = KeywordDomainEvaluator(
    DomainEvaluatorSpec(
        name="Budget",
        keywords=(
            "budget",
            "funding",
            "cost",
            "allocation",
            "biennium",
            "$",
            "per year",
            "annual expense",
            "annual cost",
            "salary",
            "faculty line",
            "staff position",
            "financial",
            "revenue",
        ),
    )
)
