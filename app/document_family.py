"""Dependency-light document-family identity for evidence diversity."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any, Mapping


_EXTENSIONS = re.compile(r"(?:\.(?:pdf|docx?|odt|rtf|txt|html?|xlsx?|csv|pptx?))+$", re.I)
_VERSION_TOKENS = re.compile(
    r"\b(?:finaldraft|final|draft|version|ver|rev|revision|v)\s*0*\d*\b",
    re.I,
)
_DATE_TOKENS = re.compile(
    r"\b(?:19|20)\d{2}(?:[-_. ](?:0?[1-9]|1[0-2]))?(?:[-_. ](?:0?[1-9]|[12]\d|3[01]))?\b"
)


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def normalized_document_family_name(value: str) -> str:
    """Remove obvious revision noise while retaining substantive identifiers."""
    filename = PurePosixPath(str(value).replace("\\", "/")).name
    name = _EXTENSIONS.sub("", filename)
    name = re.sub(r"final\s*[-_. ]*draft", " ", name, flags=re.I)
    name = _VERSION_TOKENS.sub(" ", name)
    name = _DATE_TOKENS.sub(" ", name)
    name = re.sub(r"[^a-z0-9]+", " ", name.casefold())
    return " ".join(name.split()) or "untitled"


def document_family_key(source: Any) -> str:
    """Return a stable, conservative family key from existing provenance."""
    citation = _value(source, "citation", {}) or {}
    metadata = _value(source, "metadata", {}) or {}
    raw_name = (
        citation.get("relative_path")
        or citation.get("source_path")
        or citation.get("title")
        or _value(source, "knowledge_object_id", "")
        or "untitled"
    )
    family = normalized_document_family_name(str(raw_name))
    collection = str(
        metadata.get("source_collection")
        or metadata.get("collection")
        or ""
    ).strip().casefold()
    context = str(
        metadata.get("program")
        or metadata.get("accreditation_context")
        or ""
    ).strip().casefold()
    return "|".join(part for part in (collection, context, family) if part)


__all__ = ["document_family_key", "normalized_document_family_name"]
