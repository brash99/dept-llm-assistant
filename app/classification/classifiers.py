"""Deterministic semantic classifiers and the future LLM interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from app.classification.contracts import (
    ClassificationAssertion,
    ClassificationConfidence,
    ClassificationMethod,
    ClassificationProposal,
    EvidenceCitation,
)
from app.knowledge import KnowledgeObject
from app.semantic_identity import Authority, InstitutionalEntity, TemporalScope


def _citation(obj: KnowledgeObject, field: str, excerpt: Optional[str] = None) -> EvidenceCitation:
    page_numbers = getattr(obj, "page_numbers", ()) or ()
    return EvidenceCitation(
        source_kind="knowledge_object_field",
        field=field,
        knowledge_object_id=obj.id,
        text_excerpt=excerpt,
        page_reference=(
            ",".join(map(str, page_numbers)) if page_numbers else None
        ),
    )


def _assertion(
    obj: KnowledgeObject,
    field_name: str,
    value: Any,
    source_field,
    *,
    score: float = 1.0,
    method: ClassificationMethod = ClassificationMethod.ADAPTER,
) -> ClassificationAssertion:
    return ClassificationAssertion(
        field_name=field_name,
        value=value,
        confidence=ClassificationConfidence(
            score=score,
            rationale="Proposed from an explicit normalized Knowledge Object field.",
        ),
        classification_method=method,
        supporting_evidence=tuple(
            _citation(obj, field)
            for field in (
                (source_field,) if isinstance(source_field, str) else source_field
            )
        ),
    )


def _base_assertions(obj: KnowledgeObject) -> list[ClassificationAssertion]:
    return [_assertion(obj, "object_type", obj.object_type, "object_type")]


def _explicit_authority(obj: KnowledgeObject) -> Optional[Authority]:
    metadata = obj.metadata or {}
    source = obj.source or {}
    issuer = (
        metadata.get("issuing_authority")
        or metadata.get("source_organization")
        or source.get("issuing_authority")
        or source.get("source_organization")
    )
    if not issuer:
        return None
    return Authority(
        issuing_authority=str(issuer),
        authority_class=metadata.get("authority_class"),
        evidence_role=metadata.get("evidence_role"),
    )


class SemanticClassifier(ABC):
    name = "semantic_classifier"
    method = ClassificationMethod.UNKNOWN
    supported_object_types: Tuple[str, ...] = ()

    def supports(self, knowledge_object: KnowledgeObject) -> bool:
        return knowledge_object.object_type in self.supported_object_types

    @abstractmethod
    def classify(self, knowledge_object: KnowledgeObject) -> ClassificationProposal:
        raise NotImplementedError


class ConstitutionalKnowledgeClassifier(SemanticClassifier):
    name = "constitutional_knowledge_classifier"
    method = ClassificationMethod.ADAPTER
    supported_object_types = ("constitutional_knowledge",)

    def classify(self, obj: KnowledgeObject) -> ClassificationProposal:
        assertions = _base_assertions(obj)
        scopes = tuple(getattr(obj, "institutional_scope", ()) or ())
        if scopes:
            entities = [
                InstitutionalEntity(
                    entity_type="institution",
                    entity_id=f"published_institution:{name}",
                    published_name=str(name),
                ).to_dict()
                for name in scopes
            ]
            assertions.append(
                _assertion(obj, "institutional_entities", entities, "institutional_scope")
            )
        effective_from = getattr(obj, "effective_from", None)
        effective_until = getattr(obj, "effective_until", None)
        if effective_from or effective_until:
            temporal = TemporalScope(
                effective_from=effective_from, effective_until=effective_until
            )
            assertions.append(
                _assertion(
                    obj,
                    "temporal_scope",
                    temporal.to_dict(),
                    ("effective_from", "effective_until"),
                )
            )
        relevance = {
            key: value
            for key, value in {
                "constitutional_type": getattr(obj, "constitutional_type", None),
                "principles": list(getattr(obj, "principles", ()) or ()),
            }.items()
            if value is not None and value != []
        }
        if relevance:
            assertions.append(
                _assertion(
                    obj,
                    "institutional_relevance",
                    relevance,
                    ("constitutional_type", "principles"),
                )
            )
        authority = _explicit_authority(obj)
        if authority:
            assertions.append(_assertion(obj, "authority", authority.to_dict(), "metadata"))
        return ClassificationProposal(obj.id, tuple(assertions), self.name)


class FacultyObservationClassifier(SemanticClassifier):
    name = "faculty_observation_classifier"
    method = ClassificationMethod.ADAPTER
    supported_object_types = ("faculty_observation",)

    def classify(self, obj: KnowledgeObject) -> ClassificationProposal:
        assertions = _base_assertions(obj)
        entities = []
        display_name = getattr(obj, "display_name", None)
        if display_name:
            entities.append(
                InstitutionalEntity(
                    entity_type="faculty",
                    entity_id=f"faculty_observation:{obj.id}",
                    published_name=display_name,
                ).to_dict()
            )
        department = getattr(obj, "published_department", None)
        if department:
            entities.append(
                InstitutionalEntity(
                    entity_type="department",
                    entity_id=f"published_academic_unit:{department}",
                    published_name=department,
                ).to_dict()
            )
        if entities:
            assertions.append(
                _assertion(
                    obj,
                    "institutional_entities",
                    entities,
                    tuple(
                        field
                        for field, value in (
                            ("display_name", display_name),
                            ("published_department", department),
                        )
                        if value
                    ),
                )
            )
        snapshot = getattr(obj, "snapshot_date", None)
        if snapshot:
            assertions.append(
                _assertion(
                    obj,
                    "temporal_scope",
                    TemporalScope(as_of=snapshot, published_label=snapshot).to_dict(),
                    "snapshot_date",
                )
            )
        authority = _explicit_authority(obj)
        if authority:
            assertions.append(_assertion(obj, "authority", authority.to_dict(), "metadata"))
        return ClassificationProposal(obj.id, tuple(assertions), self.name)


class CourseOfferingObservationClassifier(SemanticClassifier):
    name = "course_offering_observation_classifier"
    method = ClassificationMethod.ADAPTER
    supported_object_types = ("course_offering_observation",)

    def classify(self, obj: KnowledgeObject) -> ClassificationProposal:
        assertions = _base_assertions(obj)
        label = getattr(obj, "course_code", None)
        section = getattr(obj, "section", None)
        if label:
            published_name = f"{label} {section}".strip() if section else label
            entity = InstitutionalEntity(
                entity_type="course_offering",
                entity_id=f"course_offering:{obj.id}",
                published_name=published_name,
            )
            assertions.append(
                _assertion(
                    obj,
                    "institutional_entities",
                    [entity.to_dict()],
                    ("course_code", "section") if section else "course_code",
                )
            )
        term = getattr(obj, "academic_term", None)
        if term:
            assertions.append(
                _assertion(
                    obj,
                    "temporal_scope",
                    TemporalScope(academic_term=term, published_label=term).to_dict(),
                    "academic_term",
                )
            )
        authority = _explicit_authority(obj)
        if authority:
            assertions.append(_assertion(obj, "authority", authority.to_dict(), "metadata"))
        return ClassificationProposal(obj.id, tuple(assertions), self.name)


class CatalogObservationClassifier(SemanticClassifier):
    name = "catalog_observation_classifier"
    method = ClassificationMethod.ADAPTER
    supported_object_types = (
        "catalog_observation",
        "academic_unit_observation",
        "department_faculty_roster_observation",
        "catalog_faculty_observation",
    )

    def classify(self, obj: KnowledgeObject) -> ClassificationProposal:
        assertions = _base_assertions(obj)
        entities = []
        unit = getattr(obj, "academic_unit", None)
        if obj.object_type == "academic_unit_observation":
            published_name = getattr(obj, "published_name", None)
            if published_name:
                entities.append(
                    InstitutionalEntity(
                        entity_type="academic_unit",
                        entity_id=f"published_academic_unit:{published_name}",
                        published_name=published_name,
                    ).to_dict()
                )
        elif obj.object_type == "department_faculty_roster_observation" and unit:
            entities.append(
                InstitutionalEntity(
                    entity_type="academic_unit",
                    entity_id=f"published_academic_unit:{unit}",
                    published_name=unit,
                ).to_dict()
            )
        elif obj.object_type == "catalog_faculty_observation":
            name = getattr(obj, "published_name", None)
            if name:
                entities.append(
                    InstitutionalEntity(
                        entity_type="faculty",
                        entity_id=f"catalog_faculty_observation:{obj.id}",
                        published_name=name,
                    ).to_dict()
                )
            if unit:
                entities.append(
                    InstitutionalEntity(
                        entity_type="academic_unit",
                        entity_id=f"published_academic_unit:{unit}",
                        published_name=unit,
                    ).to_dict()
                )
        if entities:
            assertions.append(
                _assertion(
                    obj,
                    "institutional_entities",
                    entities,
                    tuple(
                        field
                        for field in ("published_name", "academic_unit")
                        if getattr(obj, field, None)
                    ),
                )
            )
        year = getattr(obj, "catalog_year", None)
        if year:
            assertions.append(
                _assertion(
                    obj,
                    "temporal_scope",
                    TemporalScope(published_label=year).to_dict(),
                    "catalog_year",
                )
            )
        authority = _explicit_authority(obj)
        if authority:
            assertions.append(_assertion(obj, "authority", authority.to_dict(), "metadata"))
        return ClassificationProposal(obj.id, tuple(assertions), self.name)


class DeterministicSemanticClassifier(SemanticClassifier):
    """Route known normalized object types to factual adapter classifiers."""

    name = "deterministic_semantic_classifier"
    method = ClassificationMethod.DETERMINISTIC_RULE

    def __init__(self, classifiers: Optional[Sequence[SemanticClassifier]] = None):
        self.classifiers = tuple(
            classifiers
            or (
                ConstitutionalKnowledgeClassifier(),
                FacultyObservationClassifier(),
                CourseOfferingObservationClassifier(),
                CatalogObservationClassifier(),
            )
        )

    def supports(self, knowledge_object: KnowledgeObject) -> bool:
        return any(item.supports(knowledge_object) for item in self.classifiers)

    def classify(self, knowledge_object: KnowledgeObject) -> ClassificationProposal:
        classifier = next(
            (item for item in self.classifiers if item.supports(knowledge_object)), None
        )
        if classifier is None:
            raise ValueError(
                f"No deterministic classifier for {knowledge_object.object_type!r}"
            )
        return classifier.classify(knowledge_object)


class MockLLMSemanticClassifier(SemanticClassifier):
    """Interface placeholder; no prompt, model, network, or parsing behavior."""

    name = "mock_llm_semantic_classifier"
    method = ClassificationMethod.LLM

    def supports(self, knowledge_object: KnowledgeObject) -> bool:
        return True

    def classify(self, knowledge_object: KnowledgeObject) -> ClassificationProposal:
        raise NotImplementedError(
            "LLM semantic classification is an interface stub; no backend is configured"
        )

    def proposal_from_assertions(
        self,
        knowledge_object: KnowledgeObject,
        assertions: Iterable[ClassificationAssertion],
    ) -> ClassificationProposal:
        """Adapt already-cited future LLM output to the common proposal contract."""
        assertions = tuple(assertions)
        if any(
            assertion.classification_method != ClassificationMethod.LLM
            for assertion in assertions
        ):
            raise ValueError("Mock LLM proposals must contain LLM assertions")
        return ClassificationProposal(
            knowledge_object_id=knowledge_object.id,
            assertions=assertions,
            classifier_name=self.name,
        )


__all__ = [
    "CatalogObservationClassifier",
    "ConstitutionalKnowledgeClassifier",
    "CourseOfferingObservationClassifier",
    "DeterministicSemanticClassifier",
    "FacultyObservationClassifier",
    "MockLLMSemanticClassifier",
    "SemanticClassifier",
]
