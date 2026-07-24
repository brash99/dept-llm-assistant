import sys
import types
from types import SimpleNamespace

import pytest


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
    LLC_AREAS_OF_INQUIRY,
    LLC_CORE_REQUIREMENTS,
    InstitutionalParticipationProfile,
    ParticipationFunction,
    ParticipationRelationship,
)
from app.observatory.decision_brief.dashboard_v2.participation import (
    InstitutionalParticipationProfilePanel,
)


def _fitness(decision_type="academic_workforce_planning"):
    return SimpleNamespace(
        decision_type=decision_type,
        topic_grades={
            "Faculty Capacity": "partial",
            "Instructional Demand": "strong",
            "Service Teaching Dependence": "weak",
            "One-Line Loss Scenario": "missing",
        },
        topic_support={
            "Faculty Capacity": {"score": 0.61},
            "Instructional Demand": {"score": 0.81},
            "Service Teaching Dependence": {"score": 0.30},
            "One-Line Loss Scenario": {"score": 0.0},
        },
    )


def _complete_profile() -> InstitutionalParticipationProfile:
    return InstitutionalParticipationProfile(
        academic_unit="Example Academic Unit",
        organizational_context={
            "college": "Example College",
            "faculty": 12,
            "staff": 2,
            "majors": ("Example Major",),
            "minors": ("Example Minor",),
            "operating_budget": "$100,000",
            "physical_space": "Example Laboratory",
        },
        instructional_functions=(
            ParticipationFunction(
                name="EXM 201 instruction",
                evidence_status="evidenced",
                evidence=("Catalog course record",),
                missing_evidence=("Current section capacity",),
                substitutability_status="Alternative providers evidenced",
                alternative_providers=("Alternative Unit",),
            ),
        ),
        relationships=(
            ParticipationRelationship(
                source="Example Academic Unit",
                relationship="offers",
                target="EXM 201",
                evidence=("Catalog course record",),
            ),
            ParticipationRelationship(
                source="EXM 201",
                relationship="supports",
                target="Example Program",
                evidence=("Program requirement record",),
            ),
        ),
        capabilities=(
            ParticipationFunction(
                name="Example Program support",
                evidence_status="evidenced",
                evidence=("Program requirement record",),
                substitutability_status="Insufficient evidence",
                missing_evidence=("Alternative-provider capacity",),
            ),
            ParticipationFunction(
                name="Undergraduate research supervision",
                evidence_status="indicated_but_incomplete",
                evidence=("Annual report reference",),
                missing_evidence=("Current supervision assignments",),
            ),
            ParticipationFunction(
                name="Faculty governance",
                evidence_status="not_yet_assessed",
                missing_evidence=("Current committee assignments",),
            ),
        ),
    )


def test_complete_participation_profile_renders_supported_facts() -> None:
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
        participation_profile=_complete_profile(),
    )

    assert "## Institutional Participation Profile" in markdown
    assert "**Selected Academic Unit:** Example Academic Unit" in markdown
    assert "**College:** Example College" in markdown
    assert "**Faculty:** 12" in markdown
    assert "EXM 201 instruction" in markdown
    assert "Example Academic Unit** offers **EXM 201" in markdown
    assert "EXM 201** supports **Example Program" in markdown
    assert "#### Evidenced Capabilities" in markdown
    assert "#### Indicated but Incomplete" in markdown
    assert "#### Not Yet Assessed" in markdown


def test_missing_fields_are_unknown_not_zero() -> None:
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
    )

    assert "**Selected Academic Unit:** Not Yet Available" in markdown
    assert "**College:** Unknown" in markdown
    assert "**Faculty:** Unknown" in markdown
    assert "**Operating Budget:** Unknown" in markdown
    assert "**Faculty:** 0" not in markdown
    assert "**Operating Budget:** 0" not in markdown


def test_profile_has_no_department_or_faculty_scores() -> None:
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
        participation_profile=_complete_profile(),
    )

    assert "Department Score" not in markdown
    assert "Faculty Score" not in markdown
    assert "rank departments or faculty" in markdown


def test_contract_rejects_unsupported_evidence_claims() -> None:
    with pytest.raises(ValueError, match="require evidence"):
        ParticipationFunction(
            name="Unsupported evidenced function",
            evidence_status="evidenced",
        )

    with pytest.raises(ValueError, match="named providers"):
        ParticipationFunction(
            name="Unsupported provider claim",
            substitutability_status="Alternative providers evidenced",
        )


def test_substitutability_is_function_level_and_not_inferred() -> None:
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
        participation_profile=_complete_profile(),
    )

    section = markdown.split("### 5. Functional Substitutability", 1)[1]
    assert "#### Example Program support" in section
    assert "**Alternative-provider status:** Insufficient evidence" in section
    assert "#### EXM 201 instruction" in section
    assert "**Alternative providers:** Alternative Unit" in section
    assert "Not established from supplied evidence" in section
    assert "Is this department substitutable?" not in markdown


def test_substitutability_wording_tracks_assessment_status() -> None:
    profile = InstitutionalParticipationProfile(
        academic_unit="Example Academic Unit",
        capabilities=(
            ParticipationFunction(
                name="Unassessed function",
            ),
            ParticipationFunction(
                name="No provider established",
                substitutability_status="No alternative provider evidenced",
            ),
            ParticipationFunction(
                name="Potential provider function",
                substitutability_status=(
                    "Potential alternative providers indicated"
                ),
                alternative_providers=("Potential Unit",),
            ),
        ),
    )
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
        participation_profile=profile,
    )

    assert "**Alternative providers:** Not assessed" in markdown
    assert (
        "**Alternative providers:** No alternative provider established "
        "by supplied evidence"
    ) in markdown
    assert "Potential providers indicated — Potential Unit" in markdown
    assert "None identified" not in markdown


def test_substitutability_deduplicates_only_identical_functions() -> None:
    shared = ParticipationFunction(
        name="Shared function name",
        evidence_status="indicated_but_incomplete",
        evidence=("Shared evidence",),
    )
    distinct = ParticipationFunction(
        name="Shared function name",
        evidence_status="indicated_but_incomplete",
        evidence=("Different evidence",),
    )
    profile = InstitutionalParticipationProfile(
        academic_unit="Example Academic Unit",
        instructional_functions=(shared,),
        capabilities=(shared, distinct),
    )
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
        participation_profile=profile,
    )
    section = markdown.split("### 5. Functional Substitutability", 1)[1]

    assert section.count("#### Shared function name") == 2


def test_unsupported_relationships_remain_unsupported() -> None:
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
        participation_profile=_complete_profile(),
    )

    assert "Example Program" in markdown
    assert "Imagined Partner" not in markdown
    assert "remain Unknown unless shown above" in markdown


def test_llc_terminology_and_reference_contract() -> None:
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
    )

    assert "Liberal Learning Core (LLC)" in markdown
    for requirement in LLC_CORE_REQUIREMENTS:
        assert requirement in markdown
    for area in LLC_AREAS_OF_INQUIRY:
        assert area in markdown
    assert "General Education" not in markdown


def test_topology_legacy_label_is_not_silently_recast_as_llc() -> None:
    impact = SimpleNamespace(
        entity=SimpleNamespace(
            name="Example Unit",
            entity_type="department",
            metadata={},
        ),
        supports=(),
        contributes_to=("General Education",),
    )
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
        topology_impact=impact,
    )

    assert "recorded as General Education" in markdown
    assert "LLC mapping not established" in markdown


def test_valid_academic_unit_topology_entity_is_adapted() -> None:
    impact = SimpleNamespace(
        entity=SimpleNamespace(
            name="Example College",
            entity_type="college",
            metadata={"faculty": 25},
        ),
        supports=("Example Program",),
        contributes_to=(),
    )
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
        topology_impact=impact,
    )

    assert "**Selected Academic Unit:** Example College" in markdown
    assert "**Faculty:** 25" in markdown
    assert "Support for Example Program" in markdown


def test_non_academic_topology_entity_is_not_adapted() -> None:
    impact = SimpleNamespace(
        entity=SimpleNamespace(
            name="Example Program",
            entity_type="program",
            metadata={"faculty": 25},
        ),
        supports=("Imagined Relationship",),
        contributes_to=(),
    )
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
        topology_impact=impact,
    )

    assert "**Selected Academic Unit:** Not Yet Available" in markdown
    assert "Example Program" not in markdown
    assert "Imagined Relationship" not in markdown
    assert "**Faculty:** Unknown" in markdown


@pytest.mark.parametrize("entity_type", [None, "", "other"])
def test_absent_or_ambiguous_entity_type_is_provisional(entity_type) -> None:
    impact = SimpleNamespace(
        entity=SimpleNamespace(
            name="Ambiguous Entity",
            entity_type=entity_type,
            metadata={},
        ),
        supports=(),
        contributes_to=(),
    )
    markdown = InstitutionalParticipationProfilePanel().render(
        evidence_fitness=_fitness(),
        topology_impact=impact,
    )

    assert "**Selected Academic Unit:** Not Yet Available" in markdown
    assert "Ambiguous Entity" not in markdown


def test_participation_rendering_is_deterministic() -> None:
    panel = InstitutionalParticipationProfilePanel()
    profile = _complete_profile()

    first = panel.render(_fitness(), participation_profile=profile)
    second = panel.render(_fitness(), participation_profile=profile)

    assert first == second


def test_dashboard_placement_and_activation() -> None:
    dashboard = ExecutiveDashboardV2()
    workforce = dashboard.render(
        question="How does this unit participate?",
        evidence_fitness=_fitness(),
        participation_profile=_complete_profile(),
    )
    other = dashboard.render(
        question="Should a new program be created?",
        evidence_fitness=_fitness("academic_program"),
        participation_profile=_complete_profile(),
    )

    assert workforce.index("## Academic Workforce Evidence Map") < (
        workforce.index("## Institutional Participation Profile")
    )
    assert "Institutional Participation Profile" not in other
