import sys
import types
from types import SimpleNamespace


try:
    import faiss  # noqa: F401
except (ImportError, OSError):
    sys.modules["faiss"] = types.ModuleType("faiss")

try:
    import sentence_transformers  # noqa: F401
except (ImportError, OSError):
    sentence_transformers = types.ModuleType(
        "sentence_transformers"
    )
    sentence_transformers.SentenceTransformer = object
    sentence_transformers.CrossEncoder = object
    sys.modules["sentence_transformers"] = sentence_transformers


from app.observatory.decision_brief.dashboard_v2 import ExecutiveDashboardV2
from app.observatory.decision_brief.dashboard_v2.contracts import (
    ACADEMIC_WORKFORCE_PLANNING_DOMAINS,
)
from app.observatory.decision_brief.dashboard_v2.evidence_map import (
    ACADEMIC_WORKFORCE_EVIDENCE_MAP,
    AcademicWorkforceEvidenceMapPanel,
)
from app.observatory.evidence_fitness import (
    ACADEMIC_WORKFORCE_PLANNING_TOPICS,
)


def _assessment(
    decision_type="academic_workforce_planning",
    *,
    topic_grades=None,
    topic_support=None,
):
    return SimpleNamespace(
        decision_type=decision_type,
        topic_grades=topic_grades or {},
        topic_support=topic_support or {},
    )


def test_evidence_map_renders_canonical_domains_and_support() -> None:
    domains = ACADEMIC_WORKFORCE_PLANNING_DOMAINS
    assessment = _assessment(
        topic_grades={
            domains[0]: "partial",
            domains[1]: "strong",
        },
        topic_support={
            domains[0]: {
                "score": 0.64,
                "sources": 2,
                "keywords": 3,
            },
            domains[1]: {
                "score": 0.82,
                "sources": 1,
                "keywords": 1,
            },
        },
    )

    markdown = AcademicWorkforceEvidenceMapPanel().render(assessment)

    assert "## Academic Workforce Evidence Map" in markdown
    positions = [markdown.index(f"### {domain}") for domain in domains]
    assert positions == sorted(positions)
    assert len(positions) == 8
    assert "⚠ Partial; 64%" in markdown
    assert "2 supporting sources; 3 keyword concepts" in markdown
    assert "✓ Strong; 82%" in markdown
    assert "1 supporting source; 1 keyword concept" in markdown
    assert "Current corpus support is strong" in markdown
    assert "confirm recency, unit-level coverage" in markdown
    assert "decision-specific completeness" in markdown
    assert "no additional evidence" not in markdown.casefold()


def test_evidence_map_contains_deterministic_relevance_and_disclaimer() -> None:
    markdown = AcademicWorkforceEvidenceMapPanel().render(_assessment())

    for metadata in ACADEMIC_WORKFORCE_EVIDENCE_MAP.values():
        assert metadata["relevance"] in markdown

    assert "does not determine which departments should lose positions" in markdown
    assert "strategic priorities" in markdown
    assert "accreditation obligations" in markdown
    assert "institutional mission" in markdown
    assert "human judgment" in markdown


def test_missing_and_partial_support_are_rendered_without_invention() -> None:
    domains = ACADEMIC_WORKFORCE_PLANNING_DOMAINS
    markdown = AcademicWorkforceEvidenceMapPanel().render(
        _assessment(
            topic_grades={domains[0]: "partial"},
            topic_support={domains[0]: {"sources": 1}},
        )
    )

    assert "Partial; score unavailable" in markdown
    assert "1 supporting source" in markdown
    assert "No support details reported." in markdown
    assert "Additional corroboration or coverage:" in markdown


def test_evidence_map_does_not_render_for_other_decision_type() -> None:
    markdown = AcademicWorkforceEvidenceMapPanel().render(
        _assessment(decision_type="academic_program")
    )

    assert markdown == ""


def test_evidence_map_taxonomy_matches_evidence_fitness() -> None:
    authoritative = tuple(ACADEMIC_WORKFORCE_PLANNING_TOPICS)

    assert ACADEMIC_WORKFORCE_PLANNING_DOMAINS == authoritative
    assert tuple(ACADEMIC_WORKFORCE_EVIDENCE_MAP) == authoritative


def test_dashboard_places_evidence_map_after_workforce_framework() -> None:
    workforce = ExecutiveDashboardV2().render(
        question="How should academic staffing be reduced?",
        evidence_fitness=_assessment(),
    )
    other = ExecutiveDashboardV2().render(
        question="Should a new program be created?",
        evidence_fitness=_assessment(decision_type="academic_program"),
    )

    framework_position = workforce.index(
        "## Executive Workforce Decision Framework"
    )
    map_position = workforce.index("## Academic Workforce Evidence Map")

    assert framework_position < map_position
    assert "Academic Workforce Evidence Map" not in other
