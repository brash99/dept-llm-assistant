#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from app.discovery import (
    CandidateRegistry,
    CandidateStatus,
)


DEFAULT_REGISTRY = Path(
    "storage/discovery_candidates/"
    "schev.jsonl"
)


def short_id(candidate_id: str) -> str:
    return candidate_id.split(":", 1)[-1][:12]


def print_candidates(
    candidates: Iterable,
) -> None:
    candidates = list(candidates)

    if not candidates:
        print("No matching candidates.")
        return

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        print()
        print("=" * 76)
        print(
            f"{index}. {candidate.title}"
        )
        print("=" * 76)
        print(
            f"ID       : {candidate.id}"
        )
        print(
            f"Short ID : {short_id(candidate.id)}"
        )
        print(
            f"Status   : {candidate.status.value}"
        )
        print(
            f"Provider : "
            f"{candidate.discovery_provider}"
        )
        print(
            f"Source   : "
            f"{candidate.source_organization}"
        )
        print(f"URL      : {candidate.url}")

        if candidate.discovery_query:
            print(
                f"Query    : "
                f"{candidate.discovery_query}"
            )

        if candidate.publication_date:
            print(
                f"Published: "
                f"{candidate.publication_date}"
            )

        if candidate.topics:
            print(
                "Topics   : "
                + ", ".join(candidate.topics)
            )

        if candidate.decision_domains:
            print(
                "Domains  : "
                + ", ".join(
                    candidate.decision_domains
                )
            )

        if candidate.description:
            print()
            print(candidate.description)

        if candidate.review_notes:
            print()
            print(
                "Review notes: "
                f"{candidate.review_notes}"
            )


def resolve_candidate_id(
    registry: CandidateRegistry,
    supplied_id: str,
) -> str:
    """
    Accept either the complete candidate ID or a unique
    hexadecimal prefix.
    """
    candidates = registry.latest()

    exact = [
        candidate.id
        for candidate in candidates
        if candidate.id == supplied_id
    ]

    if exact:
        return exact[0]

    normalized = supplied_id.removeprefix(
        "candidate:"
    )

    matches = [
        candidate.id
        for candidate in candidates
        if candidate.id.split(
            ":",
            1,
        )[-1].startswith(normalized)
    ]

    if not matches:
        raise KeyError(
            f"No candidate matches {supplied_id!r}."
        )

    if len(matches) > 1:
        raise ValueError(
            "Candidate ID prefix is ambiguous: "
            + ", ".join(
                short_id(candidate_id)
                for candidate_id in matches
            )
        )

    return matches[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "List and review ISO discovery candidates."
        )
    )

    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help=(
            "Path to the append-only candidate "
            "registry."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    list_parser = subparsers.add_parser(
        "list",
        help="List latest candidate states.",
    )

    list_parser.add_argument(
        "--status",
        choices=[
            "all",
            CandidateStatus.PENDING.value,
            CandidateStatus.ACCEPTED.value,
            CandidateStatus.REJECTED.value,
        ],
        default=CandidateStatus.PENDING.value,
    )

    for command in (
        "accept",
        "reject",
    ):
        review_parser = subparsers.add_parser(
            command,
            help=f"{command.title()} a candidate.",
        )

        review_parser.add_argument(
            "candidate_id",
            help=(
                "Complete candidate ID or unique "
                "hexadecimal prefix."
            ),
        )

        review_parser.add_argument(
            "--notes",
            default=None,
            help="Optional human review notes.",
        )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    registry = CandidateRegistry(
        args.registry
    )

    if args.command == "list":
        if args.status == "all":
            candidates = registry.latest()
        else:
            candidates = registry.latest(
                status=CandidateStatus(
                    args.status
                )
            )

        print_candidates(candidates)
        return

    candidate_id = resolve_candidate_id(
        registry,
        args.candidate_id,
    )

    status = (
        CandidateStatus.ACCEPTED
        if args.command == "accept"
        else CandidateStatus.REJECTED
    )

    reviewed = registry.review(
        candidate_id,
        status=status,
        notes=args.notes,
    )

    print(
        f"{reviewed.status.value.upper()}: "
        f"{reviewed.title}"
    )
    print(f"ID: {reviewed.id}")

    if reviewed.review_notes:
        print(
            f"Notes: {reviewed.review_notes}"
        )


if __name__ == "__main__":
    main()
