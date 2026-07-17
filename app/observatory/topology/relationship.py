"""Institutional relationships and their provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RelationshipType(str, Enum):
    """Types of institutional connections represented by the Observatory."""

    SUPPORTS = "supports"
    REQUIRES = "requires"
    CONTRIBUTES_TO = "contributes_to"
    DEPENDS_ON = "depends_on"
    ACCREDITS = "accredits"
    SHARES_RESOURCES_WITH = "shares_resources_with"


@dataclass(frozen=True)
class EvidenceReference:
    """A source supporting an institutional relationship."""

    source_id: str
    label: str
    locator: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class InstitutionalRelationship:
    """A directed, evidence-backed relationship between two entities."""

    source_id: str
    target_id: str
    relationship_type: RelationshipType
    confidence: float
    rationale: str
    evidence: tuple[EvidenceReference, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError(
                "InstitutionalRelationship.source_id must not be empty."
            )

        if not self.target_id.strip():
            raise ValueError(
                "InstitutionalRelationship.target_id must not be empty."
            )

        if self.source_id == self.target_id:
            raise ValueError(
                "InstitutionalRelationship cannot connect an entity to itself."
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "InstitutionalRelationship.confidence must be between 0 and 1."
            )

        if not self.rationale.strip():
            raise ValueError(
                "InstitutionalRelationship.rationale must not be empty."
            )
