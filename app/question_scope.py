"""Deterministic scope classification for institutional questions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class QuestionScope(str, Enum):
    SINGLE_ENTITY = "single_entity"
    MULTI_ENTITY = "multi_entity"
    INSTITUTION_WIDE = "institution_wide"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class QuestionScopeAssessment:
    scope: QuestionScope
    label: str
    rationale: str
    indicators: tuple[str, ...] = ()


_INSTITUTION_WIDE_PATTERNS = (
    r"\ball departments\b",
    r"\bwhich departments\b",
    r"\bacross (?:academic )?(?:departments|units|colleges)\b",
    r"\b(?:university|institution)[ -]wide\b",
    r"\ballocation across (?:academic )?units\b",
    r"\breduce (?:the )?total faculty\b",
    r"\bfaculty reductions?\b",
    r"\bacademic workforce planning\b",
)

_SINGLE_ENTITY_PATTERNS = (
    r"\b(?:assess|evaluate|review) the .+? (?:department|school|college|program)\b",
    r"\bthe .+? (?:department|school|college|program)\b",
)


def classify_question_scope(question: str) -> QuestionScopeAssessment:
    """Classify comparison scope without resolving or inventing entities."""
    text = " ".join(question.casefold().split())
    institution_indicators = tuple(
        pattern
        for pattern in _INSTITUTION_WIDE_PATTERNS
        if re.search(pattern, text)
    )

    # Require either an explicit institution-wide phrase or multiple workforce
    # indicators. This avoids treating every isolated use of "department" as
    # a university-wide comparison.
    explicit_wide = any(
        marker in text
        for marker in (
            "all departments",
            "which departments",
            "university-wide",
            "university wide",
            "institution-wide",
            "institution wide",
            "across departments",
            "across academic units",
            "allocation across units",
        )
    )
    workforce_wide = (
        len(institution_indicators) >= 2
        and any(term in text for term in ("faculty", "workforce", "staffing"))
    )

    if explicit_wide or workforce_wide:
        return QuestionScopeAssessment(
            scope=QuestionScope.INSTITUTION_WIDE,
            label="Institution-Wide Academic Workforce Planning",
            rationale=(
                "The question requests a comparative decision across academic "
                "units rather than an assessment of one selected entity."
            ),
            indicators=institution_indicators,
        )

    if re.search(r"\bcompare\b.+\band\b", text):
        return QuestionScopeAssessment(
            scope=QuestionScope.MULTI_ENTITY,
            label="Multi-Entity Comparison",
            rationale="The question explicitly requests comparison of multiple entities.",
            indicators=("compare ... and ...",),
        )

    single_indicators = tuple(
        pattern
        for pattern in _SINGLE_ENTITY_PATTERNS
        if re.search(pattern, text)
    )
    if single_indicators:
        return QuestionScopeAssessment(
            scope=QuestionScope.SINGLE_ENTITY,
            label="Single Academic Entity",
            rationale="The question explicitly identifies one academic entity for assessment.",
            indicators=single_indicators,
        )

    return QuestionScopeAssessment(
        scope=QuestionScope.UNRESOLVED,
        label="Scope Unresolved",
        rationale="The question does not deterministically establish a comparison scope.",
    )


__all__ = ["QuestionScope", "QuestionScopeAssessment", "classify_question_scope"]
