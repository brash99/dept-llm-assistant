from types import SimpleNamespace

from app.evidence import EvidenceClass
from app.observatory.decision_readiness import (
    DomainEvaluatorSpec,
)
from app.observatory.decision_readiness.context import (
    DecisionContext,
)
from app.observatory.evidence_fitness import (
    DecisionType,
)
from app.observatory.decision_readiness.evaluators import (
    KeywordDomainEvaluator,
)


def fake_evidence(
    *,
    title: str,
    text: str,
    evidence_class: EvidenceClass,
):
    result = SimpleNamespace(
        citation={
            "title": title,
            "relative_path": title,
            "source_path": title,
        },
        text=text,
    )

    return SimpleNamespace(
        result=result,
        evidence_class=evidence_class,
    )


def test_keyword_domain_evaluator():
    evaluator = KeywordDomainEvaluator(
        DomainEvaluatorSpec(
            name="Facilities",
            keywords=(
                "facility",
                "makerspace",
                "machine shop",
            ),
        )
    )

    assessment = evaluator.evaluate(
        [
            fake_evidence(
                title="Facilities Plan",
                text=(
                    "The facility plan discusses a makerspace "
                    "and machine shop."
                ),
                evidence_class=(
                    EvidenceClass.PLANNING
                ),
            ),
            fake_evidence(
                title="Program Review",
                text=(
                    "The program review identifies makerspace "
                    "capacity concerns."
                ),
                evidence_class=(
                    EvidenceClass.INSTITUTIONAL
                ),
            ),
        ],
        DecisionContext(
            question=(
                "Should CNU establish an academic program?"
            ),
            decision_type=DecisionType.ACADEMIC_PROGRAM,
        ),
    )

    assert assessment.name == "Facilities"
    assert assessment.supporting_sources == 2
    assert assessment.keyword_breadth == 3
    assert assessment.status in {
        "partial",
        "strong",
    }


if __name__ == "__main__":
    test_keyword_domain_evaluator()
    print(
        "Decision Readiness framework tests passed."
    )
