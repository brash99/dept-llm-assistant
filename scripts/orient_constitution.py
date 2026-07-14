#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from app.config import load_config
from app.constitution import (
    ConstitutionalCatalog,
    ConstitutionalOrientationService,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate an inspectable constitutional "
            "orientation for an institutional question."
        )
    )

    parser.add_argument(
        "question",
    )

    parser.add_argument(
        "--minimum-score",
        type=float,
        default=0.12,
    )

    parser.add_argument(
        "--max-matches",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--json",
        action="store_true",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config()

    project_root = Path(
        config["project"]["root"]
    )

    constitutional_dir = (
        project_root
        / config["storage"].get(
            "constitutional",
            "storage/constitutional",
        )
    )

    catalog = (
        ConstitutionalCatalog.from_directory(
            constitutional_dir
        )
    )

    service = ConstitutionalOrientationService(
        catalog=catalog,
        minimum_score=args.minimum_score,
        max_matches=args.max_matches,
    )

    orientation = service.orient(
        args.question
    )

    if args.json:
        print(
            json.dumps(
                orientation.to_dict(),
                indent=2,
            )
        )
        return

    print()
    print("ISO Constitutional Orientation")
    print("=" * 72)
    print(f"Question:   {orientation.question}")
    print(
        f"Confidence: "
        f"{orientation.confidence:.2f}"
    )
    print()

    if not orientation.matches:
        print(
            "No constitutional principles "
            "were identified."
        )
    else:
        print("Potentially Relevant Principles")
        print("-" * 72)

        for rank, match in enumerate(
            orientation.matches,
            start=1,
        ):
            print(
                f"{rank}. {match.principle}"
            )
            print(
                f"   Score: {match.score:.4f}"
            )
            print(
                "   Matched terms: "
                + ", ".join(
                    match.matched_terms
                )
            )
            print(
                f"   Source: "
                f"{match.constitutional_object_title}"
            )
            print()

    print("Notes")
    print("-" * 72)

    for note in orientation.notes:
        print(f"- {note}")


if __name__ == "__main__":
    main()
