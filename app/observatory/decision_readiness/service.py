from __future__ import annotations

from typing import List, Sequence

from app.evidence import Evidence, EvidenceClass
from app.observatory.decision_readiness.assessment import (
    DecisionReadinessAssessment,
    DomainAssessment,
)
from app.observatory.decision_readiness.context import (
    DecisionContext,
)
from app.observatory.decision_readiness.registry import (
    EvaluatorRegistry,
    registry,
)
from app.observatory.evidence_fitness import (
    EvidenceFitnessService,
    PROFILES,
)


class DecisionReadinessService:
    """
    Orchestrate domain-level assessment of evidence for an institutional
    decision.

    Decision Readiness evaluates the availability and strength of evidence
    across the domains relevant to a classified decision type. Authority fit,
    evidence-role fit, and overall evidence fitness remain separate concerns.
    """

    _GRADE_VALUES = {
        "strong": 1.00,
        "partial": 0.65,
        "weak": 0.30,
        "missing": 0.00,
    }

    def __init__(
        self,
        evaluator_registry: EvaluatorRegistry = registry,
    ) -> None:
        self._registry = evaluator_registry

    def evaluate(
        self,
        question: str,
        evidence_items: Sequence[Evidence],
    ) -> DecisionReadinessAssessment:
        """
        Classify the decision and evaluate its registered evidence domains.
        """
        decision_type, confidence = (
            EvidenceFitnessService.classify_decision_type(
                question
            )
        )

        decision_type_key = decision_type.value
        profile = PROFILES[decision_type]

        evaluator_types = self._registry.get(
            decision_type_key
        )

        if not evaluator_types:
            raise ValueError(
                "No Decision Readiness evaluators are "
                f"registered for {decision_type_key!r}."
            )

        context = DecisionContext(
            question=question,
            decision_type=decision_type,
        )

        empirical_items = [
            item
            for item in evidence_items
            if item.evidence_class
            != EvidenceClass.CONSTITUTIONAL
        ]

        domain_assessments: List[
            DomainAssessment
        ] = []

        for registered_evaluator in evaluator_types:
            # The registry may contain either evaluator instances
            # or evaluator classes. Support both forms.
            if isinstance(
                registered_evaluator,
                type,
            ):
                evaluator = registered_evaluator()
            else:
                evaluator = registered_evaluator

            assessment = evaluator.evaluate(
                empirical_items,
                context,
            )

            domain_assessments.append(
                assessment
            )

        domain_score = self._calculate_domain_score(
            domain_assessments
        )

        strengths = self._collect_strengths(
            domain_assessments
        )

        limitations = self._collect_limitations(
            domain_assessments
        )

        recommendations = (
            self._collect_recommendations(
                domain_assessments
            )
        )

        return DecisionReadinessAssessment(
            decision_type=decision_type_key,
            decision_type_label=profile.label,
            classification_confidence=confidence,
            overall_score=domain_score,
            domain_score=domain_score,
            authority_fit_score=0.0,
            evidence_role_fit_score=0.0,
            domains=domain_assessments,
            strengths=strengths,
            limitations=limitations,
            recommendations=recommendations,
            metadata={
                "empirical_evidence_count": len(
                    empirical_items
                ),
                "evaluator_count": len(
                    domain_assessments
                ),
                "authority_fit_deferred": True,
                "evidence_role_fit_deferred": True,
            },
        )

    @classmethod
    def _calculate_domain_score(
        cls,
        assessments: Sequence[
            DomainAssessment
        ],
    ) -> float:
        """
        Reproduce the legacy topic-coverage aggregation.
        """
        if not assessments:
            return 0.0

        grade_total = sum(
            cls._GRADE_VALUES[
                assessment.status
            ]
            for assessment in assessments
        )

        return round(
            100.0
            * grade_total
            / len(assessments),
            1,
        )

    @staticmethod
    def _collect_strengths(
        assessments: Sequence[
            DomainAssessment
        ],
    ) -> List[str]:
        strengths: List[str] = []

        for assessment in assessments:
            strengths.extend(
                assessment.strengths
            )

            if (
                assessment.status == "strong"
                and not assessment.strengths
            ):
                strengths.append(
                    f"{assessment.name} has strong "
                    "evidentiary support."
                )

        return list(
            dict.fromkeys(strengths)
        )

    @staticmethod
    def _collect_limitations(
        assessments: Sequence[
            DomainAssessment
        ],
    ) -> List[str]:
        limitations: List[str] = []

        for assessment in assessments:
            limitations.extend(
                assessment.limitations
            )

            if (
                assessment.status
                in {"partial", "weak", "missing"}
                and not assessment.limitations
            ):
                limitations.append(
                    f"{assessment.name} has "
                    f"{assessment.status} "
                    "evidentiary support."
                )

        return list(
            dict.fromkeys(limitations)
        )

    @staticmethod
    def _collect_recommendations(
        assessments: Sequence[
            DomainAssessment
        ],
    ) -> List[str]:
        recommendations: List[str] = []

        for assessment in assessments:
            recommendations.extend(
                assessment.recommendations
            )

            if (
                assessment.status == "missing"
                and not assessment.recommendations
            ):
                recommendations.append(
                    "Acquire direct evidence for "
                    f"{assessment.name}."
                )

            elif (
                assessment.status == "weak"
                and not assessment.recommendations
            ):
                recommendations.append(
                    "Strengthen the evidence base for "
                    f"{assessment.name}."
                )

        return list(
            dict.fromkeys(recommendations)
        )
