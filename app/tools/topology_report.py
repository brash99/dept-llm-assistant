"""Pretty-print an institutional topology report."""

from __future__ import annotations

import argparse

from app.observatory.topology.bootstrap import build_bootstrap_catalog
from app.observatory.topology.service import InstitutionalTopologyService


def heading(title: str):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def section(title: str):
    print()
    print(title)
    print("-" * len(title))


def find_entity(catalog, query: str):
    q = query.casefold()

    for entity in catalog.entities:
        if entity.id.casefold() == q:
            return entity

    for entity in catalog.entities:
        if entity.name.casefold() == q:
            return entity

    for entity in catalog.entities:
        if q in entity.name.casefold():
            return entity

    return None


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("entity")

    args = parser.parse_args()

    catalog = build_bootstrap_catalog()
    service = InstitutionalTopologyService(catalog)

    entity = find_entity(catalog, args.entity)

    if entity is None:
        print("Entity not found.")
        return

    heading(entity.name)

    print(f"ID   : {entity.id}")
    print(f"Type : {entity.entity_type.value}")

    section("Outgoing Relationships")

    outgoing = service.outgoing(entity.id)

    if not outgoing:
        print("  (none)")

    for rel in outgoing:

        target = catalog.get_entity(rel.target_id)

        print()
        print(f"• {target.name}")
        print(f"    {rel.relationship_type.value}")
        print(f"    confidence : {rel.confidence:.2f}")
        print(f"    {rel.rationale}")

    section("Incoming Relationships")

    incoming = service.incoming(entity.id)

    if not incoming:
        print("  (none)")

    for rel in incoming:

        source = catalog.get_entity(rel.source_id)

        print()
        print(f"• {source.name}")
        print(f"    {rel.relationship_type.value}")
        print(f"    confidence : {rel.confidence:.2f}")
        print(f"    {rel.rationale}")


if __name__ == "__main__":
    main()
