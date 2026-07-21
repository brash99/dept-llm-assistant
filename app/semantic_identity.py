"""Authoritative factual semantic identity for ISO Knowledge Objects.

These contracts state what an object is and what published institutional facts
it carries. They do not assign retrieval eligibility or derive conclusions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class InstitutionalEntity:
    """A stable reference to an entity represented in institutional evidence."""

    entity_type: str
    entity_id: str
    published_name: Optional[str] = None
    identifiers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entity_type.strip():
            raise ValueError("Institutional entity type must not be empty")
        if not self.entity_id.strip():
            raise ValueError("Institutional entity id must not be empty")

    def to_dict(self) -> Dict[str, Any]:
        return {
            key: value
            for key, value in {
                "entity_type": self.entity_type,
                "entity_id": self.entity_id,
                "published_name": self.published_name,
                "identifiers": dict(self.identifiers),
            }.items()
            if value is not None and value != {}
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InstitutionalEntity":
        return cls(
            entity_type=str(value["entity_type"]),
            entity_id=str(value["entity_id"]),
            published_name=value.get("published_name"),
            identifiers=dict(value.get("identifiers") or {}),
        )


@dataclass(frozen=True)
class OrganizationalRelationship:
    """A factual relationship assertion preserved from available evidence."""

    relationship_type: str
    target: str
    published_label: Optional[str] = None
    source: Optional[str] = None
    evidence_reference: Optional[str] = None
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.relationship_type.strip():
            raise ValueError("Relationship type must not be empty")
        if not self.target.strip():
            raise ValueError("Relationship target must not be empty")

    def to_dict(self) -> Dict[str, Any]:
        return {
            key: value
            for key, value in {
                "relationship_type": self.relationship_type,
                "source": self.source,
                "target": self.target,
                "published_label": self.published_label,
                "evidence_reference": self.evidence_reference,
                "effective_from": self.effective_from,
                "effective_until": self.effective_until,
            }.items()
            if value is not None
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OrganizationalRelationship":
        return cls(
            relationship_type=str(value["relationship_type"]),
            target=str(value["target"]),
            published_label=value.get("published_label"),
            source=value.get("source"),
            evidence_reference=value.get("evidence_reference"),
            effective_from=value.get("effective_from"),
            effective_until=value.get("effective_until"),
        )


@dataclass(frozen=True)
class Authority:
    """Published or curated factual authority metadata for an object."""

    issuing_authority: str
    authority_class: Optional[str] = None
    evidence_role: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.issuing_authority.strip():
            raise ValueError("Issuing authority must not be empty")

    def to_dict(self) -> Dict[str, Any]:
        return {
            key: value
            for key, value in {
                "issuing_authority": self.issuing_authority,
                "authority_class": self.authority_class,
                "evidence_role": self.evidence_role,
            }.items()
            if value is not None
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Authority":
        return cls(
            issuing_authority=str(value["issuing_authority"]),
            authority_class=value.get("authority_class"),
            evidence_role=value.get("evidence_role"),
        )


@dataclass(frozen=True)
class TemporalScope:
    """The published time period or as-of point described by an object."""

    as_of: Optional[str] = None
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    academic_term: Optional[str] = None
    published_label: Optional[str] = None
    reporting_period: Optional[str] = None

    def __post_init__(self) -> None:
        if not any(
            (
                self.as_of,
                self.effective_from,
                self.effective_until,
                self.academic_term,
                self.published_label,
                self.reporting_period,
            )
        ):
            raise ValueError("Temporal scope must contain at least one factual value")

    def to_dict(self) -> Dict[str, Any]:
        return {
            key: value
            for key, value in {
                "as_of": self.as_of,
                "effective_from": self.effective_from,
                "effective_until": self.effective_until,
                "academic_term": self.academic_term,
                "published_label": self.published_label,
                "reporting_period": self.reporting_period,
            }.items()
            if value is not None
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TemporalScope":
        return cls(
            as_of=value.get("as_of"),
            effective_from=value.get("effective_from"),
            effective_until=value.get("effective_until"),
            academic_term=value.get("academic_term"),
            published_label=value.get("published_label"),
            reporting_period=value.get("reporting_period"),
        )


@dataclass(frozen=True)
class SemanticIdentity:
    """Authoritative factual identity carried by one Knowledge Object."""

    object_type: str
    institutional_entities: Tuple[InstitutionalEntity, ...] = ()
    organizational_relationships: Tuple[OrganizationalRelationship, ...] = ()
    decision_domains: Tuple[str, ...] = ()
    authority: Optional[Authority] = None
    temporal_scope: Optional[TemporalScope] = None
    institutional_relevance: Mapping[str, Any] = field(default_factory=dict)
    source_family: Optional[str] = None
    document_type: Optional[str] = None
    institutional_role: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.object_type.strip():
            raise ValueError("Semantic identity object_type must not be empty")
        object.__setattr__(self, "institutional_entities", tuple(self.institutional_entities))
        object.__setattr__(
            self, "organizational_relationships", tuple(self.organizational_relationships)
        )
        object.__setattr__(self, "decision_domains", tuple(self.decision_domains))
        if not all(
            isinstance(entity, InstitutionalEntity)
            for entity in self.institutional_entities
        ):
            raise TypeError("institutional_entities must contain InstitutionalEntity values")
        if not all(
            isinstance(relationship, OrganizationalRelationship)
            for relationship in self.organizational_relationships
        ):
            raise TypeError(
                "organizational_relationships must contain OrganizationalRelationship values"
            )
        if self.authority is not None and not isinstance(self.authority, Authority):
            raise TypeError("authority must be an Authority")
        if self.temporal_scope is not None and not isinstance(
            self.temporal_scope, TemporalScope
        ):
            raise TypeError("temporal_scope must be a TemporalScope")

    def to_dict(self) -> Dict[str, Any]:
        return {
            key: value
            for key, value in {
                "object_type": self.object_type,
                "institutional_entities": [
                    entity.to_dict() for entity in self.institutional_entities
                ],
                "organizational_relationships": [
                    relationship.to_dict()
                    for relationship in self.organizational_relationships
                ],
                "decision_domains": list(self.decision_domains),
                "authority": self.authority.to_dict() if self.authority else None,
                "temporal_scope": (
                    self.temporal_scope.to_dict() if self.temporal_scope else None
                ),
                "institutional_relevance": dict(self.institutional_relevance),
                "source_family": self.source_family,
                "document_type": self.document_type,
                "institutional_role": self.institutional_role,
            }.items()
            if value is not None and value != [] and value != {}
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SemanticIdentity":
        return cls(
            object_type=str(value["object_type"]),
            institutional_entities=tuple(
                InstitutionalEntity.from_dict(item)
                for item in value.get("institutional_entities") or ()
            ),
            organizational_relationships=tuple(
                OrganizationalRelationship.from_dict(item)
                for item in value.get("organizational_relationships") or ()
            ),
            decision_domains=tuple(map(str, value.get("decision_domains") or ())),
            authority=(
                Authority.from_dict(value["authority"])
                if value.get("authority") else None
            ),
            temporal_scope=(
                TemporalScope.from_dict(value["temporal_scope"])
                if value.get("temporal_scope") else None
            ),
            institutional_relevance=dict(value.get("institutional_relevance") or {}),
            source_family=value.get("source_family"),
            document_type=value.get("document_type"),
            institutional_role=value.get("institutional_role"),
        )


__all__ = [
    "Authority",
    "InstitutionalEntity",
    "OrganizationalRelationship",
    "SemanticIdentity",
    "TemporalScope",
]
