from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.acquisition.authority import SourceAuthority
from app.acquisition.method import AcquisitionMethod


@dataclass(frozen=True)
class SourceDocument:
    """
    Stable acquisition contract for one source artifact.

    SourceDocument stores identity and provenance facts. It deliberately does
    not contain parsed text, chunks, embeddings, evidence classifications, or
    semantic interpretations.
    """

    id: str
    title: str
    source_organization: str
    authority: SourceAuthority
    acquisition_method: AcquisitionMethod
    relative_path: str
    content_hash: str
    acquired_at: datetime
    source_url: Optional[str] = None
    publication_date: Optional[date] = None
    media_type: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("SourceDocument.id must not be empty.")

        if not self.title.strip():
            raise ValueError("SourceDocument.title must not be empty.")

        if not self.source_organization.strip():
            raise ValueError(
                "SourceDocument.source_organization must not be empty."
            )

        if not self.relative_path.strip():
            raise ValueError(
                "SourceDocument.relative_path must not be empty."
            )

        if not self.content_hash.strip():
            raise ValueError(
                "SourceDocument.content_hash must not be empty."
            )

        if self.acquired_at.tzinfo is None:
            raise ValueError(
                "SourceDocument.acquired_at must be timezone-aware."
            )

        normalized_path = Path(self.relative_path)

        if normalized_path.is_absolute():
            raise ValueError(
                "SourceDocument.relative_path must be relative."
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a JSON-compatible representation suitable for a manifest.
        """
        return {
            "id": self.id,
            "title": self.title,
            "source_organization": self.source_organization,
            "authority": self.authority.value,
            "acquisition_method": self.acquisition_method.value,
            "relative_path": self.relative_path,
            "content_hash": self.content_hash,
            "acquired_at": self.acquired_at.isoformat(),
            "source_url": self.source_url,
            "publication_date": (
                self.publication_date.isoformat()
                if self.publication_date is not None
                else None
            ),
            "media_type": self.media_type,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SourceDocument":
        """
        Reconstruct a SourceDocument from a manifest record.
        """
        publication_date_value = payload.get("publication_date")

        return cls(
            id=payload["id"],
            title=payload["title"],
            source_organization=payload["source_organization"],
            authority=SourceAuthority(payload["authority"]),
            acquisition_method=AcquisitionMethod(
                payload["acquisition_method"]
            ),
            relative_path=payload["relative_path"],
            content_hash=payload["content_hash"],
            acquired_at=datetime.fromisoformat(payload["acquired_at"]),
            source_url=payload.get("source_url"),
            publication_date=(
                date.fromisoformat(publication_date_value)
                if publication_date_value
                else None
            ),
            media_type=payload.get("media_type"),
        )

    @classmethod
    def acquired_now(
        cls,
        *,
        id: str,
        title: str,
        source_organization: str,
        authority: SourceAuthority,
        acquisition_method: AcquisitionMethod,
        relative_path: str,
        content_hash: str,
        source_url: Optional[str] = None,
        publication_date: Optional[date] = None,
        media_type: Optional[str] = None,
    ) -> "SourceDocument":
        """
        Convenience constructor for acquisition services.
        """
        return cls(
            id=id,
            title=title,
            source_organization=source_organization,
            authority=authority,
            acquisition_method=acquisition_method,
            relative_path=relative_path,
            content_hash=content_hash,
            acquired_at=datetime.now(timezone.utc),
            source_url=source_url,
            publication_date=publication_date,
            media_type=media_type,
        )
