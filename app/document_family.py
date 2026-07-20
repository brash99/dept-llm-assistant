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
_PROGRAM_CODES = {"ce", "cpe", "cpen", "cs", "cpsc", "ece", "ee"}


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def normalized_document_family_name(value: str) -> str:
    """Remove obvious revision noise while retaining substantive identifiers."""
    filename = PurePosixPath(str(value).replace("\\", "/")).name
    name = _EXTENSIONS.sub("", filename)
    name = re.sub(r"_+", " ", name)
    name = re.sub(r"final\s*[-_. ]*draft", " ", name, flags=re.I)
    name = _VERSION_TOKENS.sub(" ", name)
    name = _DATE_TOKENS.sub(" ", name)
    name = re.sub(r"[^a-z0-9]+", " ", name.casefold())
    name = " ".join(name.split()) or "untitled"
    # Exported criterion sections commonly repeat the section number as a
    # filename prefix: 08_Criterion_8... and Criterion_8... are one family.
    match = re.match(r"^0*(\d+)\s+criterion\s+0*(\d+)\b(.*)$", name)
    if match and int(match.group(1)) == int(match.group(2)):
        name = f"criterion {int(match.group(2))}{match.group(3)}"
    return name


def _program_context(family: str, metadata_context: str) -> str:
    if metadata_context:
        return normalized_document_family_name(metadata_context)

    tokens = family.split()
    for index, token in enumerate(tokens):
        if token not in _PROGRAM_CODES:
            continue
        if index == 0 or any(
            marker in tokens
            for marker in ("abet", "criterion", "selfstudy", "study")
        ):
            return token
    return "unspecified"


def _academic_accreditation_family(
    raw_name: str,
    family: str,
    metadata_context: str,
) -> str:
    """Canonicalize ABET self-study packages without merging criteria."""
    searchable = f"{raw_name} {family}".casefold()
    accreditation_related = any(
        marker in searchable
        for marker in ("abet", "self-study", "self study", "selfstudy", "criterion")
    )
    if not accreditation_related:
        return family

    family = re.sub(r"\bselfstudyreport\b", "self study", family)
    family = re.sub(r"\bselfstudy\b", "self study", family)
    family = re.sub(r"\bself study report\b", "self study", family)
    family = re.sub(r"\ball in one\b", " ", family)
    family = " ".join(family.split())
    program = _program_context(family, metadata_context)

    criterion_match = re.search(r"\bcriterion\s+0*(\d+)\b", family)
    if criterion_match:
        criterion = str(int(criterion_match.group(1)))
        subject = family[criterion_match.end():].strip()
        subject_tokens = [
            token
            for token in subject.split()
            if token not in _PROGRAM_CODES
            and token not in {"abet", "criterion", "section"}
        ]
        subject_key = " ".join(subject_tokens)
        return " ".join(
            part
            for part in (
                "abet",
                program,
                f"criterion {criterion}",
                subject_key,
            )
            if part
        )

    if "self study" in family:
        return f"abet {program} self study"

    return family


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
    family = _academic_accreditation_family(
        str(raw_name),
        family,
        context,
    )
    return "|".join(part for part in (collection, family) if part)


__all__ = ["document_family_key", "normalized_document_family_name"]
