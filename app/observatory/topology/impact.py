"""Deterministic institutional-impact reasoning over topology."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from .catalog import InstitutionalTopologyCatalog
from .entity import InstitutionalEntity
from .query import InstitutionalTopologyQuery


@dataclass(frozen=True)
class ImpactSummary:
    """Derived institutional meaning for one topology entity."""

    entity: InstitutionalEntity
    supports: tuple[str, ...]
    contributes_to: tuple[str, ...]
    supported_by: tuple[str, ...]
    contributed_to_by: tuple[str, ...]
    outgoing_relationships: int
    incoming_relationships: int
    total_relationships: int

    @property
    def institutional_reach(self) -> int:
        return self.total_relationships

    def narrative(self) -> str:
        """Produce a deterministic, non-LLM interpretation."""

        functions: list[str] = []

        if self.supports:
            functions.append("disciplinary or professional programs")

        if self.contributes_to:
            functions.append("university-wide curricular functions")

        if not functions:
            return (
                f"{self.entity.name} currently has no direct relationships "
                "represented in the institutional topology."
            )

        if len(functions) == 1:
            participation = functions[0]
        else:
            participation = f"{functions[0]} and {functions[1]}"

        review_areas = sorted(
            set(self.supports)
            | set(self.contributes_to)
        )

        narrative = (
            f"{self.entity.name} participates in {participation}. "
            f"The current topology records {self.total_relationships} direct "
            f"institutional relationship"
            f"{'' if self.total_relationships == 1 else 's'}."
        )

        if review_areas:
            narrative += (
                " Any significant change should evaluate possible effects on "
                + ", ".join(review_areas)
                + "."
            )

        return narrative

    def to_dict(self) -> dict[str, Any]:
        """Return the legacy dictionary representation."""

        return {
            "entity": self.entity,
            "supports": list(self.supports),
            "contributes_to": list(self.contributes_to),
            "supported_by": list(self.supported_by),
            "contributed_to_by": list(self.contributed_to_by),
            "outgoing_relationships": self.outgoing_relationships,
            "incoming_relationships": self.incoming_relationships,
            "total_relationships": self.total_relationships,
            "institutional_reach": self.institutional_reach,
            "narrative": self.narrative(),
        }

    def __getitem__(self, key: str) -> Any:
        """Preserve dictionary-style access used by existing demos."""

        return self.to_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())


class InstitutionalImpactService:
    """Derive meaning from stored institutional relationships."""

    def __init__(self, catalog: InstitutionalTopologyCatalog):
        self.catalog = catalog
        self.query = InstitutionalTopologyQuery(catalog)

    def summarize(self, entity_id: str) -> ImpactSummary:
        entity = self.catalog.get_entity(entity_id)

        outgoing = self.query.outgoing(entity_id)
        incoming = self.query.incoming(entity_id)

        supports = tuple(
            sorted(
                self.catalog.get_entity(relationship.target_id).name
                for relationship in self.query.supports(entity_id)
            )
        )

        contributes_to = tuple(
            sorted(
                self.catalog.get_entity(relationship.target_id).name
                for relationship in self.query.contributes_to(entity_id)
            )
        )

        supported_by = tuple(
            sorted(
                self.catalog.get_entity(relationship.source_id).name
                for relationship in self.query.supported_by(entity_id)
            )
        )

        contributed_to_by = tuple(
            sorted(
                self.catalog.get_entity(relationship.source_id).name
                for relationship in self.query.contributed_to_by(entity_id)
            )
        )

        return ImpactSummary(
            entity=entity,
            supports=supports,
            contributes_to=contributes_to,
            supported_by=supported_by,
            contributed_to_by=contributed_to_by,
            outgoing_relationships=len(outgoing),
            incoming_relationships=len(incoming),
            total_relationships=len(outgoing) + len(incoming),
        )
