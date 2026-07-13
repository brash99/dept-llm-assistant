#!/usr/bin/env python3

from pathlib import Path

from app.config import load_config
from app.control_plane import (
    ProgramCatalog,
    SemanticProgramNeighborhoodService,
)


CATALOG_PATH = Path("config/institutional_programs.yaml")


def show_neighbors(service, label, query, exclude_program_id=None):
    print("=" * 78)
    print(label)
    print(f"Semantic representation: {query}")
    print("-" * 78)

    neighbors = service.neighbors(
        query_text=query,
        exclude_program_id=exclude_program_id,
        limit=5,
    )

    for neighbor in neighbors:
        print(
            f"{neighbor.score:0.4f}  "
            f"{neighbor.program.name:30s} "
            f"[{neighbor.method}]"
        )

    print()


def main():
    config = load_config()

    catalog = ProgramCatalog.from_yaml(CATALOG_PATH)

    embedding_config = config.get("embedding", {})

    service = SemanticProgramNeighborhoodService(
        programs=catalog.all(),
        model_name=embedding_config.get(
            "model",
            "BAAI/bge-base-en-v1.5",
        ),
        device=embedding_config.get(
            "device",
            "cuda",
        ),
    )

    show_neighbors(
        service,
        "Existing Electrical Engineering program",
        (
            "An active undergraduate Electrical Engineering degree program "
            "involving circuits, electronics, signals, control systems, "
            "computer engineering, physics, laboratories, and ABET accreditation."
        ),
        exclude_program_id="program.electrical_engineering",
    )

    show_neighbors(
        service,
        "Proposed Mechanical Engineering program",
        (
            "A proposed undergraduate Mechanical Engineering degree program "
            "involving mechanics, thermodynamics, materials, manufacturing, "
            "engineering design, physics, laboratories, and ABET accreditation."
        ),
    )

    show_neighbors(
        service,
        "Proposed Artificial Intelligence program",
        (
            "A proposed undergraduate Artificial Intelligence degree program "
            "involving computer science, programming, algorithms, data science, "
            "machine learning, statistics, software engineering, and ethics."
        ),
    )


if __name__ == "__main__":
    main()
