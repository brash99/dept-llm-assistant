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
        self._phrases: List[Tuple[str, ProgramEntity, str]] = []

        for program in catalog.all():
            self._phrases.append(
                (normalize_phrase(program.name), program, "canonical_name")
            )

            for alias in program.aliases:
                self._phrases.append(
                    (normalize_phrase(alias), program, "alias")
                )

        self._phrases.sort(key=lambda item: len(item[0]), reverse=True)

    def resolve(self, question: str) -> ProgramResolution:
        normalized_question = normalize_phrase(question)
        padded_question = f" {normalized_question} "

        for phrase, program, match_type in self._phrases:
            if not phrase:
                continue

            if f" {phrase} " in padded_question:
                confidence = 1.0 if match_type == "canonical_name" else 0.95

                return ProgramResolution(
                    program=program,
                    matched_phrase=phrase,
                    confidence=confidence,
                    match_type=match_type,
                )

        return ProgramResolution(
            program=None,
            matched_phrase=None,
            confidence=0.0,
            match_type="unresolved",
        )
