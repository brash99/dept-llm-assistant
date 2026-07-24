import json

import pytest

from app.contribution_ontology import (
    ContributionAssertion,
    ContributionEvidenceBinding,
    ContributionKnowledgeObject,
    ContributionMeasure,
    ContributionPeriod,
    ContributionPredicate,
    ContributionTemporalScope,
)
from app.semantic_identity import InstitutionalEntity


def _department():
    return InstitutionalEntity(
        entity_type="department",
        entity_id="academic_unit:department_philosophy_religion",
        published_name="Department of Philosophy and Religion",
    )


def _program():
    return InstitutionalEntity(
        entity_type="program",
        entity_id="academic_program:pre_law",
        published_name="Pre-Law Program",
    )


def _scope():
    return ContributionTemporalScope(
        reporting_period=ContributionPeriod(
            start="2024-07-01", end="2025-06-30", label="AY 2024-25"
        ),
        effective_period=ContributionPeriod(label="Current during AY 2024-25"),
        observation_period=ContributionPeriod(
            start="2024-08-01", end="2025-05-15"
        ),
        publication_time="2025-07-01T12:00:00+00:00",
    )


def _binding(identifier="evidence:1"):
    return ContributionEvidenceBinding(
        binding_id=identifier,
        source_references=("schedule_observation:1", "subject_registry:1"),
        provenance={"source_system": "normalized_schedule"},
        builder="test_contribution_builder",
        builder_version="1",
        source_fingerprints={"schedule": "a" * 64},
        derivation_basis="governed subject ownership and explicit enrollment",
    )


def _assertion():
    binding = _binding()
    return ContributionAssertion(
        assertion_id="contribution_assertion:philosophy_supports_pre_law",
        subject=_department(),
        predicate=ContributionPredicate.SUPPORTS_PROGRAM,
        object=_program(),
        qualifiers={"instructional_role": "ethics"},
        temporal_scope=_scope(),
        evidence_bindings=(binding,),
        provenance={"governance": "deterministic_builder"},
        measures=(
            ContributionMeasure(
                measure_id="measure:sections",
                measure_type="section_count",
                value=3,
                unit="sections",
                definition="Distinct sections supporting the program.",
                evidence_binding_ids=(binding.binding_id,),
            ),
        ),
    )


def _object():
    return ContributionKnowledgeObject(
        contribution_object_id="contribution:philosophy_religion:ay_2024_25",
        entity=_department(),
        temporal_scope=_scope(),
        assertions=(_assertion(),),
        provenance={"publisher": "ISO semantic layer"},
    )


def test_generic_contribution_object_round_trips_with_stable_fingerprint():
    value = _object()
    restored = ContributionKnowledgeObject.from_json(value.to_json())

    assert restored == value
    assert restored.deterministic_fingerprint == value.deterministic_fingerprint
    assert len(value.deterministic_fingerprint) == 64
    assert json.loads(value.to_json())["assertions"][0]["predicate"] == (
        "supports_program"
    )


def test_predicate_vocabulary_is_governed_and_unknown_values_are_rejected():
    assert {item.value for item in ContributionPredicate} == {
        "administers_program",
        "supports_program",
        "owns_curriculum",
        "provides_service_teaching_for",
        "delivers_instruction_for",
        "contributes_to_llc_requirement",
        "provides_capstone_instruction_for",
    }
    payload = _assertion().to_dict()
    payload["predicate"] = "looks_similar_to"
    payload.pop("deterministic_fingerprint")
    with pytest.raises(ValueError):
        ContributionAssertion.from_dict(payload)


def test_temporal_dimensions_remain_distinct_in_serialization():
    payload = _scope().to_dict()
    assert payload["reporting_period"]["label"] == "AY 2024-25"
    assert payload["effective_period"]["label"] == "Current during AY 2024-25"
    assert payload["observation_period"]["start"] == "2024-08-01"
    assert payload["publication_time"] == "2025-07-01T12:00:00+00:00"
    assert ContributionTemporalScope.from_dict(payload) == _scope()


def test_measure_is_a_property_of_assertion_and_must_bind_known_evidence():
    assertion = _assertion()
    assert assertion.measures[0].value == 3
    assert "measures" in assertion.to_dict()

    bad_measure = ContributionMeasure(
        measure_id="measure:bad",
        measure_type="student_credit_hours",
        value=9,
        unit="SCH",
        definition="Explicit enrollment times explicit credits.",
        evidence_binding_ids=("evidence:missing",),
    )
    with pytest.raises(ValueError, match="unknown evidence"):
        ContributionAssertion(
            assertion_id="assertion:bad",
            subject=_department(),
            predicate=ContributionPredicate.DELIVERS_INSTRUCTION_FOR,
            object=_program(),
            temporal_scope=_scope(),
            evidence_bindings=(_binding(),),
            measures=(bad_measure,),
        )


def test_assertion_requires_evidence_and_governed_predicate():
    with pytest.raises(ValueError, match="requires evidence"):
        ContributionAssertion(
            assertion_id="assertion:no_evidence",
            subject=_department(),
            predicate=ContributionPredicate.ADMINISTERS_PROGRAM,
            object=_program(),
            temporal_scope=_scope(),
            evidence_bindings=(),
        )
    with pytest.raises(TypeError, match="predicate must be governed"):
        ContributionAssertion(
            assertion_id="assertion:raw_predicate",
            subject=_department(),
            predicate="supports_program",  # type: ignore[arg-type]
            object=_program(),
            temporal_scope=_scope(),
            evidence_bindings=(_binding(),),
        )


def test_all_assertions_must_describe_the_contribution_object_entity():
    other = InstitutionalEntity(
        entity_type="department",
        entity_id="academic_unit:department_english",
        published_name="Department of English",
    )
    assertion = ContributionAssertion(
        assertion_id="assertion:english",
        subject=other,
        predicate=ContributionPredicate.SUPPORTS_PROGRAM,
        object=_program(),
        temporal_scope=_scope(),
        evidence_bindings=(_binding(),),
    )
    with pytest.raises(ValueError, match="governed subject"):
        ContributionKnowledgeObject(
            contribution_object_id="contribution:wrong_subject",
            entity=_department(),
            temporal_scope=_scope(),
            assertions=(assertion,),
        )


def test_ordering_does_not_change_semantic_fingerprint():
    first_binding = _binding("evidence:a")
    second_binding = _binding("evidence:b")
    measure_a = ContributionMeasure(
        "measure:a", "section_count", 1, "sections", "Count.", {},
        ("evidence:a",),
    )
    measure_b = ContributionMeasure(
        "measure:b", "enrollment", 20, "students", "Enrollment.", {},
        ("evidence:b",),
    )

    def assertion(bindings, measures):
        return ContributionAssertion(
            assertion_id="assertion:ordered",
            subject=_department(),
            predicate=ContributionPredicate.DELIVERS_INSTRUCTION_FOR,
            object=_program(),
            temporal_scope=_scope(),
            evidence_bindings=bindings,
            measures=measures,
        )

    assert assertion(
        (first_binding, second_binding), (measure_a, measure_b)
    ).deterministic_fingerprint == assertion(
        (second_binding, first_binding), (measure_b, measure_a)
    ).deterministic_fingerprint


def test_tampered_serialized_fingerprint_is_rejected():
    payload = _object().to_dict()
    payload["deterministic_fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="does not match content"):
        ContributionKnowledgeObject.from_dict(payload)


def test_duplicate_semantic_ids_are_rejected():
    assertion = _assertion()
    with pytest.raises(ValueError, match="Duplicate contribution assertion"):
        ContributionKnowledgeObject(
            contribution_object_id="contribution:duplicate",
            entity=_department(),
            temporal_scope=_scope(),
            assertions=(assertion, assertion),
        )

    binding = _binding()
    with pytest.raises(ValueError, match="Duplicate contribution evidence"):
        ContributionAssertion(
            assertion_id="assertion:duplicate",
            subject=_department(),
            predicate=ContributionPredicate.SUPPORTS_PROGRAM,
            object=_program(),
            temporal_scope=_scope(),
            evidence_bindings=(binding, binding),
        )


def test_invalid_period_and_source_fingerprint_are_rejected():
    with pytest.raises(ValueError, match="start must not follow end"):
        ContributionPeriod(start="2025-01-01", end="2024-01-01")
    with pytest.raises(ValueError, match="Invalid source fingerprint"):
        ContributionEvidenceBinding(
            binding_id="evidence:bad",
            source_references=("source:1",),
            provenance={},
            builder="builder",
            builder_version="1",
            source_fingerprints={"source": "not-a-fingerprint"},
            derivation_basis="explicit source assertion",
        )
