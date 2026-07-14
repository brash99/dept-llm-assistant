from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from app.constitution.objects import ConstitutionalType


@dataclass(frozen=True)
class EmpiricalRetrievalIntent:
    entities: Tuple[str, ...] = ()
    evidence_domains: Tuple[str, ...] = ()
    query_terms: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": list(self.entities),
            "evidence_domains": list(
                self.evidence_domains
            ),
            "query_terms": list(
                self.query_terms
            ),
        }


@dataclass(frozen=True)
class ConstitutionalRetrievalIntent:
    principles: Tuple[str, ...] = ()
    constitutional_types: Tuple[
        ConstitutionalType,
        ...,
    ] = ()
    query_terms: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principles": list(self.principles),
            "constitutional_types": [
                item.value
                for item in self.constitutional_types
            ],
            "query_terms": list(
                self.query_terms
            ),
        }


@dataclass(frozen=True)
class ConstitutionalRetrievalPlan:
    question: str

    empirical: EmpiricalRetrievalIntent = field(
        default_factory=EmpiricalRetrievalIntent
    )

    constitutional: ConstitutionalRetrievalIntent = field(
        default_factory=ConstitutionalRetrievalIntent
    )

    notes: Tuple[str, ...] = ()
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ValueError(
                "Retrieval-plan question must not be empty."
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Retrieval-plan confidence must be "
                "between 0.0 and 1.0."
            )

    @property
    def requires_constitutional_evidence(
        self,
    ) -> bool:
        return bool(
            self.constitutional.principles
            or self.constitutional.constitutional_types
            or self.constitutional.query_terms
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "empirical": self.empirical.to_dict(),
            "constitutional": (
                self.constitutional.to_dict()
            ),
            "notes": list(self.notes),
            "confidence": self.confidence,
        }
