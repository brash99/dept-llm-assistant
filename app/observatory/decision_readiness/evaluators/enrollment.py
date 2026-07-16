from app.observatory.decision_readiness.base import DomainEvaluatorSpec
from app.observatory.decision_readiness.evaluators.keyword import (
    KeywordDomainEvaluator,
)

EnrollmentEvaluator = KeywordDomainEvaluator(
    DomainEvaluatorSpec(
        name="Enrollment / Demand",
        keywords=(
            "enrollment",
            "recruitment",
            "admissions",
            "prospective students",
            "demand",
        ),
    )
)
