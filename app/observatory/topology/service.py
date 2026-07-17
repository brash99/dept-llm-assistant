"""Query service for institutional topology."""

from __future__ import annotations

from .catalog import InstitutionalTopologyCatalog
from .relationship import (
    InstitutionalRelationship,
    RelationshipType,
)


class InstitutionalTopologyService:
    """Provides deterministic queries over institutional topology."""

    def __init__(self, catalog: InstitutionalTopologyCatalog):
        self.catalog = catalog

    def outgoing(
        self,
        entity_id: str,
        relationship_type: RelationshipType | None = None,
    ) -> tuple[InstitutionalRelationship, ...]:

        results = []

        for relationship in self.catalog.relationships:

            if relationship.source_id != entity_id:
                continue

            if (
                relationship_type is not None
                and relationship.relationship_type != relationship_type
            ):
                continue

            results.append(relationship)

        return tuple(results)

    def incoming(
        self,
        entity_id: str,
        relationship_type: RelationshipType | None = None,
    ) -> tuple[InstitutionalRelationship, ...]:

        results = []

        for relationship in self.catalog.relationships:

            if relationship.target_id != entity_id:
                continue

            if (
                relationship_type is not None
                and relationship.relationship_type != relationship_type
            ):
                continue

            results.append(relationship)

        return tuple(results)

    def between(
        self,
        source_id: str,
        target_id: str,
    ) -> tuple[InstitutionalRelationship, ...]:

        return tuple(

            relationship

            for relationship in self.catalog.relationships

            if relationship.source_id == source_id
            and relationship.target_id == target_id
        )
