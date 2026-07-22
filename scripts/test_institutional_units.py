from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.classification.classifiers import DeterministicSemanticClassifier
from app.classification.corpus import (
    CorpusClassificationOptions, SemanticCorpusPopulationService,
)
from app.classification.policy import ClassificationGovernor
from app.institutional_units import (
    AcademicUnitRegistry,
    assess_faculty_workforce_eligibility,
    is_department_workforce_entity,
)
from app.knowledge import KnowledgeObject, load_knowledge_object
from app.observatory.decision_brief.dashboard_v2.participation import _topology_profile
from app.observatory.topology.bootstrap import build_bootstrap_catalog
from app.observatory.topology.entity import EntityType


def _faculty(department="School of Engineering and Computing", object_id="faculty:test"):
    obj = KnowledgeObject(
        id=object_id, object_type="faculty_observation",
        title="Published faculty observation", text="Published facts.", metadata={},
    )
    obj.display_name = "Example Faculty"
    obj.published_department = department
    obj.snapshot_date = "2026-07-21"
    return obj


def _proposal_value(proposal, field):
    return next(item.value for item in proposal.assertions if item.field_name == field)


def _entity(values, unit_id):
    return next(item for item in values if item["entity_id"] == unit_id)


def test_governed_school_types_roles_and_hierarchy():
    registry = AcademicUnitRegistry.load()
    sec = registry.resolve("SEC")
    assert sec.formal_unit_type == "dependent_school"
    assert sec.entity_type == "school"
    assert sec.parent_unit_id == "academic_unit:college_natural_behavioral_sciences"
    assert sec.has_dean is False
    assert set(sec.operational_roles) >= {
        "department_equivalent", "faculty_home_unit", "workforce_allocation_unit",
    }
    assert sec.is_department_workforce_unit

    luter = registry.resolve("Luter School of Business")
    assert luter.formal_unit_type == "independent_school"
    assert luter.has_dean is True
    assert "college_equivalent" in luter.operational_roles
    assert "department_equivalent" not in luter.operational_roles
    assert len(luter.subordinate_unit_ids) == 2
    assert not luter.is_department_workforce_unit

    arts = registry.resolve("School of the Arts")
    assert arts.formal_unit_type == "dependent_school"
    assert arts.has_dean is False
    assert arts.parent_unit_id == "academic_unit:faculty_arts_humanities"
    assert "department_equivalent" not in arts.operational_roles
    assert len(arts.subordinate_unit_ids) == 2


def test_governed_subordinate_departments_and_unknown_school_behavior():
    registry = AcademicUnitRegistry.load()
    fine_art = registry.resolve("Fine Art and Art History")
    music = registry.resolve("Music, Theatre, and Dance")
    accounting = registry.resolve("Accounting and Finance Department")
    management = registry.resolve("Management and Marketing Department")
    assert fine_art.formal_unit_type == music.formal_unit_type == "department"
    assert fine_art.parent_unit_id == music.parent_unit_id == "academic_unit:school_arts"
    assert accounting.parent_unit_id == management.parent_unit_id == "academic_unit:luter_school_business"
    assert all(unit.is_department_workforce_unit for unit in (fine_art, music, accounting, management))
    assert registry.resolve("Imaginary School of Examples") is None

    proposal = DeterministicSemanticClassifier().classify(
        _faculty("Imaginary School of Examples")
    )
    unit = _entity(_proposal_value(proposal, "institutional_entities"), "published_academic_unit:Imaginary School of Examples")
    assert unit["entity_type"] == "academic_unit"
    assert "formal_unit_type" not in unit
    assert "operational_roles" not in unit


def test_sec_faculty_membership_is_organizational_not_major_assignment():
    obj = _faculty()
    proposal = DeterministicSemanticClassifier().classify(obj)
    entities = _proposal_value(proposal, "institutional_entities")
    relationships = _proposal_value(proposal, "organizational_relationships")
    sec = _entity(entities, "academic_unit:sec")
    assert sec["entity_type"] == "school"
    assert sec["formal_unit_type"] == "dependent_school"
    assert "department_equivalent" in sec["operational_roles"]
    assert _entity(entities, "academic_unit:college_natural_behavioral_sciences")
    assert any(item["relationship_type"] == "faculty_member_of_unit" and item["target"] == sec["entity_id"] for item in relationships)
    assert any(item["relationship_type"] == "belongs_to" and item["target"] == "academic_unit:college_natural_behavioral_sciences" for item in relationships)
    encoded = json.dumps(proposal.to_dict()).casefold()
    assert "physics major" not in encoded
    assert "computer science major" not in encoded
    assert "faculty_associated_with_major" not in encoded


def test_ordinary_department_remains_a_department_and_workforce_helper_is_role_aware():
    proposal = DeterministicSemanticClassifier().classify(_faculty("Department of Examples"))
    entity = _entity(_proposal_value(proposal, "institutional_entities"), "published_academic_unit:Department of Examples")
    assert entity["entity_type"] == "department"
    assert is_department_workforce_entity(entity)
    assert is_department_workforce_entity({
        "entity_type": "school", "formal_unit_type": "dependent_school",
        "operational_roles": ["department_equivalent"],
    })
    assert not is_department_workforce_entity({
        "entity_type": "school", "formal_unit_type": "independent_school",
        "operational_roles": ["college_equivalent"],
    })


def test_workforce_participation_includes_only_explicit_department_equivalents():
    sec = SimpleNamespace(entity=SimpleNamespace(
        entity_type="school", name="School of Engineering and Computing",
        metadata={"operational_roles": ["department_equivalent"]},
    ))
    luter = SimpleNamespace(entity=SimpleNamespace(
        entity_type="school", name="Luter School of Business",
        metadata={"operational_roles": ["college_equivalent"]},
    ))
    assert _topology_profile(sec).academic_unit == "School of Engineering and Computing"
    assert _topology_profile(luter).academic_unit is None

    catalog = build_bootstrap_catalog()
    assert catalog.get_entity("academic_unit:sec").entity_type == EntityType.SCHOOL
    assert catalog.get_entity("program:physics").entity_type == EntityType.PROGRAM


def test_registry_reclassification_replaces_legacy_entity_and_is_idempotent(tmp_path):
    path = tmp_path / "faculty.json"
    obj = _faculty(object_id="faculty:sec")
    obj.metadata["semantic_identity"] = {
        "object_type": "faculty_observation",
        "institutional_entities": [
            {"entity_type": "faculty", "entity_id": "faculty_observation:faculty:sec", "published_name": "Example Faculty"},
            {"entity_type": "department", "entity_id": "published_academic_unit:School of Engineering and Computing", "published_name": "School of Engineering and Computing"},
        ],
        "decision_domains": ["preserved_domain"],
    }
    payload = obj.to_dict()
    payload.update({
        "display_name": obj.display_name, "published_department": obj.published_department,
        "snapshot_date": obj.snapshot_date, "observation_id": obj.id,
    })
    path.write_text(json.dumps(payload), encoding="utf-8")
    options = CorpusClassificationOptions(
        input_roots=(path,), report_dir=tmp_path / "apply", apply=True,
    )
    first = SemanticCorpusPopulationService().run(options)
    restored = load_knowledge_object(path)
    identity = restored.semantic_identity.to_dict()
    assert first.overall.changed == 1
    assert "preserved_domain" in identity["decision_domains"]
    assert not any(item["entity_id"] == "published_academic_unit:School of Engineering and Computing" for item in identity["institutional_entities"])
    assert any(item["entity_id"] == "academic_unit:sec" for item in identity["institutional_entities"])

    second = SemanticCorpusPopulationService().run(CorpusClassificationOptions(
        input_roots=(path,), report_dir=tmp_path / "second", apply=False,
    ))
    assert second.overall.changed == 0
    assert second.overall.unchanged == 1


def test_governed_aliases_and_contamination_cleanup_are_bounded():
    registry = AcademicUnitRegistry.load()
    communication = "academic_unit:department_communication_studies"
    for label in (
        "Communication", "Communication Studies", "Department of Communication",
        "Department of Communication Studies",
    ):
        assert registry.resolve_published_label(label).unit_id == communication
    contaminated = registry.resolve_published_label(
        "Communication. Ph.B., Miami University;"
    )
    assert contaminated.unit_id == communication
    assert contaminated.cleaned_label == "Communication"
    assert contaminated.classification == "parser_contamination"
    assert contaminated.resolution_method == "cleaned_governed_alias"

    bces = "academic_unit:department_biology_chemistry_environmental_science"
    for label in (
        "Biology, Chemistry and Environmental Science",
        "Biology, Chemistry, and Environmental Science",
        "Department of Biology, Chemistry and Environmental Science",
    ):
        assert registry.resolve_published_label(label).unit_id == bces
    contaminated_bces = registry.resolve_published_label(
        "Biology, Chemistry, and Environmental Science. B.Ed., Beijing Sport University;"
    )
    assert contaminated_bces.unit_id == bces
    assert contaminated_bces.classification == "parser_contamination"


def test_emeritus_is_preserved_resolved_and_excluded_from_active_workforce():
    registry = AcademicUnitRegistry.load()
    for label in ("Accounting, Emeritus", "Accounting, Emerita", "Biology, Emeritus"):
        result = registry.resolve_published_label(label)
        assert result.unit is not None
        assert result.classification == "excluded_emeritus"
        assert result.active_workforce_eligible is False
        assert result.exclusion_reason == "explicit_emeritus_or_emerita"
        assert "emerit" in result.original_label.casefold()
    eligibility = assess_faculty_workforce_eligibility({
        "published_title": "Professor of Communication, Emerita",
    })
    assert eligibility.active_workforce_eligible is False
    assert eligibility.matched_published_values == (
        "Professor of Communication, Emerita",
    )


def test_common_words_and_competing_embedded_units_are_not_guessed():
    registry = AcademicUnitRegistry.load()
    assert registry.resolve_published_label("Art").resolution_method == "unresolved"
    ambiguous = registry.resolve_published_label(
        "Accounting, Finance, Management & Marketing. B.B.A, University of Notre Dame;"
    )
    assert ambiguous.resolution_method == "ambiguous"
    assert ambiguous.unit is None
    assert set(ambiguous.competing_unit_ids) == {
        "academic_unit:department_accounting_finance",
        "academic_unit:department_management_marketing",
    }


def test_historical_pcse_is_distinct_from_current_sec_and_new_units_load():
    registry = AcademicUnitRegistry.load()
    historical = registry.resolve_published_label(
        "Department of Physics, Computer Science and Engineering"
    ).unit
    current = registry.resolve("SEC")
    assert historical.unit_id == "academic_unit:department_pcse_historical"
    assert historical.deprecated is True
    assert historical.is_department_workforce_unit is False
    assert historical.to_entity().deprecated is True
    assert is_department_workforce_entity(historical.to_entity()) is False
    assert historical.unit_id != current.unit_id
    for unit_id in (
        "academic_unit:department_communication_studies",
        "academic_unit:department_economics", "academic_unit:department_english",
        "academic_unit:department_history",
        "academic_unit:department_leadership_american_studies",
        "academic_unit:department_mathematics",
        "academic_unit:department_philosophy_religion",
        "academic_unit:department_political_science",
        "academic_unit:department_psychology",
        "academic_unit:department_sociology_social_work_anthropology",
    ):
        assert registry.get(unit_id).formal_unit_type == "department"


def test_academic_unit_parent_hierarchy_rejects_cycles():
    source = AcademicUnitRegistry.load()
    left = replace(
        source.get("academic_unit:department_english"),
        parent_unit_id="academic_unit:department_history",
    )
    right = replace(
        source.get("academic_unit:department_history"),
        parent_unit_id="academic_unit:department_english",
    )
    with pytest.raises(ValueError, match="contains a cycle"):
        AcademicUnitRegistry((left, right))
