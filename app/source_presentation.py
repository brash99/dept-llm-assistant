"""Executive-facing source labels, separate from retrieval diagnostics."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def repository_relative_path(
    value: str | Path | None,
    repository_root: str | Path | None = None,
) -> str:
    """Present repository evidence paths without machine-specific prefixes.

    URLs and paths outside the repository are preserved.  The final marker
    fallback makes artifacts built on the Mac and A100 display identically.
    """
    if value is None:
        return ""
    text = str(value)
    if urlparse(text).scheme:
        return text
    path = Path(text)
    if not path.is_absolute():
        return path.as_posix()

    roots = [Path(repository_root).resolve()] if repository_root else []
    roots.append(PROJECT_ROOT.resolve())
    for root in roots:
        try:
            return path.resolve().relative_to(root).as_posix()
        except ValueError:
            continue

    parts = path.parts
    marker_indexes = [
        index for index, part in enumerate(parts) if part == "dept-llm-assistant"
    ]
    if marker_indexes:
        suffix = parts[marker_indexes[-1] + 1 :]
        return Path(*suffix).as_posix() if suffix else "."
    return path.as_posix()


def executive_source_label(
    citation_label: str,
    title: str,
    evidence_class: str | None = None,
) -> str:
    parts = [f"[{citation_label}]"]
    if evidence_class:
        parts.append(f"[{evidence_class}]")
    parts.append(title)
    return " ".join(parts)


__all__ = ["executive_source_label", "repository_relative_path"]
