#!/usr/bin/env python3

from pathlib import Path

from app.control_plane import ProgramCatalog, ProgramOrientationService


CATALOG_PATH = Path("config/institutional_programs.yaml")


def show_orientation(
    service: ProgramOrientationService,
    question: str,
    proposed_program_name=None,
) -> None:
    result = service.orient(
        question=question,
        proposed_program_name=proposed_program_name,
    )

    print("=" * 78)
    print(question)
    print("-" * 78)

    if result.resolution.program:
        program = result.resolution.program
        print(f"Resolved program : {program.name}")
        print(f"Status           : {program.status}")
        print(f"Match type       : {result.resolution.match_type}")
        print(f"Confidence       : {result.resolution.confidence:.2f}")
    else:
        print("Resolved program : <none>")
        print(f"Proposed name    : {result.proposed_program_name}")

    print()
    print("Warnings")
    for warning in result.warnings:
        print(f"  - {warning}")

    print()
    print("Provisional neighbors")
    if result.neighbors:
        for neighbor in result.neighbors:
            print(
                f"  {neighbor.score:0.3f}  "
                f"{neighbor.program.name} "
                f"[{neighbor.method}]"
            )
    else:
        print("  <none>")

    print()
    print("Expected evidence")
    for category in result.expected_evidence:
        print(f"  - {category}")

    print()


def main() -> None:
    catalog = ProgramCatalog.from_yaml(CATALOG_PATH)
    service = ProgramOrientationService(catalog)

    show_orientation(
        service,
        "What additional resources would be required to start "
        "an Electrical Engineering major?",
    )

    show_orientation(
        service,
        "What additional resources would be required to start "
        "a Mechanical Engineering major?",
        proposed_program_name="Mechanical Engineering",
    )

    show_orientation(
        service,
        "Should we create a new Artificial Intelligence program?",
        proposed_program_name="Artificial Intelligence",
    )


if __name__ == "__main__":
    main()
