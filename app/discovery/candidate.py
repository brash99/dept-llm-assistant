from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple
import hashlib


class CandidateStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


def now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def make_candidate_id(
    source_organization: str,
    url: str,
) -> str:
    identity = (
        source_organization.strip().casefold()
        + "\n"
        + url.strip()
    )

    digest = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()

    return f"candidate:{digest}"


@dataclass(frozen=True)
class CandidateResource:
    id: str
    title: str
    url: str

    source_organization: str
    discovery_provider: str
    discovery_query: Optional[str]

    status: CandidateStatus
    discovered_at: str

    description: Optional[str] = None
    media_type: Optional[str] = None
    publication_date: Optional[str] = None

    topics: Tuple[str, ...] = ()
    decision_domains: Tuple[str, ...] = ()

    review_notes: Optional[str] = None
    reviewed_at: Optional[str] = None

    @classmethod
    def discovered_now(
        cls,
        *,
        title: str,
        url: str,
        source_organization: str,
        discovery_provider: str,
        discovery_query: Optional[str] = None,
        description: Optional[str] = None,
        media_type: Optional[str] = None,
        publication_date: Optional[str] = None,
        topics: Tuple[str, ...] = (),
        decision_domains: Tuple[str, ...] = (),
    ) -> "CandidateResource":
        return cls(
            id=make_candidate_id(
                source_organization,
                url,
            ),
            title=title,
            url=url,
            source_organization=source_organization,
            discovery_provider=discovery_provider,
            discovery_query=discovery_query,
            status=CandidateStatus.PENDING,
            discovered_at=now_iso(),
            description=description,
            media_type=media_type,
            publication_date=publication_date,
            topics=tuple(topics),
            decision_domains=tuple(
                decision_domains
            ),
        )

    def reviewed(
        self,
        *,
        status: CandidateStatus,
        notes: Optional[str] = None,
    ) -> "CandidateResource":
        if status is CandidateStatus.PENDING:
            raise ValueError(
                "A review must accept or reject "
                "the candidate."
            )

        return replace(
            self,
            status=status,
            review_notes=notes,
            reviewed_at=now_iso(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source_organization": (
                self.source_organization
            ),
            "discovery_provider": (
                self.discovery_provider
            ),
            "discovery_query": (
                self.discovery_query
            ),
            "status": self.status.value,
            "discovered_at": (
                self.discovered_at
            ),
            "description": self.description,
            "media_type": self.media_type,
            "publication_date": (
                self.publication_date
            ),
            "topics": list(self.topics),
            "decision_domains": list(
                self.decision_domains
            ),
            "review_notes": self.review_notes,
            "reviewed_at": self.reviewed_at,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Dict[str, Any],
    ) -> "CandidateResource":
        return cls(
            id=str(payload["id"]),
            title=str(payload["title"]),
            url=str(payload["url"]),
            source_organization=str(
                payload["source_organization"]
            ),
            discovery_provider=str(
                payload["discovery_provider"]
            ),
            discovery_query=payload.get(
                "discovery_query"
            ),
            status=CandidateStatus(
                payload.get(
                    "status",
                    CandidateStatus.PENDING.value,
                )
            ),
            discovered_at=str(
                payload["discovered_at"]
            ),
            description=payload.get(
                "description"
            ),
            media_type=payload.get(
                "media_type"
            ),
            publication_date=payload.get(
                "publication_date"
            ),
            topics=tuple(
                payload.get("topics", [])
            ),
            decision_domains=tuple(
                payload.get(
                    "decision_domains",
                    [],
                )
            ),
            review_notes=payload.get(
                "review_notes"
            ),
            reviewed_at=payload.get(
                "reviewed_at"
            ),
        )
