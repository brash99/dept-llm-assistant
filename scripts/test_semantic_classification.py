from __future__ import annotations

import pytest

from app.classification import (
    ClassificationAssertion,
    ClassificationConfidence,
    ClassificationMethod,
    ClassificationProposal,
    DeterministicSemanticClassifier,
    EvidenceCitation,
    MockLLMSemanticClassifier,
    ProposalStage,
    SemanticClassificationService,
)
from app.knowledge import KnowledgeObject


def _object(object_type: str, object_id: str = "ko-1", **fields) -> KnowledgeObject:
    obj = KnowledgeObject(
        id=object_id,
        object_type=object_type,
        title="Published observation",
        text="Published factual text",
        metadata={},
        source={"relative_path": "normalized/example.json"},
    )
    for name, value in fields.items():
        setattr(obj, name, value)
    return obj


def _assertion(
    field_name: str = "object_type",
    value="faculty_observation",
    score: float = 0.9,
    method: ClassificationMethod = ClassificationMethod.MANUAL,
) -> ClassificationAssertion:
    return ClassificationAssertion(
        field_name=field_name,
        value=value,
        confidence=ClassificationConfidence(score, "reviewed assertion"),
        classification_method=method,
        supporting_evidence=(
            EvidenceCitation(
                source_kind="knowledge_object_field",
                field=field_name,
                knowledge_object_id="ko-1",
            ),
        ),
    )


def _assertion_value(proposal: ClassificationProposal, field_name: str):
    return next(
        assertion.value
        for assertion in proposal.assertions
        if assertion.field_name == field_name
    )


def test_classification_contracts_serialize_and_preserve_lifecycle():
    proposal = ClassificationProposal(
        knowledge_object_id="ko-1",
        assertions=(_assertion(),),
        classifier_name="manual_review",
    )

    restored = ClassificationProposal.from_dict(proposal.to_dict())

    assert restored.to_dict() == proposal.to_dict()
    assert restored.stage == ProposalStage.PROPOSED
    assert restored.average_confidence == pytest.approx(0.9)
    assert restored.methods == (ClassificationMethod.MANUAL,)
    restored.reject("unsupported by reviewed evidence")
    assert restored.stage == ProposalStage.REJECTED
    assert restored.rejection_reason == "unsupported by reviewed evidence"
    with pytest.raises(ValueError, match="cannot be accepted"):
        restored.accept()


def test_assertions_require_valid_confidence_and_cited_evidence():
    with pytest.raises(ValueError, match="between 0 and 1"):
        ClassificationConfidence(1.01)
    with pytest.raises(ValueError, match="requires supporting evidence"):
        ClassificationAssertion(
            field_name="object_type",
            value="document",
            confidence=ClassificationConfidence(1.0),
            classification_method=ClassificationMethod.DETERMINISTIC_RULE,
            supporting_evidence=(),
        )
    assert {method.value for method in ClassificationMethod} == {
        "deterministic_rule",
        "adapter",
        "registry_lookup",
        "llm",
        "manual",
        "unknown",
    }


@pytest.mark.parametrize(
    ("obj", "entity_type", "temporal_key"),
    (
        (
            _object(
                "faculty_observation",
                display_name="Ada Example",
                published_department="Department of Examples",
                snapshot_date="2026-07-21",
            ),
            "faculty",
            "as_of",
        ),
        (
            _object(
                "course_offering_observation",
                course_code="EXM 201",
                section="01",
                academic_term="Fall 2026",
            ),
            "course_offering",
            "academic_term",
        ),
        (
            _object(
                "academic_unit_observation",
                published_name="Department of Examples",
                catalog_year="2025-26",
            ),
            "academic_unit",
            "published_label",
        ),
        (
            _object(
                "department_faculty_roster_observation",
                academic_unit="Department of Examples",
                catalog_year="2025-26",
            ),
            "academic_unit",
            "published_label",
        ),
        (
            _object(
                "catalog_faculty_observation",
                published_name="Grace Example",
                academic_unit="Department of Examples",
                catalog_year="2025-26",
            ),
            "faculty",
            "published_label",
        ),
    ),
)
def test_deterministic_classifiers_propose_only_published_fields(
    obj, entity_type, temporal_key
):
    proposal = DeterministicSemanticClassifier().classify(obj)

    assert obj.semantic_identity is None
    assert proposal.stage == ProposalStage.PROPOSED
    assert _assertion_value(proposal, "object_type") == obj.object_type
    entities = _assertion_value(proposal, "institutional_entities")
    assert any(entity["entity_type"] == entity_type for entity in entities)
    assert temporal_key in _assertion_value(proposal, "temporal_scope")
    assert all(
        assertion.classification_method == ClassificationMethod.ADAPTER
        and assertion.confidence.score == 1.0
        and assertion.supporting_evidence
        for assertion in proposal.assertions
    )


def test_constitutional_classifier_preserves_normative_fields_without_alignment():
    obj = _object(
        "constitutional_knowledge",
        institutional_scope=("Christopher Newport University",),
        effective_from="2023",
        effective_until=None,
        constitutional_type="strategic_compass",
        principles=("build a foundation to thrive",),
    )

    proposal = DeterministicSemanticClassifier().classify(obj)
    relevance = _assertion_value(proposal, "institutional_relevance")

    assert relevance["constitutional_type"] == "strategic_compass"
    assert relevance["principles"] == ["build a foundation to thrive"]
    assert "alignment" not in relevance


def test_catalog_publication_classifier_uses_year_without_inventing_entities():
    obj = _object(
        "catalog_observation",
        catalog_year="2025-26",
        publication_title="Christopher Newport University Catalog",
    )

    proposal = DeterministicSemanticClassifier().classify(obj)

    assert _assertion_value(proposal, "temporal_scope") == {
        "published_label": "2025-26"
    }
    assert not any(
        assertion.field_name == "institutional_entities"
        for assertion in proposal.assertions
    )

    faculty = _object(
        "catalog_faculty_observation",
        published_name="Grace Example",
        academic_unit=None,
        catalog_year="2025-26",
    )
    entities = _assertion_value(
        DeterministicSemanticClassifier().classify(faculty),
        "institutional_entities",
    )
    assert [entity["entity_type"] for entity in entities] == ["faculty"]


def test_service_optionally_accepts_and_applies_without_changing_object_id():
    obj = _object(
        "faculty_observation",
        display_name="Ada Example",
        snapshot_date="2026-07-21",
    )
    service = SemanticClassificationService()

    result = service.classify(obj, apply=True)

    assert result.automatically_accepted is True
    assert result.applied is True
    assert result.proposal.stage == ProposalStage.ACCEPTED
    assert obj.id == "ko-1"
    assert obj.semantic_identity.object_type == "faculty_observation"
    assert service.metrics.to_dict() == {
        "number_classified": 1,
        "method_used": {"adapter": 1},
        "average_confidence": 1.0,
        "number_requiring_review": 0,
        "number_automatically_accepted": 1,
    }


def test_service_leaves_lower_confidence_proposal_for_review():
    class ManualClassifier:
        method = ClassificationMethod.MANUAL

        def supports(self, obj):
            return True

        def classify(self, obj):
            return ClassificationProposal(
                obj.id, (_assertion(score=0.6),), "manual_classifier"
            )

    obj = _object("faculty_observation")
    service = SemanticClassificationService(classifiers=(ManualClassifier(),))

    result = service.classify(obj)

    assert result.proposal.stage == ProposalStage.PROPOSED
    assert result.proposal.requires_review() is True
    assert obj.semantic_identity is None
    assert service.metrics.number_requiring_review == 1
    assert service.metrics.number_automatically_accepted == 0


def test_application_requires_acceptance_and_matching_object():
    proposal = ClassificationProposal("ko-1", (_assertion(),), "manual")
    with pytest.raises(ValueError, match="accepted"):
        proposal.apply_to_knowledge_object(_object("faculty_observation"))
    proposal.accept()
    with pytest.raises(ValueError, match="does not belong"):
        proposal.apply_to_knowledge_object(
            _object("faculty_observation", object_id="ko-2")
        )


def test_unknown_objects_remain_backward_compatible_and_unmodified():
    obj = _object("document")
    service = SemanticClassificationService()

    with pytest.raises(ValueError, match="No semantic classifier supports"):
        service.classify(obj)

    assert obj.semantic_identity is None
    assert service.metrics.number_classified == 0


def test_mock_llm_is_interface_only_but_accepts_cited_future_assertions():
    obj = _object("document")
    classifier = MockLLMSemanticClassifier()

    with pytest.raises(NotImplementedError, match="no backend"):
        classifier.classify(obj)

    assertion = _assertion(
        value="document", score=0.7, method=ClassificationMethod.LLM
    )
    proposal = classifier.proposal_from_assertions(obj, (assertion,))
    assert proposal.stage == ProposalStage.PROPOSED
    assert proposal.methods == (ClassificationMethod.LLM,)


def test_existing_identity_is_not_overwritten_until_application():
    obj = _object(
        "faculty_observation",
        display_name="Ada Example",
        snapshot_date="2026-07-21",
    )
    obj.metadata["semantic_identity"] = {"object_type": "faculty_observation"}
    before = dict(obj.metadata["semantic_identity"])

    result = SemanticClassificationService().classify(obj, auto_accept=False)

    assert result.proposal.stage == ProposalStage.PROPOSED
    assert obj.metadata["semantic_identity"] == before
