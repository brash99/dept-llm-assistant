from __future__ import annotations

from app.observatory.decision_readiness.base import (
    DomainEvaluatorSpec,
)
from app.observatory.decision_readiness.evaluators.keyword import (
    KeywordDomainEvaluator,
)
from app.observatory.evidence_fitness import (
    ACADEMIC_WORKFORCE_PLANNING_TOPICS,
)


def _build_evaluator(
    name: str,
    *,
    required_evidence: tuple[str, ...],
) -> KeywordDomainEvaluator:
    """
    Build a deterministic evaluator from the canonical Academic Workforce
    Planning topic taxonomy.

    The evidence profile remains the single source of truth for domain names
    and retrieval keywords. Decision Readiness adds explicit statements of
    the evidence required to support an executive staffing decision.
    """
    return KeywordDomainEvaluator(
        DomainEvaluatorSpec(
            name=name,
            keywords=ACADEMIC_WORKFORCE_PLANNING_TOPICS[name],
            required_evidence=required_evidence,
        )
    )


InstructionalDemandEvaluator = _build_evaluator(
    "Instructional Demand",
    required_evidence=(
        "Department-level student credit-hour production.",
        "Course-section enrollments and class-size distributions.",
        "Teaching-load and instructional-workload data.",
    ),
)

FacultyCapacityEvaluator = _build_evaluator(
    "Faculty Capacity",
    required_evidence=(
        "Current faculty headcount and FTE by department.",
        "Faculty teaching assignments and normal teaching loads.",
        "Adjunct, overload, vacancy, retirement, and attrition data.",
    ),
)

ServiceTeachingDependenceEvaluator = _build_evaluator(
    "Service Teaching Dependence",
    required_evidence=(
        "Department-level service-course enrollments.",
        "General education and cross-program course dependencies.",
        "Non-major enrollment and prerequisite dependency data.",
    ),
)

AccreditationExternalConstraintsEvaluator = _build_evaluator(
    "Accreditation and External Constraints",
    required_evidence=(
        "Program-specific accreditation and licensure requirements.",
        "Minimum faculty-count or faculty-qualification requirements.",
        "External regulatory constraints affecting staffing.",
    ),
)

EnrollmentTrendsEvaluator = _build_evaluator(
    "Enrollment Trends",
    required_evidence=(
        "Multi-year major enrollment by department or program.",
        "Multi-year degree-completion and graduation data.",
        "Relevant application, yield, retention, and demand trends.",
    ),
)

FinancialImplicationsEvaluator = _build_evaluator(
    "Financial Implications",
    required_evidence=(
        "Department-level instructional cost information.",
        "Faculty compensation and projected savings assumptions.",
        "Relevant tuition, revenue, and resource-allocation effects.",
    ),
)

StrategicPriorityAlignmentEvaluator = _build_evaluator(
    "Strategic Priority Alignment",
    required_evidence=(
        "Authoritative institutional strategic priorities.",
        "Evidence connecting departments to mission-critical functions.",
        "Relevant state, regional, or workforce priorities.",
    ),
)

OneLineLossScenarioEvaluator = _build_evaluator(
    "One-Line Loss Scenario",
    required_evidence=(
        "Course coverage after removal of one faculty position.",
        "Effects on schedules, required courses, and program viability.",
        "Department-specific expertise, succession, and replacement risks.",
    ),
)


ACADEMIC_WORKFORCE_PLANNING_EVALUATORS = [
    InstructionalDemandEvaluator,
    FacultyCapacityEvaluator,
    ServiceTeachingDependenceEvaluator,
    AccreditationExternalConstraintsEvaluator,
    EnrollmentTrendsEvaluator,
    FinancialImplicationsEvaluator,
    StrategicPriorityAlignmentEvaluator,
    OneLineLossScenarioEvaluator,
]


__all__ = [
    "InstructionalDemandEvaluator",
    "FacultyCapacityEvaluator",
    "ServiceTeachingDependenceEvaluator",
    "AccreditationExternalConstraintsEvaluator",
    "EnrollmentTrendsEvaluator",
    "FinancialImplicationsEvaluator",
    "StrategicPriorityAlignmentEvaluator",
    "OneLineLossScenarioEvaluator",
    "ACADEMIC_WORKFORCE_PLANNING_EVALUATORS",
]
