"""Deterministic ordering for normalized academic-term identifiers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


_TERM_ORDER = {
    "spring": 10,
    "may": 20,
    "summer_1": 30,
    "extended_summer": 35,
    "summer_2": 40,
    "fall": 50,
}
_TERM_PATTERN = re.compile(
    r"^(?P<year>\d{4})_(?P<label>spring|may|summer_1|extended_summer|summer_2|fall)$"
)


@dataclass(frozen=True)
class AcademicTermOrder:
    term: str
    supported: bool
    year: int | None
    period: str | None
    sort_key: tuple[Any, ...]
    warning: str | None = None


def academic_term_order(term: str) -> AcademicTermOrder:
    value = str(term or "").strip().casefold()
    match = _TERM_PATTERN.fullmatch(value)
    if not match:
        return AcademicTermOrder(
            term=str(term or ""), supported=False, year=None, period=None,
            sort_key=(1, str(term or "").casefold()),
            warning="unsupported_or_malformed_academic_term",
        )
    year = int(match.group("year"))
    period = match.group("label")
    return AcademicTermOrder(
        term=value, supported=True, year=year, period=period,
        sort_key=(0, year, _TERM_ORDER[period], period),
    )


def academic_term_sort_key(term: str) -> tuple[Any, ...]:
    return academic_term_order(term).sort_key


__all__ = ["AcademicTermOrder", "academic_term_order", "academic_term_sort_key"]
