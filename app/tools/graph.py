"""Explore the institutional topology from the command line."""

from __future__ import annotations

import argparse
from collections import defaultdict

from app.observatory.topology.bootstrap import build_bootstrap_catalog
from app.observatory.topology.query import InstitutionalTopologyQuery


def relationship_label(relationship, root_id: str) -> str:
    label = relationship.relationship_type.value

    if relationship.target_id == root_id:
        if label == "supports":
            return "supported_by"
        if label == "contributes_to":
            return "contributed_to_by"
        return f"incoming_{label}"

    return label


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Explore institutional topology."
    )
    parser.add_argument("entity")
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Traversal depth; default is 1.",
    )
    parser.add_argument(
        "--direction",
        choices=("outgoing", "incoming", "both"),
        default="both",
    )
    args = parser.parse_args()

    catalog = build_bootstrap_catalog()
    query = InstitutionalTopologyQuery(catalog)

    entity = query.find_entity(args.entity)

    if entity is None:
        print(f"Entity not found or query is ambiguous: {args.entity}")
        return 1

    print()
    print(entity.name)
    print("=" * len(entity.name))

    if args.depth == 1:
        grouped = defaultdict(list)

        for relationship in query.outgoing(entity.id):
            grouped[relationship_label(relationship, entity.id)].append(
                catalog.get_entity(relationship.target_id)
            )

        for relationship in query.incoming(entity.id):
            grouped[relationship_label(relationship, entity.id)].append(
                catalog.get_entity(relationship.source_id)
            )

        if not grouped:
            print("\n(no direct relationships)")
            return 0

        for label in sorted(grouped):
            print()
            print(label)
            print("-" * len(label))

            for connected_entity in sorted(
                grouped[label],
                key=lambda item: item.name.casefold(),
            ):
                print(f"  • {connected_entity.name}")

        return 0

    traversal = query.traverse(
        entity.id,
        max_depth=args.depth,
        direction=args.direction,
    )

    if not traversal:
        print("\n(no reachable entities)")
        return 0

    for depth in range(1, args.depth + 1):
        level = [result for result in traversal if result.depth == depth]

        if not level:
            continue

        print()
        print(f"Depth {depth}")
        print("-" * 7)

        for result in sorted(
            level,
            key=lambda item: item.entity.name.casefold(),
        ):
            relationship = result.via_relationship
            assert relationship is not None

            print(
                f"  • {result.entity.name} "
                f"[{relationship.relationship_type.value}]"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
