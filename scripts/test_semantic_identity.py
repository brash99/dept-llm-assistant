import json

import pytest

from app.chunk import chunk_document
from app.knowledge import KnowledgeObject
from app.semantic_identity import (
    Authority,
    InstitutionalEntity,
    OrganizationalRelationship,
    SemanticIdentity,
    TemporalScope,
)
from app.semantic_scope import (
    MembershipProvenance,
    SemanticMembership,
    semantic_membership_ids,
)


def _identity():
    return SemanticIdentity(
        object_type="document",
        institutional_entities=(
            InstitutionalEntity(
                entity_type="institution",
                entity_id="institution:cnu",
                published_name="Christopher Newport University",
            ),
            InstitutionalEntity(
                entity_type="department",
                entity_id="department:english",
                published_name="Department of English",
            ),
        ),
        organizational_relationships=(
            OrganizationalRelationship(
                relationship_type="published_by",
                source="knowledge_object:annual_report",
                target="department:english",
                published_label="Published by the Department of English",
                evidence_reference="page:1",
            ),
        ),
        decision_domains=("academic_workforce_planning",),
        authority=Authority(
            issuing_authority="Department of English",
            authority_class="institutional_report",
            evidence_role="Departmental Report",
        ),
        temporal_scope=TemporalScope(
            effective_from="2025-07-01",
            effective_until="2026-06-30",
            published_label="Academic Year 2025-26",
        ),
        institutional_relevance={"published_scope": "departmental"},
    )


def test_semantic_identity_serializes_and_round_trips_through_knowledge_object():
    obj = KnowledgeObject(
        id="stable-object-id",
        object_type="document",
        title="English annual report",
        text="Published facts.",
    )
    obj.set_semantic_identity(_identity())
    encoded = json.loads(obj.to_json())
    restored = KnowledgeObject.from_dict(encoded)

    assert restored.id == "stable-object-id"
    assert restored.semantic_identity == _identity()
    assert [entity.entity_type for entity in restored.institutional_entities] == [
        "institution",
        "department",
    ]
    assert restored.authority.issuing_authority == "Department of English"
    assert restored.temporal_scope.published_label == "Academic Year 2025-26"
    assert restored.decision_domains == ("academic_workforce_planning",)


@pytest.mark.parametrize(
    "relationship_type",
    ("belongs_to", "published_by", "describes", "governs", "supports", "references", "concerns"),
)
def test_general_relationship_types_preserve_factual_assertions(relationship_type):
    relationship = OrganizationalRelationship(
        relationship_type=relationship_type,
        source="knowledge_object:source",
        target="institution:cnu",
        evidence_reference="source:page-2",
        effective_from="2025-01-01",
    )
    assert OrganizationalRelationship.from_dict(relationship.to_dict()) == relationship


def test_institutional_entity_types_are_extensible_not_closed_taxonomy():
    types = (
        "institution", "college", "department", "program", "faculty", "research_group"
    )
    entities = tuple(
        InstitutionalEntity(entity_type=value, entity_id=f"{value}:example")
        for value in types
    )
    identity = SemanticIdentity(object_type="document", institutional_entities=entities)
    assert tuple(entity.entity_type for entity in identity.institutional_entities) == types


def test_academic_unit_organizational_fields_round_trip_without_affecting_legacy_entities():
    entity = InstitutionalEntity(
        entity_type="school", entity_id="academic_unit:sec",
        published_name="School of Engineering and Computing",
        formal_unit_type="dependent_school",
        operational_roles=("department_equivalent", "faculty_home_unit"),
        parent_unit_id="academic_unit:cnbs", governance_level="department_equivalent",
        leadership_type="director", has_dean=False,
        contains_subordinate_departments=False,
    )
    assert InstitutionalEntity.from_dict(entity.to_dict()) == entity
    assert InstitutionalEntity.from_dict({
        "entity_type": "department", "entity_id": "department:english"
    }).formal_unit_type is None


@pytest.mark.parametrize("provenance", tuple(MembershipProvenance))
def test_membership_provenance_is_explicit_and_retrieval_compatible(provenance):
    membership = SemanticMembership(
        scope="department:english",
        provenance=provenance,
        asserted_by="adapter:catalog" if provenance == MembershipProvenance.ASSERTED else None,
        reviewed_by="reviewer:institutional_research"
        if provenance == MembershipProvenance.REVIEWED else None,
    )
    restored = SemanticMembership.from_dict(membership.to_dict())
    assert restored == membership
    assert semantic_membership_ids([membership.to_dict()]) == ("department:english",)


def test_legacy_knowledge_object_without_identity_remains_valid():
    obj = KnowledgeObject(
        id="legacy",
        object_type="document",
        title="Legacy object",
        text="Legacy factual text.",
        metadata={
            "semantic_memberships": ["institution"],
            "organizational_relationships": [
                {"relationship_type": "concerns", "target": "institution:cnu"}
            ],
            "decision_domains": ["academic_program"],
        },
    )
    assert obj.semantic_identity is None
    assert obj.semantic_memberships == ("institution",)
    assert obj.decision_domains == ("academic_program",)
    assert obj.organizational_relationships[0]["relationship_type"] == "concerns"
    assert KnowledgeObject.from_dict(obj.to_dict()).to_dict() == obj.to_dict()


def test_identity_inherits_to_chunk_without_changing_text_or_ids():
    obj = KnowledgeObject(
        id="stable-object-id",
        object_type="document",
        title="Annual report",
        text="Exactly the original chunk text.",
    )
    obj.set_semantic_identity(_identity())
    before = chunk_document(obj)[0]
    after = chunk_document(obj)[0]
    assert before.id == after.id
    assert before.text == "Exactly the original chunk text."
    assert before.metadata["semantic_identity"] == _identity().to_dict()


def test_identity_object_type_must_match_knowledge_object():
    obj = KnowledgeObject("id", "document", "Title", "Text")
    original_id = obj.id
    with pytest.raises(ValueError, match="must match"):
        obj.set_semantic_identity(SemanticIdentity(object_type="faculty_observation"))
    assert obj.id == original_id
    assert obj.semantic_identity is None

    malformed = KnowledgeObject(
        "legacy-id",
        "document",
        "Title",
        "Text",
        metadata={
            "semantic_identity": SemanticIdentity(
                object_type="faculty_observation"
            ).to_dict()
        },
    )
    with pytest.raises(ValueError, match="must match"):
        _ = malformed.semantic_identity
