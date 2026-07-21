"""Simple command-line explorer for the institutional topology."""

from __future__ import annotations

import argparse
import sys

from app.observatory.topology.bootstrap import build_bootstrap_catalog
from app.observatory.topology.service import InstitutionalTopologyService


def normalize(value: str) -> str:
    """Normalize text for simple case-insensitive matching."""

    return " ".join(value.casefold().split())


def find_entity(catalog, query: str):
    """Find an entity by exact ID, exact name, or partial name."""

    normalized_query = normalize(query)

    try:
        exact_id_match = catalog.get_entity(query)
    except KeyError:
        exact_id_match = None

    if exact_id_match is not None:
        return exact_id_match

    exact_name_matches = [
        entity
        for entity in catalog.entities
        if normalize(entity.name) == normalized_query
    ]

    if len(exact_name_matches) == 1:
        return exact_name_matches[0]

    partial_matches = [
        entity
        for entity in catalog.entities
        if normalized_query in normalize(entity.name)
    ]

    if len(partial_matches) == 1:
        return partial_matches[0]

    if len(partial_matches) > 1:
        print(f"Multiple entities match {query!r}:")
        for entity in sorted(partial_matches, key=lambda item: item.name):
            print(f"  - {entity.name} ({entity.id})")
        return None

    return None


def print_relationship(
    catalog,
    relationship,
    *,
    outgoing: bool,
) -> None:
    """Print one relationship in a readable form."""

    if outgoing:
        related_entity = catalog.get_entity(relationship.target_id)
        direction = "→"
    else:
        related_entity = catalog.get_entity(relationship.source_id)
        direction = "←"

    related_name = (
        related_entity.name
        if related_entity is not None
        else (
            relationship.target_id
            if outgoing
            else relationship.source_id
        )
    )

    print(
        f"  {direction} "
        f"{relationship.relationship_type.value:16s} "
        f"{related_name}"
    )
    print(f"      confidence: {relationship.confidence:.2f}")
    print(f"      rationale:  {relationship.rationale}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Explore the ISO institutional topology."
    )
    parser.add_argument(
        "entity",
        help="Entity name or ID, such as Physics or academic_unit:sec",
    )
    args = parser.parse_args()

    catalog = build_bootstrap_catalog()
    service = InstitutionalTopologyService(catalog)

    entity = find_entity(catalog, args.entity)

    if entity is None:
        print(f"No unique entity found for {args.entity!r}.", file=sys.stderr)
        return 1

    outgoing = service.outgoing(entity.id)
    incoming = service.incoming(entity.id)

    print()
    print("=" * 72)
    print(entity.name)
    print("=" * 72)
    print(f"ID:   {entity.id}")
    print(f"Type: {entity.entity_type.value}")

    print()
    print("Outgoing relationships")
    print("-" * 72)

    if outgoing:
        for relationship in outgoing:
            print_relationship(
                catalog,
                relationship,
                outgoing=True,
            )
    else:
        print("  None")

    print()
    print("Incoming relationships")
    print("-" * 72)

    if incoming:
        for relationship in incoming:
            print_relationship(
                catalog,
                relationship,
                outgoing=False,
            )
    else:
        print("  None")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
