from __future__ import annotations

from typing import Any, Iterable, Optional


def get_value(
    obj: Any,
    *names: str,
    default: Any = None,
) -> Any:
    """Return the first non-None attribute found on an object."""
    if obj is None:
        return default

    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)

            if value is not None:
                return value

    return default


def percentage(value: Any) -> Optional[float]:
    """Normalize a score expressed as either 0-1 or 0-100."""
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if 0.0 <= number <= 1.0:
        number *= 100.0

    return max(0.0, min(100.0, number))


def progress_bar(
    value: Optional[float],
    width: int = 10,
) -> str:
    if value is None:
        return "○ Unavailable"

    filled = round(width * value / 100.0)
    empty = width - filled

    return f"{'█' * filled}{'░' * empty} {value:.0f}%"


def score_label(
    value: Optional[float],
) -> str:
    if value is None:
        return "Unavailable"

    if value >= 85:
        return "Strong"

    if value >= 70:
        return "Good"

    if value >= 50:
        return "Developing"

    return "Limited"


def status_symbol(label: str) -> str:
    normalized = label.casefold()

    if any(
        word in normalized
        for word in (
            "strong",
            "high",
            "good",
            "connected",
            "ready",
            "focused",
        )
    ):
        return "✓"

    if any(
        word in normalized
        for word in (
            "moderate",
            "developing",
            "partial",
        )
    ):
        return "⚠"

    return "○"


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    if isinstance(value, set):
        return sorted(value, key=str)

    if isinstance(value, str):
        return [value]

    if isinstance(value, Iterable):
        return list(value)

    return [value]


def display_name(value: Any) -> str:
    """Render strings or lightweight domain objects safely."""
    if value is None:
        return "Unknown"

    if isinstance(value, str):
        return value

    for attribute in ("name", "title", "label"):
        if hasattr(value, attribute):
            result = getattr(value, attribute)

            if result:
                return str(result)

    return str(value)
