"""Dependency-free presentation contracts for Dashboard V2."""

from dataclasses import dataclass, field
from typing import Any


ACADEMIC_WORKFORCE_PLANNING_DOMAINS = (
    "Instructional Demand",
    "Faculty Capacity",
    "Service Teaching Dependence",
    "Accreditation and External Constraints",
    "Enrollment Trends",
    "Financial Implications",
    "Strategic Priority Alignment",
    "One-Line Loss Scenario",
)


LLC_CORE_REQUIREMENTS = (
    "Mathematics",
    "Second Language Literacy",
    "English",
    "Logical Reasoning",
    "Economics",
)


LLC_AREAS_OF_INQUIRY = (
    "Creative Expressions",
    "Civic and Democratic Engagement",
    "Western Traditions",
    "Global and Multicultural Perspectives",
    "Investigating the Natural World",
)


SUBSTITUTABILITY_STATUSES = (
    "Alternative providers evidenced",
    "Potential alternative providers indicated",
    "No alternative provider evidenced",
    "Substitutability not assessed",
    "Insufficient evidence",
)


PARTICIPATION_EVIDENCE_STATUSES = (
    "evidenced",
    "indicated_but_incomplete",
    "not_yet_assessed",
)


@dataclass(frozen=True)
class ParticipationRelationship:
    source: str
    relationship: str
    target: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParticipationFunction:
    name: str
    evidence_status: str = "not_yet_assessed"
    evidence: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    substitutability_status: str = "Substitutability not assessed"
    alternative_providers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.evidence_status not in PARTICIPATION_EVIDENCE_STATUSES:
            raise ValueError(
                "Unsupported participation evidence status: "
                f"{self.evidence_status}"
            )
        if self.evidence_status == "evidenced" and not self.evidence:
            raise ValueError(
                "Evidenced participation functions require evidence."
            )
        if self.substitutability_status not in SUBSTITUTABILITY_STATUSES:
            raise ValueError(
                "Unsupported substitutability status: "
                f"{self.substitutability_status}"
            )
        if (
            self.substitutability_status
            in {
                "Alternative providers evidenced",
                "Potential alternative providers indicated",
            }
            and not self.alternative_providers
        ):
            raise ValueError(
                "Alternative-provider claims require named providers."
            )


@dataclass(frozen=True)
class InstitutionalParticipationProfile:
    academic_unit: str | None = None
    organizational_context: dict[str, Any] = field(default_factory=dict)
    instructional_functions: tuple[ParticipationFunction, ...] = ()
    relationships: tuple[ParticipationRelationship, ...] = ()
    capabilities: tuple[ParticipationFunction, ...] = ()
