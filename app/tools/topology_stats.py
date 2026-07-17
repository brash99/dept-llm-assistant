"""Display basic health statistics for institutional topology."""

from __future__ import annotations

from collections import Counter

from app.observatory.topology.bootstrap import build_bootstrap_catalog


def display_name(value) -> str:
    raw = getattr(value, "value", str(value))
    return raw.replace("_", " ").title()


def main() -> int:
    catalog = build_bootstrap_catalog()

    entities = list(catalog.entities)
    relationships = list(catalog.relationships)

    entity_types = Counter(
        display_name(entity.entity_type)
        for entity in entities
    )

    relationship_types = Counter(
        display_name(relationship.relationship_type)
        for relationship in relationships
    )

    degree = Counter()

    for relationship in relationships:
        degree[relationship.source_id] += 1
        degree[relationship.target_id] += 1

    average_degree = (
        sum(degree.values()) / len(entities)
        if entities
        else 0.0
    )

    highest_degree_entity = None
    highest_degree = 0

    if degree:
        highest_degree_id, highest_degree = max(
            degree.items(),
            key=lambda item: item[1],
        )
        highest_degree_entity = catalog.get_entity(highest_degree_id)

    print()
    print("=" * 72)
    print("Institutional Topology")
    print("=" * 72)

    print()
    print("Entities")
    print("-" * 8)

    for entity_type, count in sorted(entity_types.items()):
        print(f"{entity_type:.<36} {count:>4}")

    print(f"{'Total':.<36} {len(entities):>4}")

    print()
    print("Relationships")
    print("-" * 13)

    for relationship_type, count in sorted(
        relationship_types.items()
    ):
        print(f"{relationship_type:.<36} {count:>4}")

    print(f"{'Total':.<36} {len(relationships):>4}")

    print()
    print("Graph Structure")
    print("-" * 15)
    print(f"{'Average degree':.<36} {average_degree:>4.2f}")

    if highest_degree_entity is None:
        print(f"{'Highest-degree entity':.<36} (none)")
    else:
        print(
            f"{'Highest-degree entity':.<36} "
            f"{highest_degree_entity.name} ({highest_degree})"
        )

    isolated = [
        entity.name
        for entity in entities
        if degree[entity.id] == 0
    ]

    print(f"{'Isolated entities':.<36} {len(isolated):>4}")

    if isolated:
        for name in sorted(isolated):
            print(f"    • {name}")

    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
