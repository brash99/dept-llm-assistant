import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.control_plane.catalog import ProgramCatalog
from app.control_plane.entities import ProgramEntity


def normalize_phrase(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


@dataclass(frozen=True)
class ProgramResolution:
    program: Optional[ProgramEntity]
    matched_phrase: Optional[str]
    confidence: float
    match_type: str
    diagnostics: Tuple[str, ...] = ()

    @property
    def found(self) -> bool:
        return self.program is not None


class ProgramResolver:
    """
    Resolve program names and aliases explicitly mentioned in a question.

    Version 0.1 is deliberately deterministic:
    - exact canonical-name match,
    - exact alias match,
    - longest matching phrase wins.
    """

    def __init__(self, catalog: ProgramCatalog):
        self.catalog = catalog
        self._phrases: List[Tuple[str, str, ProgramEntity, str]] = []

        for program in catalog.all():
            self._phrases.append(
                (normalize_phrase(program.name), program.name, program, "canonical_name")
            )

            for alias in program.aliases:
                self._phrases.append(
                    (normalize_phrase(alias), alias, program, "alias")
                )

        self._phrases.sort(
            key=lambda item: (len(item[0]), item[3] == "canonical_name"),
            reverse=True,
        )

    _COMMON_WORD_ALIASES = {
        "ai", "as", "ce", "cs", "is", "it", "me", "or",
    }
    _ACADEMIC_CONTEXT = re.compile(
        r"\b(?:major(?:ing)?|minor|program|degree|department|"
        r"bachelor of science|b\.\s*s\.|concentration|curriculum|"
        r"students? in|enrollment in)\b",
        flags=re.IGNORECASE,
    )

    @classmethod
    def _is_high_risk_alias(cls, alias: str) -> bool:
        normalized = normalize_phrase(alias)
        return len(normalized.replace(" ", "")) <= 2 or normalized in cls._COMMON_WORD_ALIASES

    @classmethod
    def _high_risk_match(cls, question: str, alias: str) -> tuple[bool, str]:
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])")
        matches = list(pattern.finditer(question))
        if not matches:
            return False, "rejected: capitalization or exact token boundary did not match"

        for match in matches:
            nearby = question[max(0, match.start() - 60):min(len(question), match.end() + 60)]
            if cls._ACADEMIC_CONTEXT.search(nearby):
                return True, "accepted: exact capitalization, token boundary, and nearby academic context"

        return False, "rejected: exact alias lacked nearby academic context"

    def resolve(self, question: str) -> ProgramResolution:
        normalized_question = normalize_phrase(question)
        padded_question = f" {normalized_question} "

        diagnostics = []

        for phrase, stored_phrase, program, match_type in self._phrases:
            if not phrase:
                continue

            if f" {phrase} " in padded_question:
                if match_type == "alias" and self._is_high_risk_alias(stored_phrase):
                    accepted, reason = self._high_risk_match(question, stored_phrase)
                    diagnostics.append(f"High-risk alias {stored_phrase!r} {reason}.")
                    if not accepted:
                        continue

                confidence = 1.0 if match_type == "canonical_name" else 0.95

                return ProgramResolution(
                    program=program,
                    matched_phrase=phrase,
                    confidence=confidence,
                    match_type=match_type,
                    diagnostics=tuple(diagnostics),
                )

        return ProgramResolution(
            program=None,
            matched_phrase=None,
            confidence=0.0,
            match_type="unresolved",
            diagnostics=tuple(diagnostics),
        )
