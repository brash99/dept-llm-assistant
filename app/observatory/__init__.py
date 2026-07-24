"""Institutional Semantic Observatory public API.

Metrics are loaded only when requested so presentation-only imports do not
initialize FAISS or sentence-transformer dependencies.
"""

from __future__ import annotations

from typing import Any


__all__ = ["ObservatoryAssessment", "build_observatory_assessment"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from app.observatory import metrics

        return getattr(metrics, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
