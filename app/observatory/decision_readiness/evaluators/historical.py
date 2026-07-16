from app.observatory.decision_readiness.base import DomainEvaluatorSpec
from app.observatory.decision_readiness.evaluators.keyword import (
    KeywordDomainEvaluator,
)

HistoricalPrecedentEvaluator = KeywordDomainEvaluator(
    DomainEvaluatorSpec(
        name="Historical Precedent",
        keywords=(
            "historical",
            "history",
            "precedent",
            "previous proposal",
            "does not currently offer",
        ),
    )
)
