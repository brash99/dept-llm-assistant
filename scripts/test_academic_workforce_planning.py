import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.observatory.evidence_fitness import (
    ACADEMIC_WORKFORCE_PLANNING_TOPICS,
    PROFILES,
    DecisionType,
    EvidenceFitnessService,
)


CANONICAL_BENCHMARK = (
    "Christopher Newport University currently employs approximately "
    "275 faculty members. Suppose the university needed to reduce that "
    "number to 250 over the next several years. Which departments should "
    "those 25 faculty reductions come from, and why?"
)

HEALTH_PHYSICS_BENCHMARK = (
    "Should CNU develop a Health Physics academic program as part of "
    "its strategic planning?"
)


EXPECTED_DOMAINS = [
    "Instructional Demand",
    "Faculty Capacity",
    "Service Teaching Dependence",
    "Accreditation and External Constraints",
    "Enrollment Trends",
    "Financial Implications",
    "Strategic Priority Alignment",
    "One-Line Loss Scenario",
]


def main() -> None:
    decision_type, confidence = (
        EvidenceFitnessService.classify_decision_type(
            CANONICAL_BENCHMARK
        )
    )

    assert decision_type == (
        DecisionType.ACADEMIC_WORKFORCE_PLANNING
    ), (
        "Canonical benchmark was classified as "
        f"{decision_type.value!r}, not Academic Workforce Planning."
    )

    assert confidence >= 0.95, (
        f"Unexpectedly low classification confidence: {confidence}"
    )

    profile = PROFILES[
        DecisionType.ACADEMIC_WORKFORCE_PLANNING
    ]

    assert profile.label == "Academic Workforce Planning"
    assert list(profile.topic_keywords) == EXPECTED_DOMAINS
    assert list(
        ACADEMIC_WORKFORCE_PLANNING_TOPICS
    ) == EXPECTED_DOMAINS

    # Guard against collisions with other established decision types.
    classification_cases = {
        HEALTH_PHYSICS_BENCHMARK: DecisionType.ACADEMIC_PROGRAM,
        (
            "Should CNU create a new mechanical engineering "
            "degree program?"
        ): DecisionType.ACADEMIC_PROGRAM,
        (
            "Should CNU evaluate the Chemistry major for continuation?"
        ): DecisionType.ACADEMIC_PROGRAM,
        (
            "Should CNU expand the Data Science minor?"
        ): DecisionType.ACADEMIC_PROGRAM,
        (
            "Should CNU close the existing certificate program?"
        ): DecisionType.ACADEMIC_PROGRAM,
        (
            "What do recent SCHEV reports indicate about "
            "state enrollment policy?"
        ): DecisionType.STATE_POLICY,
        (
            "How have undergraduate enrollment and retention "
            "changed over five years?"
        ): DecisionType.ENROLLMENT_PLANNING,
        (
            "What accreditation requirements apply to the "
            "engineering program?"
        ): DecisionType.ACCREDITATION,
        (
            "How should the university reduce faculty positions "
            "across departments?"
        ): DecisionType.ACADEMIC_WORKFORCE_PLANNING,
        (
            "What happens if one faculty line is removed from "
            "the Physics department?"
        ): DecisionType.ACADEMIC_WORKFORCE_PLANNING,
        (
            "How should CNU revise its institutional strategic plan?"
        ): DecisionType.STRATEGIC_PLANNING,
    }

    for question, expected in classification_cases.items():
        actual, _ = EvidenceFitnessService.classify_decision_type(
            question
        )
        assert actual == expected, (
            f"{question!r} classified as {actual.value!r}; "
            f"expected {expected.value!r}."
        )

    readiness = EvidenceFitnessService.evaluate(
        question=CANONICAL_BENCHMARK,
        evidence_items=[],
    )

    health_physics_readiness = EvidenceFitnessService.evaluate(
        question=HEALTH_PHYSICS_BENCHMARK,
        evidence_items=[],
    )

    assert health_physics_readiness.decision_type == (
        DecisionType.ACADEMIC_PROGRAM
    )
    assert list(health_physics_readiness.topic_grades) == list(
        PROFILES[DecisionType.ACADEMIC_PROGRAM].topic_keywords
    )

    assert readiness.decision_type == (
        DecisionType.ACADEMIC_WORKFORCE_PLANNING
    )

    assert list(readiness.topic_grades) == EXPECTED_DOMAINS
    assert all(
        grade == "missing"
        for grade in readiness.topic_grades.values()
    )
    assert readiness.fitness_score < 50.0, (
        "An empty evidence collection should not be assessed as "
        f"decision-ready: {readiness.fitness_score}"
    )

    print("PASS: Academic Workforce Planning decision type")
    print("PASS: Academic Workforce Planning readiness registry")
    print(f"Canonical confidence: {confidence:.2f}")
    print(
        "Empty-evidence fitness score: "
        f"{readiness.fitness_score:.1f}"
    )
    print("Evidence domains:")
    for number, domain in enumerate(EXPECTED_DOMAINS, start=1):
        print(f"  {number}. {domain}")


if __name__ == "__main__":
    main()
