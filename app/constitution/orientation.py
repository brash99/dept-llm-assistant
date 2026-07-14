from dataclasses import dataclass, field
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

from app.constitution.catalog import ConstitutionalCatalog
from app.constitution.objects import (
    ConstitutionalKnowledgeObject,
)


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize_tokens(text: str) -> Tuple[str, ...]:
    return tuple(
        _TOKEN_PATTERN.findall(text.casefold())
    )


@dataclass(frozen=True)
class ConstitutionalPrincipleMatch:
    """
    One inspectable match between an institutional question and a declared
    constitutional principle.
    """

    constitutional_object_id: str
    constitutional_object_title: str
    constitutional_type: str
    principle: str
    score: float
    matched_terms: Tuple[str, ...] = ()
    method: str = "lexical_profile"

    def to_dict(self) -> dict:
        return {
            "constitutional_object_id": (
                self.constitutional_object_id
            ),
            "constitutional_object_title": (
                self.constitutional_object_title
            ),
            "constitutional_type": (
                self.constitutional_type
            ),
            "principle": self.principle,
            "score": self.score,
            "matched_terms": list(
                self.matched_terms
            ),
            "method": self.method,
        }


@dataclass(frozen=True)
class ConstitutionalOrientation:
    """
    Explainable interpretation of which institutional principles may be
    relevant to a question.

    Orientation does not determine alignment and does not recommend action.
    """

    question: str
    matches: Tuple[
        ConstitutionalPrincipleMatch,
        ...,
    ] = ()
    notes: Tuple[str, ...] = ()
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ValueError(
                "Constitutional orientation question "
                "must not be empty."
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Constitutional orientation confidence "
                "must be between 0.0 and 1.0."
            )

    @property
    def relevant_principles(
        self,
    ) -> Tuple[str, ...]:
        return tuple(
            match.principle
            for match in self.matches
        )

    @property
    def requires_constitutional_retrieval(
        self,
    ) -> bool:
        return bool(self.matches)

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "matches": [
                match.to_dict()
                for match in self.matches
            ],
            "notes": list(self.notes),
            "confidence": self.confidence,
            "requires_constitutional_retrieval": (
                self.requires_constitutional_retrieval
            ),
        }


class ConstitutionalOrientationService:
    """
    Produces a deterministic first-pass constitutional orientation.

    Version 0.1 uses curated lexical profiles. This keeps the result
    inspectable and testable while establishing the service contract.
    A later semantic matcher can replace or supplement this strategy.
    """

    DEFAULT_PROFILES: Dict[str, Tuple[str, ...]] = {
        "advance the power and promise of an education embedded in the liberal arts": (
            "academic",
            "academics",
            "curriculum",
            "curricular",
            "degree",
            "education",
            "educational",
            "faculty",
            "learning",
            "liberal arts",
            "major",
            "minor",
            "program",
            "scholarship",
            "student learning",
            "teaching",
        ),
        "connect with our community": (
            "community",
            "economic development",
            "employer",
            "engagement",
            "hampton roads",
            "industry",
            "internship",
            "newport news",
            "partnership",
            "peninsula",
            "public service",
            "regional",
            "virginia",
            "workforce",
        ),
        "create a stronger culture of inclusion and belonging": (
            "access",
            "accessibility",
            "belonging",
            "climate",
            "culture",
            "diversity",
            "equity",
            "inclusive",
            "inclusion",
            "retention",
            "student support",
            "wellbeing",
        ),
        "build a foundation to thrive": (
            "budget",
            "capacity",
            "endowment",
            "facilities",
            "faculty hiring",
            "finance",
            "financial",
            "funding",
            "infrastructure",
            "investment",
            "recruiting",
            "resources",
            "retaining",
            "staffing",
            "sustainability",
        ),
    }

    def __init__(
        self,
        *,
        catalog: ConstitutionalCatalog,
        profiles: Optional[
            Dict[
                str,
                Iterable[str],
            ]
        ] = None,
        minimum_score: float = 0.12,
        max_matches: int = 4,
    ) -> None:
        if not 0.0 <= minimum_score <= 1.0:
            raise ValueError(
                "minimum_score must be between "
                "0.0 and 1.0."
            )

        if max_matches < 1:
            raise ValueError(
                "max_matches must be at least 1."
            )

        self.catalog = catalog
        self.minimum_score = minimum_score
        self.max_matches = max_matches

        source_profiles = (
            profiles
            if profiles is not None
            else self.DEFAULT_PROFILES
        )

        self.profiles = {
            principle.casefold(): tuple(
                term.casefold().strip()
                for term in terms
                if term.strip()
            )
            for principle, terms in (
                source_profiles.items()
            )
        }

    def orient(
        self,
        question: str,
    ) -> ConstitutionalOrientation:
        if not question.strip():
            raise ValueError(
                "Question must not be empty."
            )

        question_normalized = question.casefold()
        question_tokens = set(
            normalize_tokens(question)
        )

        candidates: List[
            ConstitutionalPrincipleMatch
        ] = []

        for obj in self.catalog.all():
            candidates.extend(
                self._matches_for_object(
                    question_normalized=(
                        question_normalized
                    ),
                    question_tokens=question_tokens,
                    obj=obj,
                )
            )

        candidates.sort(
            key=lambda item: (
                -item.score,
                item.principle.casefold(),
            )
        )

        matches = tuple(
            match
            for match in candidates
            if match.score >= self.minimum_score
        )[: self.max_matches]

        notes: List[str] = []

        if matches:
            notes.append(
                "Potentially relevant institutional "
                "principles were identified. "
                "This is orientation, not an "
                "alignment judgment."
            )
        else:
            notes.append(
                "No constitutional principle exceeded "
                "the current deterministic relevance "
                "threshold."
            )

        confidence = (
            max(
                match.score
                for match in matches
            )
            if matches
            else 0.0
        )

        return ConstitutionalOrientation(
            question=question,
            matches=matches,
            notes=tuple(notes),
            confidence=min(1.0, confidence),
        )

    def _matches_for_object(
        self,
        *,
        question_normalized: str,
        question_tokens: Set[str],
        obj: ConstitutionalKnowledgeObject,
    ) -> List[
        ConstitutionalPrincipleMatch
    ]:
        matches: List[
            ConstitutionalPrincipleMatch
        ] = []

        for principle in obj.principles:
            profile = self.profiles.get(
                principle.casefold(),
                (),
            )

            matched_terms = []

            for term in profile:
                if " " in term:
                    if term in question_normalized:
                        matched_terms.append(term)
                elif term in question_tokens:
                    matched_terms.append(term)

            if not profile:
                principle_tokens = set(
                    normalize_tokens(principle)
                )

                overlap = sorted(
                    question_tokens
                    & principle_tokens
                )

                matched_terms.extend(overlap)
                denominator = max(
                    1,
                    len(principle_tokens),
                )
            else:
                denominator = max(
                    1,
                    min(5, len(profile)),
                )

            score = min(
                1.0,
                len(set(matched_terms))
                / denominator,
            )

            if matched_terms:
                matches.append(
                    ConstitutionalPrincipleMatch(
                        constitutional_object_id=(
                            obj.id
                        ),
                        constitutional_object_title=(
                            obj.title
                        ),
                        constitutional_type=(
                            obj.constitutional_type
                        ),
                        principle=principle,
                        score=round(score, 4),
                        matched_terms=tuple(
                            sorted(
                                set(matched_terms)
                            )
                        ),
                    )
                )

        return matches
