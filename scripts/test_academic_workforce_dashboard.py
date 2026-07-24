from __future__ import annotations


from app.observatory.decision_brief.dashboard_v2 import (
    ExecutiveDashboardV2,
)
from app.observatory.decision_brief.dashboard_v2.contracts import (
    ACADEMIC_WORKFORCE_PLANNING_DOMAINS,
)
from app.observatory.decision_brief.dashboard_v2.workforce import (
    WorkforceDecisionFrameworkPanel,
)
from app.observatory.evidence_fitness import (
    ACADEMIC_WORKFORCE_PLANNING_TOPICS,
    DecisionType,
    EvidenceFitnessAssessment,
)


def _make_assessment(
    decision_type: DecisionType | str,
) -> EvidenceFitnessAssessment:
    domains = list(ACADEMIC_WORKFORCE_PLANNING_TOPICS)
    grades = ("strong", "partial", "weak", "missing")

    return EvidenceFitnessAssessment(
        decision_type=decision_type,
        decision_type_label="Academic Workforce Planning",
        decision_type_confidence=0.99,
        fitness_score=50.0,
        topic_coverage_score=50.0,
        authority_fit_score=50.0,
        evidence_role_fit_score=50.0,
        topic_grades={
            domain: grades[index % len(grades)]
            for index, domain in enumerate(domains)
        },
        topic_support={
            domain: {
                "score": index / 10.0,
                "sources": index,
                "keywords": index + 1,
            }
            for index, domain in enumerate(domains)
        },
    )


def test_workforce_panel_renders_all_canonical_domains() -> None:
    markdown = WorkforceDecisionFrameworkPanel().render(
        evidence_fitness=_make_assessment(
            DecisionType.ACADEMIC_WORKFORCE_PLANNING
        ),
    )

    assert "## Executive Workforce Decision Framework" in markdown
    assert "does not recommend departmental position reductions" in markdown

    positions = [
        markdown.index(f"| {domain} |")
        for domain in ACADEMIC_WORKFORCE_PLANNING_DOMAINS
    ]
    assert positions == sorted(positions)
    assert len(positions) == 8

    assert "| Instructional Demand | ✓ Strong | 0%; 0 sources; 1 keyword concept" in markdown
    assert "| Faculty Capacity | ⚠ Partial | 10%; 1 source; 2 keyword concepts" in markdown
    assert "Additional corroborating evidence to reach strong support." in markdown
    assert "Additional direct sources and broader evidence coverage." in markdown
    assert "Direct evidence for this domain." in markdown


def test_local_domains_match_authoritative_taxonomy() -> None:
    assert ACADEMIC_WORKFORCE_PLANNING_DOMAINS == tuple(
        ACADEMIC_WORKFORCE_PLANNING_TOPICS
    )


def test_panel_accepts_string_decision_type() -> None:
    markdown = WorkforceDecisionFrameworkPanel().render(
        evidence_fitness=_make_assessment(
            "academic_workforce_planning"
        )
    )

    assert "Executive Workforce Decision Framework" in markdown


def test_dashboard_includes_panel_only_for_workforce_planning() -> None:
    dashboard = ExecutiveDashboardV2()
    workforce_markdown = dashboard.render(
        question="How should academic staffing be reduced?",
        evidence_fitness=_make_assessment(
            DecisionType.ACADEMIC_WORKFORCE_PLANNING
        ),
    )
    program_markdown = dashboard.render(
        question="Should the university create a new program?",
        evidence_fitness=_make_assessment(
            DecisionType.ACADEMIC_PROGRAM
        ),
    )

    assert "Executive Workforce Decision Framework" in workforce_markdown
    assert "Executive Workforce Decision Framework" not in program_markdown
