"""Factual signal extraction for generic document routing.

Signals are candidates, not semantic assertions.  In particular, timestamps and
year-like strings retain their source and are never promoted to publication or
reporting dates by this service.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Any, Mapping, Optional, Tuple
from urllib.parse import urlparse

from app.knowledge import KnowledgeObject


YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
ACADEMIC_YEAR_RE = re.compile(
    r"(?<!\d)((?:19|20)\d{2})[-_](?:(?:19|20)?(\d{2,4}))(?!\d)"
)


@dataclass(frozen=True)
class DocumentSignals:
    source_key: str
    source_root: str
    qualified_relative_path: str
    path_segments: Tuple[str, ...]
    filename: str
    extension: str
    parser: Optional[str]
    file_type: Optional[str]
    mime_type: Optional[str]
    title: str
    title_is_blank: bool
    title_is_filename: bool
    canonical_url: Optional[str]
    canonical_domain: Optional[str]
    issuing_authority: Optional[str]
    explicit_external_provenance: bool
    acquisition_date: Optional[str]
    publication_date: Optional[str]
    effective_period: Optional[str]
    application_created_at: Optional[str]
    application_modified_at: Optional[str]
    filesystem_modified_at: Optional[str]
    candidate_reporting_periods: Tuple[str, ...]
    candidate_academic_years: Tuple[str, ...]
    sensitive_reasons: Tuple[str, ...]


class DocumentSignalExtractor:
    """Extract normalized, provenance-bearing routing inputs without classifying."""

    version = "1"
    _sensitive_segments = {
        "student work": "student_level_work",
        "exit interviews": "exit_interviews",
        "transcripts": "transcripts",
        "adjunct eval": "personnel_evaluation",
        "adjunct evaluation": "personnel_evaluation",
        "faculty searches": "faculty_search",
        "faculty search": "faculty_search",
    }

    def extract(self, obj: KnowledgeObject) -> DocumentSignals:
        metadata = obj.metadata or {}
        source = obj.source or {}
        path = str(
            metadata.get("qualified_relative_path")
            or metadata.get("local_relative_path")
            or source.get("relative_path")
            or getattr(obj, "relative_path", "")
            or ""
        ).replace("\\", "/").lstrip("/")
        pure = PurePosixPath(path)
        segments = tuple(part.casefold().strip() for part in pure.parts if part.strip())
        source_key = str(metadata.get("source_key") or source.get("source_key") or "")
        source_key = source_key.replace("\\", "/").split("/", 1)[0]
        if not source_key and segments:
            source_key = segments[0]
        canonical_url = _string(metadata.get("canonical_url") or source.get("canonical_url"))
        title = str(obj.title or metadata.get("title") or "").strip()
        stem = pure.stem.casefold().replace("_", " ").replace("-", " ").strip()
        normalized_title = title.casefold().replace("_", " ").replace("-", " ").strip()
        date_sources = " ".join((path, title))
        years = tuple(dict.fromkeys(YEAR_RE.findall(date_sources)))
        academic_years = tuple(dict.fromkeys(_academic_years(date_sources)))
        lower_path = path.casefold()
        sensitive = tuple(
            sorted(
                {reason for marker, reason in self._sensitive_segments.items() if marker in lower_path}
            )
        )
        return DocumentSignals(
            source_key=source_key.casefold(),
            source_root=segments[0] if segments else "",
            qualified_relative_path=path,
            path_segments=segments,
            filename=pure.name,
            extension=pure.suffix.casefold(),
            parser=_string(getattr(obj, "parser", None) or metadata.get("parser")),
            file_type=_string(getattr(obj, "file_type", None) or metadata.get("file_type")),
            mime_type=_string(metadata.get("mime_type") or metadata.get("content_type")),
            title=title,
            title_is_blank=not title,
            title_is_filename=bool(title) and normalized_title in {stem, pure.name.casefold()},
            canonical_url=canonical_url,
            canonical_domain=(urlparse(canonical_url).hostname or "").casefold() if canonical_url else None,
            issuing_authority=_string(metadata.get("issuing_authority") or source.get("issuing_authority")),
            explicit_external_provenance=bool(
                canonical_url and (metadata.get("issuing_authority") or source.get("issuing_authority"))
                and (metadata.get("authority_class") or source.get("authority_class"))
            ),
            acquisition_date=_string(metadata.get("retrieval_timestamp") or metadata.get("acquisition_date")),
            publication_date=_string(metadata.get("publication_date")),
            effective_period=_string(metadata.get("effective_period")),
            application_created_at=_property(metadata, "created"),
            application_modified_at=_property(metadata, "modified"),
            filesystem_modified_at=_string(getattr(obj, "modified_at", None) or metadata.get("modified_at")),
            candidate_reporting_periods=years,
            candidate_academic_years=academic_years,
            sensitive_reasons=sensitive,
        )


def _property(metadata: Mapping[str, Any], name: str) -> Optional[str]:
    for container in (metadata.get("core_properties"), metadata.get("pdf_metadata"), metadata):
        if isinstance(container, Mapping):
            value = container.get(name) or container.get(f"{name}_at")
            if value is not None:
                return str(value)
    return None


def _academic_years(value: str):
    for start, end in ACADEMIC_YEAR_RE.findall(value):
        end_year = int(end) if len(end) == 4 else (int(start[:2]) * 100 + int(end))
        if end_year == int(start) + 1:
            yield f"{start}-{end_year}"


def _string(value: Any) -> Optional[str]:
    return str(value) if value not in (None, "") else None


__all__ = ["DocumentSignalExtractor", "DocumentSignals"]
