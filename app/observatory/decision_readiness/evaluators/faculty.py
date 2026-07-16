from app.observatory.decision_readiness.base import DomainEvaluatorSpec
from app.observatory.decision_readiness.evaluators.keyword import (
    KeywordDomainEvaluator,
)

FacultyEvaluator = KeywordDomainEvaluator(
    DomainEvaluatorSpec(
        name="Faculty",
        keywords=(
            "faculty",
            "faculty line",
            "staffing",
            "instructor",
            "tenure",
            "adjunct",
        ),
    )
)
