"""Demonstrate topology reasoning."""

from __future__ import annotations

import argparse

from app.observatory.topology.bootstrap import build_bootstrap_catalog
from app.observatory.topology.impact import InstitutionalImpactService


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("entity")

    args = parser.parse_args()

    catalog = build_bootstrap_catalog()

    entity = None

    for e in catalog.entities:
        if (
            e.id.casefold() == args.entity.casefold()
            or e.name.casefold() == args.entity.casefold()
        ):
            entity = e
            break

    if entity is None:
        print("Entity not found.")
        return

    service = InstitutionalImpactService(catalog)

    impact = service.summarize(entity.id)

    print()
    print("=" * 72)
    print("Institutional Impact Summary")
    print("=" * 72)
    print()

    print("Entity")
    print(f"    {entity.name}")
    print()

    print("Supports")

    if impact["supports"]:
        for item in impact["supports"]:
            print(f"    • {item}")
    else:
        print("    (none)")

    print()

    print("Contributes To")

    if impact["contributes_to"]:
        for item in impact["contributes_to"]:
            print(f"    • {item}")
    else:
        print("    (none)")

    print()

    print("Relationship Counts")

    print(f"    Outgoing : {impact['outgoing_relationships']}")
    print(f"    Incoming : {impact['incoming_relationships']}")
    print(f"    Total    : {impact['total_relationships']}")
    print()


if __name__ == "__main__":
    main()
