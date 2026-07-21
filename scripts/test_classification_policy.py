from __future__ import annotations

import json

import pytest

from app.classification import (
    ClassificationAssertion,
    ClassificationConfidence,
    ClassificationMethod,
    ClassificationProposal,
    EvidenceCitation,
)
from app.classification.classifiers import DeterministicSemanticClassifier
from app.classification.policy import (
    AuditCandidate,
    AuditPolicy,
    ClassificationDecision,
    ClassificationDisposition,
    ClassificationGovernor,
    ClassificationPolicy,
    FieldPolicy,
)
from app.knowledge import KnowledgeObject


def _object(object_type="faculty_observation", object_id="ko-1", **fields):
    obj = KnowledgeObject(object_id, object_type, "Fixture", "Fixture text")
    for name, value in fields.items():
        setattr(obj, name, value)
    return obj


def _assertion(
    field_name="object_type",
    value="faculty_observation",
    *,
    method=ClassificationMethod.ADAPTER,
    score=1.0,
    adequate_citation=True,
    citation_attributes=None,
):
    citation = EvidenceCitation(
        source_kind="knowledge_object_field",
        field=field_name if adequate_citation else None,
        knowledge_object_id="ko-1" if adequate_citation else None,
        attributes=citation_attributes or {},
    )
    return ClassificationAssertion(
        field_name,
        value,
        ClassificationConfidence(score),
        method,
        (citation,),
    )


def _proposal(*assertions, classifier="fixture_classifier"):
    return ClassificationProposal("ko-1", assertions, classifier)


@pytest.mark.parametrize(
    ("method", "score", "expected"),
    (
        (ClassificationMethod.ADAPTER, 1.0, ClassificationDisposition.AUTO_ACCEPT),
        (ClassificationMethod.DETERMINISTIC_RULE, 1.0, ClassificationDisposition.REVIEW),
        (
            ClassificationMethod.REGISTRY_LOOKUP,
            0.97,
            ClassificationDisposition.REVIEW,
        ),
        (ClassificationMethod.LLM, 1.0, ClassificationDisposition.REVIEW),
        (ClassificationMethod.MANUAL, 0.2, ClassificationDisposition.AUTO_ACCEPT),
        (ClassificationMethod.UNKNOWN, 1.0, ClassificationDisposition.ABSTAIN),
    ),
)
def test_policy_is_method_aware(method, score, expected):
    decision = ClassificationPolicy().evaluate(
        _proposal(_assertion(method=method, score=score))
    )
    assert decision.assertion_decisions[0].disposition == expected


def test_registered_rule_and_unique_registry_match_can_auto_accept():
    rule = _assertion(
        method=ClassificationMethod.DETERMINISTIC_RULE,
        citation_attributes={
            "registered_rule": True,
            "predicates_satisfied": True,
            "unambiguous": True,
        },
    )
    registry = _assertion(
        method=ClassificationMethod.REGISTRY_LOOKUP,
        citation_attributes={
            "unique_match": True,
            "canonical_entity_exists": True,
            "competing_match_above_threshold": False,
        },
    )
    assert ClassificationPolicy().evaluate(_proposal(rule)).disposition == (
        ClassificationDisposition.AUTO_ACCEPT
    )
    assert ClassificationPolicy().evaluate(_proposal(registry)).disposition == (
        ClassificationDisposition.AUTO_ACCEPT
    )
    assert ClassificationAssertion.from_dict(rule.to_dict()) == rule


def test_high_consequence_fields_are_accepted_with_audit():
    authority = _assertion(
        "authority",
        {"issuing_authority": "Christopher Newport University"},
    )
    decision = ClassificationPolicy().evaluate(_proposal(authority))
    assert decision.disposition == ClassificationDisposition.ACCEPT_WITH_AUDIT


def test_field_policy_can_require_a_stricter_threshold():
    policies = dict(ClassificationPolicy().field_policies)
    policies["object_type"] = FieldPolicy(
        "object_type",
        {ClassificationMethod.ADAPTER: 1.0},
        {ClassificationMethod.ADAPTER: 0.8},
    )
    decision = ClassificationPolicy(policies).evaluate(
        _proposal(_assertion(score=0.95))
    )
    assert decision.disposition == ClassificationDisposition.REVIEW


def test_structurally_inadequate_citation_causes_abstention():
    decision = ClassificationPolicy().evaluate(
        _proposal(_assertion(adequate_citation=False))
    )
    item = decision.assertion_decisions[0]
    assert item.disposition == ClassificationDisposition.ABSTAIN
    assert item.reasons[0].code == "insufficient_evidence"


def test_invalid_or_unknown_identity_fields_are_rejected():
    decision = ClassificationPolicy().evaluate(
        _proposal(_assertion("department_score", 0.8))
    )
    assert decision.disposition == ClassificationDisposition.REJECT
    assert decision.assertion_decisions[0].reasons[0].code == "unknown_field"


def test_competing_object_types_and_existing_departments_conflict():
    policy = ClassificationPolicy()
    current = _proposal(_assertion(value="faculty_observation"), classifier="one")
    competing = _proposal(_assertion(value="document"), classifier="two")
    decision = policy.evaluate(current, competing_proposals=(competing,))
    assert decision.disposition == ClassificationDisposition.CONFLICT

    obj = _object(
        display_name="Ada Example",
        published_department="Department of Physics",
        snapshot_date="2026-07-21",
    )
    obj.metadata["semantic_identity"] = {
        "object_type": "faculty_observation",
        "institutional_entities": [
            {
                "entity_type": "department",
                "entity_id": "department:english",
            }
        ],
    }
    proposal = DeterministicSemanticClassifier().classify(obj)
    decision = policy.evaluate(proposal, knowledge_object=obj)
    conflicted = {
        item.assertion.field_name
        for item in decision.assertion_decisions
        if item.disposition == ClassificationDisposition.CONFLICT
    }
    assert conflicted == {"institutional_entities"}


def test_object_type_mismatch_with_enclosing_object_conflicts():
    obj = _object("faculty_observation")
    decision = ClassificationPolicy().evaluate(
        _proposal(_assertion(value="document")),
        knowledge_object=obj,
    )
    assert decision.disposition == ClassificationDisposition.CONFLICT
    assert decision.assertion_decisions[0].conflicts[0].competing_source == (
        "knowledge_object.object_type"
    )


def test_partial_safe_application_merges_identity_and_is_idempotent():
    obj = _object()
    obj.metadata["semantic_identity"] = {
        "object_type": "faculty_observation",
        "decision_domains": ["academic_program"],
    }
    proposal = _proposal(
        _assertion(),
        _assertion(
            "institutional_entities",
            [
                {
                    "entity_type": "faculty",
                    "entity_id": "faculty:ada",
                    "published_name": "Ada Example",
                }
            ],
        ),
        _assertion(
            "authority",
            {"issuing_authority": "Unreviewed model output"},
            method=ClassificationMethod.LLM,
            score=0.8,
        ),
    )
    decision = ClassificationPolicy().evaluate(proposal, knowledge_object=obj)

    assert [item.disposition for item in decision.assertion_decisions] == [
        ClassificationDisposition.AUTO_ACCEPT,
        ClassificationDisposition.AUTO_ACCEPT,
        ClassificationDisposition.REVIEW,
    ]
    original_id = obj.id
    decision.apply_to_knowledge_object(obj)
    first = json.loads(obj.to_json())
    decision.apply_to_knowledge_object(obj)

    assert obj.id == original_id
    assert obj.semantic_identity.decision_domains == ("academic_program",)
    assert obj.semantic_identity.authority is None
    assert len(obj.metadata["classification_provenance"]) == 1
    assert json.loads(obj.to_json()) == first


def test_decision_serialization_round_trip():
    decision = ClassificationPolicy().evaluate(_proposal(_assertion()))
    restored = ClassificationDecision.from_dict(decision.to_dict())
    assert restored.to_dict() == decision.to_dict()
    assert restored.fingerprint() == decision.fingerprint()


def test_governor_abstains_for_unsupported_objects_and_dry_run_does_not_mutate():
    governor = ClassificationGovernor((DeterministicSemanticClassifier(),))
    unsupported = _object("document")
    result = governor.classify(unsupported)
    assert result.proposal is None
    assert result.abstention.reasons[0].code == "unsupported_object_type"

    supported = _object(
        display_name="Ada Example", snapshot_date="2026-07-21"
    )
    before = supported.to_json()
    result = governor.classify(supported, apply=False)
    assert result.decision.accepted_assertions
    assert supported.to_json() == before


def test_audit_sampling_is_seeded_reproducible_and_honors_minimums():
    policy = ClassificationPolicy()
    candidates = []
    for index in range(8):
        proposal = ClassificationProposal(
            f"ko-{index}",
            (
                ClassificationAssertion(
                    "object_type",
                    "faculty_observation",
                    ClassificationConfidence(1.0),
                    ClassificationMethod.ADAPTER,
                    (
                        EvidenceCitation(
                            "knowledge_object_field",
                            field="object_type",
                            knowledge_object_id=f"ko-{index}",
                        ),
                    ),
                ),
            ),
            "faculty_classifier" if index < 4 else "catalog_classifier",
        )
        candidates.append(
            AuditCandidate(policy.evaluate(proposal), "faculty" if index % 2 else "catalog")
        )
    audit_policy = AuditPolicy(
        percentage=0.0,
        minimum_per_classifier=1,
        minimum_per_object_type=1,
        seed="stable-seed",
    )
    first = audit_policy.select(candidates)
    second = audit_policy.select(tuple(reversed(candidates)))
    assert first == second
    assert len(first.selected_keys) >= 2
    selected = {candidate.key: candidate for candidate in candidates if candidate.key in first.selected_keys}
    assert {item.decision.classifier_name for item in selected.values()} == {
        "faculty_classifier",
        "catalog_classifier",
    }
    assert {item.object_type for item in selected.values()} == {"faculty", "catalog"}


def test_audit_sampling_selects_assertions_near_policy_threshold():
    proposal = _proposal(_assertion(score=0.95))
    candidate = AuditCandidate(
        ClassificationPolicy().evaluate(proposal), "faculty_observation"
    )
    selection = AuditPolicy(
        percentage=0.0,
        minimum_per_classifier=0,
        minimum_per_object_type=0,
        near_threshold_margin=0.0,
    ).select((candidate,))
    assert selection.selected_keys == (candidate.key,)
    assert selection.reasons[candidate.key] == ("near_policy_threshold",)
