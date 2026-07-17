"""Catalog of institutional entities and relationships."""

from __future__ import annotations

from .entity import InstitutionalEntity
from .relationship import InstitutionalRelationship


class InstitutionalTopologyCatalog:
    """Simple in-memory catalog of institutional topology."""

    def __init__(self) -> None:
        self._entities: dict[str, InstitutionalEntity] = {}
        self._relationships: list[InstitutionalRelationship] = []

    @property
    def entities(self) -> tuple[InstitutionalEntity, ...]:
        return tuple(self._entities.values())

    @property
    def relationships(self) -> tuple[InstitutionalRelationship, ...]:
        return tuple(self._relationships)

    def add_entity(self, entity: InstitutionalEntity) -> None:
        self._entities[entity.id] = entity

    def add_relationship(
        self,
        relationship: InstitutionalRelationship,
    ) -> None:
        if relationship.source_id not in self._entities:
            raise KeyError(
                f"Unknown source entity: {relationship.source_id}"
            )

        if relationship.target_id not in self._entities:
            raise KeyError(
                f"Unknown target entity: {relationship.target_id}"
            )

        self._relationships.append(relationship)

    def get_entity(
        self,
        entity_id: str,
    ) -> InstitutionalEntity:
        return self._entities[entity_id]
