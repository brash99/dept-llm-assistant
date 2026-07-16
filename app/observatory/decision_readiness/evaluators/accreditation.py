from app.observatory.decision_readiness.base import DomainEvaluatorSpec
from app.observatory.decision_readiness.evaluators.keyword import (
    KeywordDomainEvaluator,
)

AccreditationEvaluator = KeywordDomainEvaluator(
    DomainEvaluatorSpec(
        name="Accreditation",
        keywords=(
            "abet",
            "accreditation",
            "sacscoc",
            "criteria",
            "criterion",
        ),
    )
)
