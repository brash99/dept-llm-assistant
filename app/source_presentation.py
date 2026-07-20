"""Executive-facing source labels, separate from retrieval diagnostics."""

from __future__ import annotations


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


__all__ = ["executive_source_label"]
