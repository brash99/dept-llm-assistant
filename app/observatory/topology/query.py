"""Reusable queries and traversal over institutional topology."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Optional

from .catalog import InstitutionalTopologyCatalog
from .entity import InstitutionalEntity
from .relationship import InstitutionalRelationship, RelationshipType
from .service import InstitutionalTopologyService


@dataclass(frozen=True)
class TraversalResult:
    """One entity reached during graph traversal."""

    entity: InstitutionalEntity
    depth: int
    via_relationship: Optional[InstitutionalRelationship] = None


class InstitutionalTopologyQuery:
    """Retrieve facts from an InstitutionalTopologyCatalog.

    This class answers structural questions about the graph. It does not
    interpret institutional significance; that belongs in reasoning services
    such as InstitutionalImpactService.
    """

    def __init__(self, catalog: InstitutionalTopologyCatalog):
        self.catalog = catalog
        self.service = InstitutionalTopologyService(catalog)

    def find_entity(self, query: str) -> Optional[InstitutionalEntity]:
        """Find an entity by ID, exact name, or unique partial name."""

        normalized = query.strip().casefold()

        if not normalized:
            return None

        try:
            return self.catalog.get_entity(query)
        except KeyError:
            pass

        exact_name_matches = [
            entity
            for entity in self.catalog.entities
            if entity.name.casefold() == normalized
        ]

        if len(exact_name_matches) == 1:
            return exact_name_matches[0]

        partial_matches = [
            entity
            for entity in self.catalog.entities
            if normalized in entity.name.casefold()
        ]

        if len(partial_matches) == 1:
            return partial_matches[0]

        return None

    def outgoing(
        self,
        entity_id: str,
        relationship_type: Optional[RelationshipType] = None,
    ) -> list[InstitutionalRelationship]:
        relationships = list(self.service.outgoing(entity_id))
        return self._filter_relationships(relationships, relationship_type)

    def incoming(
        self,
        entity_id: str,
        relationship_type: Optional[RelationshipType] = None,
    ) -> list[InstitutionalRelationship]:
        relationships = list(self.service.incoming(entity_id))
        return self._filter_relationships(relationships, relationship_type)

    def supports(self, entity_id: str) -> list[InstitutionalRelationship]:
        return self.outgoing(entity_id, RelationshipType.SUPPORTS)

    def contributes_to(self, entity_id: str) -> list[InstitutionalRelationship]:
        return self.outgoing(entity_id, RelationshipType.CONTRIBUTES_TO)

    def supported_by(self, entity_id: str) -> list[InstitutionalRelationship]:
        return self.incoming(entity_id, RelationshipType.SUPPORTS)

    def contributed_to_by(
        self,
        entity_id: str,
    ) -> list[InstitutionalRelationship]:
        return self.incoming(entity_id, RelationshipType.CONTRIBUTES_TO)

    def neighbors(
        self,
        entity_id: str,
    ) -> list[InstitutionalEntity]:
        """Return unique entities directly connected to an entity."""

        neighbor_ids: set[str] = set()

        for relationship in self.outgoing(entity_id):
            neighbor_ids.add(relationship.target_id)

        for relationship in self.incoming(entity_id):
            neighbor_ids.add(relationship.source_id)

        return sorted(
            (
                self.catalog.get_entity(neighbor_id)
                for neighbor_id in neighbor_ids
            ),
            key=lambda entity: entity.name.casefold(),
        )

    def traverse(
        self,
        entity_id: str,
        max_depth: int = 1,
        direction: str = "both",
    ) -> list[TraversalResult]:
        """Breadth-first traversal from an entity.

        Parameters
        ----------
        entity_id:
            Starting entity ID.
        max_depth:
            Maximum number of relationship steps.
        direction:
            ``outgoing``, ``incoming``, or ``both``.
        """

        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")

        if direction not in {"outgoing", "incoming", "both"}:
            raise ValueError(
                "direction must be 'outgoing', 'incoming', or 'both'"
            )

        self.catalog.get_entity(entity_id)

        visited = {entity_id}
        queue = deque([(entity_id, 0)])
        results: list[TraversalResult] = []

        while queue:
            current_id, depth = queue.popleft()

            if depth >= max_depth:
                continue

            edges: list[tuple[str, InstitutionalRelationship]] = []

            if direction in {"outgoing", "both"}:
                edges.extend(
                    (relationship.target_id, relationship)
                    for relationship in self.outgoing(current_id)
                )

            if direction in {"incoming", "both"}:
                edges.extend(
                    (relationship.source_id, relationship)
                    for relationship in self.incoming(current_id)
                )

            for neighbor_id, relationship in edges:
                if neighbor_id in visited:
                    continue

                visited.add(neighbor_id)
                neighbor = self.catalog.get_entity(neighbor_id)
                neighbor_depth = depth + 1

                results.append(
                    TraversalResult(
                        entity=neighbor,
                        depth=neighbor_depth,
                        via_relationship=relationship,
                    )
                )

                queue.append((neighbor_id, neighbor_depth))

        return results

    @staticmethod
    def _filter_relationships(
        relationships: Iterable[InstitutionalRelationship],
        relationship_type: Optional[RelationshipType],
    ) -> list[InstitutionalRelationship]:
        if relationship_type is None:
            return list(relationships)

        return [
            relationship
            for relationship in relationships
            if relationship.relationship_type == relationship_type
        ]
