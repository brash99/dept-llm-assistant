from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.discovery.candidate import (
    CandidateResource,
    CandidateStatus,
)


class CandidateRegistry:
    """
    Append-only JSONL registry of discovered resources.

    Later records with the same candidate ID represent
    updated review state. The latest record is canonical.
    """

    def __init__(
        self,
        path: Path,
    ) -> None:
        self.path = Path(path)

    def read_all_records(
        self,
    ) -> List[CandidateResource]:
        if not self.path.exists():
            return []

        records = []

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for line_number, line in enumerate(
                handle,
                start=1,
            ):
                stripped = line.strip()

                if not stripped:
                    continue

                try:
                    payload = json.loads(
                        stripped
                    )
                    records.append(
                        CandidateResource.from_dict(
                            payload
                        )
                    )
                except Exception as error:
                    raise ValueError(
                        "Invalid discovery candidate "
                        f"record at {self.path}:"
                        f"{line_number}"
                    ) from error

        return records

    def latest_by_id(
        self,
    ) -> Dict[str, CandidateResource]:
        latest = {}

        for candidate in (
            self.read_all_records()
        ):
            latest[candidate.id] = candidate

        return latest

    def latest(
        self,
        *,
        status: Optional[
            CandidateStatus
        ] = None,
    ) -> List[CandidateResource]:
        candidates = list(
            self.latest_by_id().values()
        )

        if status is not None:
            candidates = [
                candidate
                for candidate in candidates
                if candidate.status is status
            ]

        return sorted(
            candidates,
            key=lambda item: (
                item.discovered_at,
                item.title.casefold(),
            ),
        )

    def append(
        self,
        candidate: CandidateResource,
    ) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    candidate.to_dict(),
                    sort_keys=True,
                )
            )
            handle.write("\n")

    def add(
        self,
        candidate: CandidateResource,
    ) -> str:
        existing = self.latest_by_id().get(
            candidate.id
        )

        if existing is not None:
            return "already_known"

        self.append(candidate)

        return "added"

    def review(
        self,
        candidate_id: str,
        *,
        status: CandidateStatus,
        notes: Optional[str] = None,
    ) -> CandidateResource:
        candidate = self.latest_by_id().get(
            candidate_id
        )

        if candidate is None:
            raise KeyError(
                f"Unknown candidate: "
                f"{candidate_id}"
            )

        reviewed = candidate.reviewed(
            status=status,
            notes=notes,
        )

        self.append(reviewed)

        return reviewed
