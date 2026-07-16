from app.observatory.decision_readiness.base import DomainEvaluatorSpec
from app.observatory.decision_readiness.evaluators.keyword import (
    KeywordDomainEvaluator,
)

CurriculumEvaluator = KeywordDomainEvaluator(
    DomainEvaluatorSpec(
        name="Curriculum",
        keywords=(
            "curriculum",
            "course",
            "courses",
            "major",
            "minor",
            "degree",
            "credit hours",
            "learning outcomes",
        ),
    )
)
