import sys
import types
from pathlib import Path

import pytest


try:
    import faiss  # noqa: F401
except (ImportError, OSError):
    sys.modules["faiss"] = types.ModuleType("faiss")

try:
    import sentence_transformers  # noqa: F401
except (ImportError, OSError):
    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = object
    module.CrossEncoder = object
    sys.modules["sentence_transformers"] = module


from app.control_plane.catalog import ProgramCatalog
from app.control_plane.orientation import ProgramOrientationService
from app.control_plane.resolver import ProgramResolver
from app.constitution.orientation import (
    ConstitutionalOrientation,
    ConstitutionalPrincipleMatch,
)
from app.document_family import document_family_key
from app.evidence import EvidenceClass, evidence_role_label, make_evidence
from app.observatory.decision_brief.service import (
    build_decision_brief_prompt,
    build_grouped_evidence_context,
    build_constitutional_orientation_context,
    resolve_topology_entity,
)
from app.observatory.decision_brief.dashboard_v2.participation import (
    InstitutionalParticipationProfilePanel,
)
from app.observatory.decision_brief.dashboard_v2.workforce import (
    WorkforceDecisionFrameworkPanel,
)
from app.observatory.decision_brief.dashboard_v2.evidence_map import (
    AcademicWorkforceEvidenceMapPanel,
)
from app.observatory.evidence_fitness import EvidenceFitnessService
from app.observatory.topology.bootstrap import build_bootstrap_catalog
from app.observatory.topology.entity import EntityType, InstitutionalEntity
from app.observatory.topology.impact import ImpactSummary
from app.question_scope import QuestionScope, classify_question_scope
from app.retrieval import (
    RetrievalProfile,
    RetrievalReport,
    RetrievalTrace,
    diversify_document_families,
)
import app.retrieval as retrieval_module
from app.source_presentation import executive_source_label
from app.vector_index import RetrievalResult
import app.decision_brief as decision_brief_entrypoint
import app.observatory.decision_brief.service as decision_brief_service


QUENTIN_QUESTION = (
    "CNU currently employs approximately 275 full-time faculty members. "
    "Suppose the university determines that this number must be reduced to "
    "approximately 250 through attrition. Which departments should those 25 "
    "faculty reductions come from, and why is that appropriate? Liberal "
    "Learning Core obligations remain relevant."
)

HEALTH_PHYSICS_BENCHMARK = """Prepare an Institutional Decision Brief addressing the following question.

Institutional Question

Christopher Newport University has been approached about the possibility of developing a Health Physics academic program. Evaluate whether pursuing such a program would be strategically advisable for the university.

Your analysis should be based only on available institutional evidence and relevant external evidence. Consider, where supported by the evidence:

• Alignment with Christopher Newport University's mission, Strategic Compass, and institutional priorities.
• Existing academic strengths that could support such a program.
• Student demand and enrollment considerations.
• Workforce demand and regional or national employment outlook.
• Potential partnerships (for example, Jefferson Lab, regional healthcare organizations, government agencies, or industry), but only where supported by evidence.
• Resource requirements, including faculty expertise, facilities, accreditation, laboratory needs, and long-term sustainability.
• Financial opportunities and risks.
• Significant uncertainties, missing evidence, or assumptions that limit the analysis.

If the available evidence is insufficient to support a confident recommendation, explicitly identify the missing evidence rather than speculating.

Produce a complete Institutional Decision Brief using the Observatory's standard format, including Evidence Fitness, constitutional alignment, and a clearly justified recommendation."""


class _NoNeighbors:
    def neighbors(self, **kwargs):
        return []


def _constitutional_orientation(question: str) -> ConstitutionalOrientation:
    match = ConstitutionalPrincipleMatch(
        constitutional_object_id="strategic-compass",
        constitutional_object_title="Strategic Compass",
        constitutional_type="strategic_compass",
        principle=(
            "advance the power and promise of an education embedded in "
            "the liberal arts"
        ),
        score=0.4,
        matched_terms=("academic", "program"),
    )
    return ConstitutionalOrientation(
        question=question,
        matches=(match,),
        confidence=0.4,
    )


def test_health_physics_preserves_existing_and_proposed_semantics() -> None:
    catalog = ProgramCatalog.from_yaml(
        Path("config/institutional_programs.yaml")
    )
    orientation = ProgramOrientationService(
        resolver=ProgramResolver(catalog),
        neighborhood_service=_NoNeighbors(),
    ).orient(HEALTH_PHYSICS_BENCHMARK)

    assert [entity.name for entity in orientation.resolved_entities] == [
        "Physics"
    ]
    assert [
        (concept.name, concept.concept_type)
        for concept in orientation.proposed_concepts
    ] == [("Health Physics", "academic_program")]

    decision_type, _ = EvidenceFitnessService.classify_decision_type(
        HEALTH_PHYSICS_BENCHMARK
    )
    assert decision_type.value == "academic_program"


def test_health_physics_orientation_reaches_narrative_prompt() -> None:
    orientation = _constitutional_orientation(HEALTH_PHYSICS_BENCHMARK)
    evidence_context = build_grouped_evidence_context(
        [],
        constitutional_orientation=orientation,
    )
    orientation_context = build_constitutional_orientation_context(
        orientation
    )
    evidence_fitness = EvidenceFitnessService.evaluate(
        HEALTH_PHYSICS_BENCHMARK,
        [],
    )
    prompt = build_decision_brief_prompt(
        HEALTH_PHYSICS_BENCHMARK,
        evidence_context,
        evidence_fitness=evidence_fitness,
        constitutional_orientation_context=orientation_context,
    )

    assert evidence_fitness.decision_type.value == "academic_program"
    assert orientation.matches
    assert "Strategic Compass" not in evidence_context
    assert "Strategic Compass" in orientation_context
    assert "Deterministic Constitutional Orientation" in prompt
    assert "Strategic Compass" in prompt
    assert "No constitutional evidence was retrieved." not in prompt
    assert "not a retrieved empirical source" in prompt
    normalized_prompt = " ".join(prompt.split())
    assert (
        "do not say that no constitutional evidence or orientation was "
        "available"
    ) in normalized_prompt


def test_health_physics_complete_decision_brief_pipeline(
    monkeypatch,
) -> None:
    orientation = _constitutional_orientation(HEALTH_PHYSICS_BENCHMARK)
    captured = {}

    class _Completions:
        def create(self, **kwargs):
            captured["prompt"] = kwargs["messages"][0]["content"]
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message=types.SimpleNamespace(
                            content=(
                                "# Decision Brief\n\n"
                                "Constitutional orientation was supplied "
                                "separately from empirical evidence."
                            )
                        )
                    )
                ]
            )

    class _OpenAI:
        def __init__(self, **kwargs):
            self.chat = types.SimpleNamespace(
                completions=_Completions()
            )

    monkeypatch.setattr(
        decision_brief_entrypoint,
        "retrieve",
        lambda **kwargs: ([], None, None),
    )
    monkeypatch.setattr(
        decision_brief_service,
        "OpenAI",
        _OpenAI,
    )

    brief, results, profile = (
        decision_brief_entrypoint.generate_decision_brief(
            question=HEALTH_PHYSICS_BENCHMARK,
            vector_db_dir=Path("unused-test-index"),
            model_name="unused-test-model",
            embedding_device="cpu",
            llm_base_url="http://unused.test/v1",
            llm_model="test-model",
            constitutional_orientation=orientation,
        )
    )

    assert results == []
    assert profile is None
    assert brief.evidence_fitness.decision_type.value == "academic_program"
    assert "# Decision Brief" in brief.raw_markdown
    assert HEALTH_PHYSICS_BENCHMARK in brief.raw_markdown

    prompt = captured["prompt"]
    assert "Deterministic Constitutional Orientation" in prompt
    assert "Strategic Compass" in prompt
    assert "No constitutional evidence was retrieved." not in prompt
    assert "not a retrieved empirical source" in prompt


def _result(path: str, text: str, score: float = 1.0) -> RetrievalResult:
    return RetrievalResult(
        score=score,
        chunk_id=path + ":0",
        knowledge_object_id=path,
        object_type="document",
        chunk_index=0,
        text=text,
        citation={"title": Path(path).stem, "relative_path": path},
        metadata={},
    )


def test_high_risk_program_aliases_require_case_and_academic_context() -> None:
    resolver = ProgramResolver(
        ProgramCatalog.from_yaml(Path("config/institutional_programs.yaml"))
    )
    assert not resolver.resolve("Why is that appropriate?").found
    assert not resolver.resolve("IS especially important here?").found
    assert resolver.resolve("Review the IS program.").program.name == "Information Science"
    assert resolver.resolve("students majoring in IS need advising").program.name == "Information Science"
    assert resolver.resolve("Review the Information Science major.").program.name == "Information Science"
    assert resolver.resolve("Review Computer Science.").program.name == "Computer Science"


def test_scope_classifier_and_topology_selection_are_comparison_safe() -> None:
    assert classify_question_scope(QUENTIN_QUESTION).scope == QuestionScope.INSTITUTION_WIDE
    assert classify_question_scope("Assess the Physics Department").scope == QuestionScope.SINGLE_ENTITY
    assert classify_question_scope("Compare Physics and Chemistry").scope == QuestionScope.MULTI_ENTITY
    catalog = build_bootstrap_catalog()
    assert resolve_topology_entity(QUENTIN_QUESTION, catalog) is None
    assert resolve_topology_entity("Assess the Physics Department", catalog).name == "Physics"

    fitness = types.SimpleNamespace(
        decision_type="academic_workforce_planning",
        question_scope="institution_wide",
        question_scope_label="Institution-Wide Academic Workforce Planning",
        topic_grades={},
        topic_support={},
    )
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=fitness
    )
    assert "comparative multi-unit analysis required" in markdown
    assert "Unit-level participation profiles are not yet available" in markdown


def test_document_family_variants_diversify_without_collapsing_criteria() -> None:
    variants = [
        _result("ABET/Criterion 5 FinalDraft V03 2024-03-01.pdf", "a", 0.9),
        _result("ABET/Criterion 5 Final V04 2024-04-01.docx", "b", 0.8),
        _result("ABET/Criterion 6 Draft V03.pdf", "c", 0.7),
        _result("Reports/Physics Annual Report.pdf", "d", 0.6),
        _result("Reports/Chemistry Annual Report.pdf", "e", 0.5),
    ]
    assert document_family_key(variants[0]) == document_family_key(variants[1])
    assert document_family_key(variants[0]) != document_family_key(variants[2])
    kept, removed = diversify_document_families(variants, max_per_family=1)
    assert kept[0] is variants[0]
    assert variants[1] in removed
    assert variants[2] in kept
    assert variants[3] in kept and variants[4] in kept
    kept_two, removed_two = diversify_document_families(variants, max_per_family=2)
    assert not removed_two
    assert len(kept_two) == len(variants)


def test_production_abet_titles_form_stable_semantic_families() -> None:
    criterion_8_a = _result("ABET/08_Criterion_8_InstSupport_Final.pdf", "a")
    criterion_8_b = _result("ABET/Criterion_8_InstSupport_FinalDraft.docx", "b")
    generic_a = _result("ABET/ABET Self-Study Report.pdf", "c")
    generic_b = _result("ABET/ABET_SelfStudy_V04.pdf", "d")
    ce_a = _result("ABET/SelfStudyReport_CE_All_In_One.pdf", "e")
    ce_b = _result("ABET/CE_SelfStudyReport_2021.pdf", "f")
    ee = _result("ABET/EE_ABET_SelfStudy.pdf", "g")
    criterion_6 = _result("ABET/06_Criterion_6_Faculty_ECE.pdf", "h")

    assert document_family_key(criterion_8_a) == document_family_key(criterion_8_b)
    assert document_family_key(generic_a) == document_family_key(generic_b)
    assert document_family_key(ce_a) == document_family_key(ce_b)
    assert document_family_key(ce_a) != document_family_key(ee)
    assert document_family_key(criterion_8_a) != document_family_key(criterion_6)


def test_self_studies_are_institutional_but_formal_criteria_remain_external() -> None:
    results = [
        _result("ABET/ABET Self-Study Report.pdf", "local accreditation narrative"),
        _result("ABET/08_Criterion_8_InstSupport_Final.pdf", "local response"),
        _result(
            "raw_web/abet_standards/2025 Criteria for Accrediting Engineering Programs.pdf",
            "formal accreditation criteria",
        ),
        _result("ABET/Purdue ABET Self-Study Sample.pdf", "peer example"),
        _result("ABET/ABET Criterion 5 Curriculum.pdf", "formal criterion text"),
    ]
    evidence = make_evidence(results)

    assert evidence[0].evidence_class == EvidenceClass.INSTITUTIONAL
    assert evidence_role_label(evidence[0]) == "Institutional Self-Study"
    assert evidence[1].evidence_class == EvidenceClass.INSTITUTIONAL
    assert evidence_role_label(evidence[1]) == "Institutional Self-Study"
    assert evidence[2].evidence_class == EvidenceClass.EXTERNAL_STANDARD
    assert evidence_role_label(evidence[2]) == "Formal External Standard"
    assert evidence[3].evidence_class == EvidenceClass.EXTERNAL_COMPARATOR
    assert evidence[4].evidence_class == EvidenceClass.EXTERNAL_STANDARD


def test_retrieval_family_diagnostics_are_accurate(monkeypatch: pytest.MonkeyPatch) -> None:
    candidates = [
        _result("ABET/Criterion 5 Final V03.pdf", "a", 0.9),
        _result("ABET/Criterion 5 Draft V04.pdf", "b", 0.8),
        _result("CNU/Physics Annual Report.pdf", "c", 0.7),
    ]
    monkeypatch.setattr(
        retrieval_module,
        "search_index",
        lambda **kwargs: list(candidates),
    )
    results, report, trace, _profile = retrieval_module.retrieve(
        query="faculty capacity",
        vector_db_dir="unused",
        model_name="unused",
        fetch_k=3,
        dedupe_by=None,
        rerank=False,
        return_trace=True,
        constitutional_top_k=0,
        empirical_top_k=3,
        max_per_document_family=1,
    )
    assert len(results) == 2
    assert report.num_after_rerank == 3
    assert report.num_after_family_diversity == 2
    assert report.num_removed_by_family_diversity == 1
    assert report.max_per_document_family == 1
    assert trace.family_removed_candidates[0].citation["relative_path"].endswith("V04.pdf")
    assert all(item.metadata.get("document_family_key") for item in results)


def test_retrieval_contracts_preserve_legacy_constructor_defaults() -> None:
    profile = RetrievalProfile(1.0, 0.2, 0.2, 0.3, 0.3)
    trace = RetrievalTrace([], [], [], [], [])
    report = RetrievalReport(
        "query", 12, 200, "relative_path", 2, 10, 2, 10, False,
        200, 100, 100, 12, 12,
    )

    assert profile.family_diversity_seconds == 0.0
    assert trace.family_diversified_candidates == []
    assert trace.family_removed_candidates == []
    assert trace.allocation_removed_candidates == []
    assert report.max_per_document_family is None
    assert report.num_after_family_diversity == 0
    assert report.num_removed_by_family_diversity == 0
    assert report.num_removed_by_evidence_allocation == 0


def test_institution_wide_fitness_does_not_inflate_narrow_source_families() -> None:
    results = [
        _result(
            "CNU/PCSE Department Annual Report.pdf",
            "The department has 12 faculty members, faculty lines, teaching load, "
            "a budget for travel, and financial resources.",
        ),
        *[
            _result(
                f"ABET/Program Self-Study Final V0{version}.pdf",
                "The self-study discusses ABET accreditation, faculty qualifications, "
                "institutional support, and financial resources.",
            )
            for version in range(3, 7)
        ],
        _result(
            "CNU/Strategic Compass.pdf",
            "The Strategic Compass describes institutional mission, student success, "
            "and strategic financial sustainability.",
        ),
    ]
    assessment = EvidenceFitnessService.evaluate(QUENTIN_QUESTION, make_evidence(results))
    assert assessment.question_scope == "institution_wide"
    assert assessment.topic_grades["Faculty Capacity"] != "strong"
    assert assessment.topic_grades["Financial Implications"] != "strong"
    assert assessment.topic_grades["Instructional Demand"] == "missing"
    assert assessment.topic_grades["Enrollment Trends"] == "missing"
    accreditation = assessment.topic_support["Accreditation and External Constraints"]
    assert accreditation["unique_document_families"] == 1
    assert "current unit-level compliance" in accreditation["scope_limitation"]
    framework = WorkforceDecisionFrameworkPanel().render(assessment)
    evidence_map = AcademicWorkforceEvidenceMapPanel().render(assessment)
    assert "Evidence is direct but limited to one academic unit" in framework
    assert "no decision-specific cost evidence" in evidence_map
    assert "No additional evidence" not in framework


def test_enrollment_snapshot_is_not_graded_as_a_trend() -> None:
    snapshot = make_evidence([
        _result(
            "CNU/PCSE Program Review.pdf",
            "Major enrollment was 533 students in 2021. Six percent were "
            "out-of-state and many transferred from community colleges.",
        ),
        _result(
            "CNU/PCSE Demographic Profile.pdf",
            "The majors include in-state and out-of-state students in 2021.",
        ),
    ])
    assessment = EvidenceFitnessService.evaluate(QUENTIN_QUESTION, snapshot)
    assert assessment.topic_grades["Enrollment Trends"] == "weak"
    support = assessment.topic_support["Enrollment Trends"]
    assert support["score"] <= 0.30
    assert "snapshot or demographic context" in support["scope_limitation"]


def test_multi_year_enrollment_evidence_can_be_partial() -> None:
    temporal = make_evidence([
        _result(
            "CNU/PCSE Multi-Year Enrollment.pdf",
            "Major enrollment changed from 420 students in 2019 to 533 students "
            "in 2021, with year-over-year completion data.",
        ),
    ])
    assessment = EvidenceFitnessService.evaluate(QUENTIN_QUESTION, temporal)
    assert assessment.topic_grades["Enrollment Trends"] == "partial"
    assert (
        assessment.topic_support["Enrollment Trends"]["directness"]
        == "direct temporal enrollment evidence"
    )


def _impact(incoming: int, outgoing: int) -> ImpactSummary:
    entity = InstitutionalEntity("entity.test", "Test Unit", EntityType.DEPARTMENT)
    return ImpactSummary(
        entity=entity,
        supports=("Program",) if outgoing else (),
        contributes_to=(),
        supported_by=("College",) if incoming else (),
        contributed_to_by=(),
        outgoing_relationships=outgoing,
        incoming_relationships=incoming,
        total_relationships=incoming + outgoing,
    )


def test_topology_narrative_counts_relationship_directions() -> None:
    assert "1 represented incoming relationship and no represented outgoing" in _impact(1, 0).narrative()
    assert "no represented incoming relationships and 1 represented outgoing" in _impact(0, 1).narrative()
    assert "1 represented incoming relationship and 1 represented outgoing" in _impact(1, 1).narrative()
    assert "no direct relationships" in _impact(0, 0).narrative()


def test_prompt_serializes_evidence_roles_and_claim_safety() -> None:
    items = make_evidence([
        _result(
            "ABET/Computer Science Self-Study.pdf",
            "Our program normally assigns two faculty members for course coverage.",
        )
    ])
    context = build_grouped_evidence_context(items)
    prompt = build_decision_brief_prompt(
        "Assess staffing", context, evidence_topics=["Faculty Capacity"]
    )
    assert "Evidence Role: Institutional Self-Study" in context
    assert "must not be generalized" in prompt
    assert "Formal" in prompt and "External Standard" in prompt
    assert "uncertainty language" in prompt


def test_executive_source_label_omits_uncalibrated_score() -> None:
    label = executive_source_label(
        "Empirical Source 1", "Department Report", "Institutional Evidence"
    )
    assert label == "[Empirical Source 1] [Institutional Evidence] Department Report"
    assert "score" not in label.casefold()
