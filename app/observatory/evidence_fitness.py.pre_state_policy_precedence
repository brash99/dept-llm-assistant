from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple

from app.evidence import Evidence, EvidenceClass


class DecisionType(str, Enum):
    ACADEMIC_PROGRAM = "academic_program"
    ENROLLMENT_PLANNING = "enrollment_planning"
    BUDGET_FINANCE = "budget_finance"
    STATE_POLICY = "state_policy"
    ACCREDITATION = "accreditation"
    STRATEGIC_PLANNING = "strategic_planning"
    GENERAL_INSTITUTIONAL = "general_institutional"


@dataclass(frozen=True)
class EvidenceExpectationProfile:
    decision_type: DecisionType
    label: str
    description: str
    topic_keywords: Dict[str, Tuple[str, ...]]
    preferred_classes: Tuple[EvidenceClass, ...]
    acceptable_external_ratio: float
    minimum_institutional_ratio: float


@dataclass
class EvidenceFitnessAssessment:
    decision_type: DecisionType
    decision_type_label: str
    decision_type_confidence: float
    fitness_score: float
    topic_coverage_score: float
    authority_fit_score: float
    evidence_role_fit_score: float
    covered_topics: List[str] = field(default_factory=list)
    missing_topics: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


ACADEMIC_PROGRAM_TOPICS = {
    "Curriculum": (
        "curriculum",
        "course",
        "courses",
        "major",
        "minor",
        "degree",
        "credit hours",
        "learning outcomes",
    ),
    "Faculty": (
        "faculty",
        "faculty line",
        "staffing",
        "instructor",
        "tenure",
        "adjunct",
    ),
    "Facilities": (
        "facility",
        "facilities",
        "space",
        "building",
        "laboratory",
        "makerspace",
        "machine shop",
    ),
    "Equipment": (
        "equipment",
        "instrumentation",
        "machines",
        "lab equipment",
    ),
    "Accreditation": (
        "abet",
        "accreditation",
        "sacscoc",
        "criteria",
        "criterion",
    ),
    "Budget": (
        "budget",
        "funding",
        "cost",
        "allocation",
        "biennium",
    ),
    "Enrollment / Demand": (
        "enrollment",
        "recruitment",
        "admissions",
        "prospective students",
        "demand",
    ),
    "Strategic Planning": (
        "strategic",
        "planning",
        "initiative",
        "program review",
        "mission",
    ),
    "Historical Precedent": (
        "historical",
        "history",
        "precedent",
        "previous proposal",
        "does not currently offer",
    ),
}


PROFILES = {
    DecisionType.ACADEMIC_PROGRAM: EvidenceExpectationProfile(
        decision_type=DecisionType.ACADEMIC_PROGRAM,
        label="Academic Program Decision",
        description=(
            "Creation, revision, continuation, closure, or evaluation "
            "of an academic program."
        ),
        topic_keywords=ACADEMIC_PROGRAM_TOPICS,
        preferred_classes=(
            EvidenceClass.INSTITUTIONAL,
            EvidenceClass.PLANNING,
            EvidenceClass.EXTERNAL_STANDARD,
            EvidenceClass.HISTORICAL,
        ),
        acceptable_external_ratio=0.35,
        minimum_institutional_ratio=0.25,
    ),
    DecisionType.ENROLLMENT_PLANNING: EvidenceExpectationProfile(
        decision_type=DecisionType.ENROLLMENT_PLANNING,
        label="Enrollment Planning",
        description=(
            "Enrollment demand, recruitment, retention, graduation, "
            "or enrollment forecasting."
        ),
        topic_keywords={
            "Enrollment Trends": (
                "enrollment",
                "headcount",
                "fte",
                "census",
                "projection",
                "forecast",
            ),
            "Admissions Demand": (
                "admission",
                "applications",
                "yield",
                "prospective",
                "recruitment",
            ),
            "Retention / Graduation": (
                "retention",
                "graduation",
                "completion",
                "persistence",
            ),
            "Student Affordability": (
                "tuition",
                "financial aid",
                "affordability",
                "student debt",
            ),
            "Institutional Capacity": (
                "faculty",
                "housing",
                "capacity",
                "staffing",
                "space",
            ),
        },
        preferred_classes=(
            EvidenceClass.INSTITUTIONAL,
            EvidenceClass.PLANNING,
            EvidenceClass.EXTERNAL_STANDARD,
            EvidenceClass.HISTORICAL,
        ),
        acceptable_external_ratio=0.50,
        minimum_institutional_ratio=0.25,
    ),
    DecisionType.BUDGET_FINANCE: EvidenceExpectationProfile(
        decision_type=DecisionType.BUDGET_FINANCE,
        label="Budget and Finance",
        description=(
            "Funding, tuition, financial aid, appropriations, costs, "
            "or institutional financial planning."
        ),
        topic_keywords={
            "State Funding": (
                "state funding",
                "appropriation",
                "general fund",
                "state support",
            ),
            "Tuition and Fees": (
                "tuition",
                "fees",
                "student charges",
            ),
            "Affordability": (
                "affordability",
                "disposable income",
                "student debt",
                "financial burden",
            ),
            "Financial Aid": (
                "financial aid",
                "grant",
                "scholarship",
                "aid formula",
            ),
            "Institutional Costs": (
                "cost",
                "operating cost",
                "salary increase",
                "inflation",
                "expenditure",
            ),
            "Historical Trends": (
                "trend",
                "historical",
                "since 200",
                "over time",
                "biennium",
            ),
        },
        preferred_classes=(
            EvidenceClass.INSTITUTIONAL,
            EvidenceClass.PLANNING,
            EvidenceClass.EXTERNAL_STANDARD,
            EvidenceClass.HISTORICAL,
        ),
        acceptable_external_ratio=0.85,
        minimum_institutional_ratio=0.00,
    ),
    DecisionType.STATE_POLICY: EvidenceExpectationProfile(
        decision_type=DecisionType.STATE_POLICY,
        label="State Policy Analysis",
        description=(
            "Questions asking what a state agency, legislature, or "
            "statewide policy framework indicates or requires."
        ),
        topic_keywords={
            "State Authority": (
                "schev",
                "commonwealth",
                "general assembly",
                "state council",
            ),
            "Policy or Requirement": (
                "policy",
                "requirement",
                "mandate",
                "appropriation act",
            ),
            "Statewide Evidence": (
                "virginia institutions",
                "statewide",
                "public institutions",
            ),
            "Historical Context": (
                "historical",
                "trend",
                "over time",
                "since 200",
            ),
            "Implementation Status": (
                "approved",
                "implemented",
                "recommendation",
                "proposed",
                "enacted",
            ),
        },
        preferred_classes=(
            EvidenceClass.EXTERNAL_STANDARD,
            EvidenceClass.PLANNING,
            EvidenceClass.HISTORICAL,
            EvidenceClass.INSTITUTIONAL,
        ),
        acceptable_external_ratio=1.00,
        minimum_institutional_ratio=0.00,
    ),
    DecisionType.ACCREDITATION: EvidenceExpectationProfile(
        decision_type=DecisionType.ACCREDITATION,
        label="Accreditation",
        description=(
            "Accreditation requirements, compliance, assessment, "
            "or substantive-change questions."
        ),
        topic_keywords={
            "Accreditation Standard": (
                "accreditation",
                "abet",
                "sacscoc",
                "criterion",
                "standard",
            ),
            "Curriculum": (
                "curriculum",
                "course",
                "credit hours",
                "learning outcomes",
            ),
            "Faculty": (
                "faculty",
                "qualifications",
                "staffing",
            ),
            "Assessment": (
                "assessment",
                "outcomes",
                "continuous improvement",
            ),
            "Facilities / Resources": (
                "facility",
                "equipment",
                "laboratory",
                "resources",
            ),
        },
        preferred_classes=(
            EvidenceClass.EXTERNAL_STANDARD,
            EvidenceClass.INSTITUTIONAL,
            EvidenceClass.PLANNING,
        ),
        acceptable_external_ratio=0.70,
        minimum_institutional_ratio=0.20,
    ),
    DecisionType.STRATEGIC_PLANNING: EvidenceExpectationProfile(
        decision_type=DecisionType.STRATEGIC_PLANNING,
        label="Strategic Planning",
        description=(
            "Institutional strategy, priorities, mission, resource "
            "allocation, or long-range planning."
        ),
        topic_keywords={
            "Mission and Values": (
                "mission",
                "values",
                "strategic compass",
                "priority",
            ),
            "Institutional Conditions": (
                "enrollment",
                "budget",
                "faculty",
                "student",
                "program",
            ),
            "Future Direction": (
                "future",
                "planning",
                "initiative",
                "goal",
                "strategy",
            ),
            "Implementation": (
                "implementation",
                "timeline",
                "responsibility",
                "milestone",
            ),
            "External Context": (
                "schev",
                "state",
                "peer",
                "comparator",
            ),
        },
        preferred_classes=(
            EvidenceClass.CONSTITUTIONAL,
            EvidenceClass.INSTITUTIONAL,
            EvidenceClass.PLANNING,
            EvidenceClass.EXTERNAL_COMPARATOR,
            EvidenceClass.EXTERNAL_STANDARD,
        ),
        acceptable_external_ratio=0.45,
        minimum_institutional_ratio=0.20,
    ),
    DecisionType.GENERAL_INSTITUTIONAL: EvidenceExpectationProfile(
        decision_type=DecisionType.GENERAL_INSTITUTIONAL,
        label="General Institutional Question",
        description=(
            "A broad institutional question that does not yet match "
            "a more specific decision profile."
        ),
        topic_keywords={
            "Institutional Evidence": (
                "cnu",
                "institution",
                "university",
                "current",
            ),
            "Planning": (
                "planning",
                "strategy",
                "proposal",
                "initiative",
            ),
            "Historical Context": (
                "historical",
                "history",
                "previous",
                "trend",
            ),
            "External Context": (
                "state",
                "schev",
                "accreditation",
                "peer",
            ),
        },
        preferred_classes=(
            EvidenceClass.INSTITUTIONAL,
            EvidenceClass.PLANNING,
            EvidenceClass.HISTORICAL,
            EvidenceClass.EXTERNAL_STANDARD,
            EvidenceClass.EXTERNAL_COMPARATOR,
        ),
        acceptable_external_ratio=0.40,
        minimum_institutional_ratio=0.20,
    ),
}


def _source_text(item: Evidence) -> str:
    citation = item.result.citation or {}

    parts = [
        citation.get("title") or "",
        citation.get("relative_path") or "",
        citation.get("source_path") or "",
        item.result.text or "",
    ]

    return " ".join(parts).lower()


class EvidenceFitnessService:
    @classmethod
    def classify_decision_type(
        cls,
        question: str,
    ) -> tuple[DecisionType, float]:
        text = question.casefold()

        rules = [
            (
                DecisionType.ACCREDITATION,
                (
                    "accreditation",
                    "abet",
                    "sacscoc",
                    "substantive change",
                ),
                0.95,
            ),
            (
                DecisionType.BUDGET_FINANCE,
                (
                    "budget",
                    "funding",
                    "tuition",
                    "financial aid",
                    "appropriation",
                    "affordability",
                    "cost",
                ),
                0.90,
            ),
            (
                DecisionType.ENROLLMENT_PLANNING,
                (
                    "enrollment",
                    "recruitment",
                    "retention",
                    "graduation",
                    "admissions",
                    "yield",
                ),
                0.90,
            ),
            (
                DecisionType.ACADEMIC_PROGRAM,
                (
                    "major",
                    "minor",
                    "degree program",
                    "academic program",
                    "curriculum",
                    "program closure",
                ),
                0.90,
            ),
            (
                DecisionType.STATE_POLICY,
                (
                    "schev",
                    "state policy",
                    "general assembly",
                    "commonwealth",
                    "statewide",
                ),
                0.85,
            ),
            (
                DecisionType.STRATEGIC_PLANNING,
                (
                    "strategic",
                    "long-range",
                    "institutional priority",
                    "mission",
                ),
                0.85,
            ),
        ]

        matches = []

        for decision_type, keywords, confidence in rules:
            count = sum(
                1
                for keyword in keywords
                if keyword in text
            )

            if count:
                matches.append(
                    (
                        count,
                        confidence,
                        decision_type,
                    )
                )

        if not matches:
            return (
                DecisionType.GENERAL_INSTITUTIONAL,
                0.50,
            )

        matches.sort(
            key=lambda item: (
                item[0],
                item[1],
            ),
            reverse=True,
        )

        _, confidence, decision_type = matches[0]

        return decision_type, confidence

    @classmethod
    def evaluate(
        cls,
        question: str,
        evidence_items: List[Evidence],
    ) -> EvidenceFitnessAssessment:
        decision_type, confidence = (
            cls.classify_decision_type(question)
        )

        profile = PROFILES[decision_type]

        empirical_items = [
            item
            for item in evidence_items
            if item.evidence_class
            != EvidenceClass.CONSTITUTIONAL
        ]

        empirical_total = len(empirical_items)

        combined_text = "\n".join(
            _source_text(item)
            for item in empirical_items
        )

        covered_topics = []
        missing_topics = []

        for topic, keywords in (
            profile.topic_keywords.items()
        ):
            if any(
                keyword in combined_text
                for keyword in keywords
            ):
                covered_topics.append(topic)
            else:
                missing_topics.append(topic)

        if profile.topic_keywords:
            topic_coverage = (
                100.0
                * len(covered_topics)
                / len(profile.topic_keywords)
            )
        else:
            topic_coverage = 0.0

        class_counts = {
            evidence_class: sum(
                1
                for item in evidence_items
                if item.evidence_class
                == evidence_class
            )
            for evidence_class
            in EvidenceClass
        }

        preferred_count = sum(
            class_counts.get(
                evidence_class,
                0,
            )
            for evidence_class
            in profile.preferred_classes
        )

        evidence_role_fit = (
            100.0
            * preferred_count
            / len(evidence_items)
            if evidence_items
            else 0.0
        )

        institutional_count = (
            class_counts.get(
                EvidenceClass.INSTITUTIONAL,
                0,
            )
        )

        external_count = (
            class_counts.get(
                EvidenceClass.EXTERNAL_STANDARD,
                0,
            )
            + class_counts.get(
                EvidenceClass.EXTERNAL_COMPARATOR,
                0,
            )
        )

        institutional_ratio = (
            institutional_count
            / empirical_total
            if empirical_total
            else 0.0
        )

        external_ratio = (
            external_count
            / empirical_total
            if empirical_total
            else 0.0
        )

        institutional_fit = 100.0

        if (
            profile.minimum_institutional_ratio > 0
            and institutional_ratio
            < profile.minimum_institutional_ratio
        ):
            institutional_fit = (
                100.0
                * institutional_ratio
                / profile.minimum_institutional_ratio
            )

        external_fit = 100.0

        if (
            external_ratio
            > profile.acceptable_external_ratio
        ):
            excess = (
                external_ratio
                - profile.acceptable_external_ratio
            )

            remaining = max(
                0.01,
                1.0
                - profile.acceptable_external_ratio
            )

            external_fit = max(
                0.0,
                100.0
                * (1.0 - excess / remaining),
            )

        authority_fit = (
            0.65 * institutional_fit
            + 0.35 * external_fit
        )

        fitness_score = (
            0.50 * topic_coverage
            + 0.25 * authority_fit
            + 0.25 * evidence_role_fit
        )

        strengths = []
        weaknesses = []
        recommendations = []

        if topic_coverage >= 75:
            strengths.append(
                "Retrieved evidence covers most expected "
                "domains for this decision type."
            )

        if evidence_role_fit >= 75:
            strengths.append(
                "Most retrieved sources have evidence roles "
                "appropriate to the question."
            )

        if authority_fit >= 75:
            strengths.append(
                "The authority mix is appropriate for this "
                "decision type."
            )

        if missing_topics:
            weaknesses.append(
                "Material evidence gaps remain: "
                + ", ".join(missing_topics)
                + "."
            )

            recommendations.append(
                "Acquire or retrieve evidence for: "
                + ", ".join(missing_topics)
                + "."
            )

        if (
            institutional_ratio
            < profile.minimum_institutional_ratio
        ):
            weaknesses.append(
                "The evidence set contains less direct "
                "institutional evidence than expected."
            )

            recommendations.append(
                "Retrieve current institutional records "
                "relevant to this decision."
            )

        if (
            external_ratio
            > profile.acceptable_external_ratio
        ):
            weaknesses.append(
                "External evidence exceeds the expected share "
                "for this decision type."
            )

        return EvidenceFitnessAssessment(
            decision_type=decision_type,
            decision_type_label=profile.label,
            decision_type_confidence=round(
                confidence,
                3,
            ),
            fitness_score=round(
                max(0.0, min(100.0, fitness_score)),
                1,
            ),
            topic_coverage_score=round(
                topic_coverage,
                1,
            ),
            authority_fit_score=round(
                authority_fit,
                1,
            ),
            evidence_role_fit_score=round(
                evidence_role_fit,
                1,
            ),
            covered_topics=covered_topics,
            missing_topics=missing_topics,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
        )
