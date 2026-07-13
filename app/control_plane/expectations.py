from dataclasses import dataclass
from typing import List


PROGRAM_EVIDENCE_EXPECTATIONS = [
    "current program status",
    "curriculum",
    "faculty expertise",
    "enrollment and demand",
    "assessment",
    "budget and staffing",
    "facilities",
    "equipment",
    "accreditation",
    "strategic alignment",
    "historical precedent",
]


@dataclass(frozen=True)
class EvidenceExpectation:
    entity_type: str
    categories: List[str]


def expectations_for_program() -> EvidenceExpectation:
    """
    Return general evidence expectations for reasoning about a program.

    These expectations apply to the entity type Program, not to any
    particular major or institutional question.
    """

    return EvidenceExpectation(
        entity_type="program",
        categories=list(PROGRAM_EVIDENCE_EXPECTATIONS),
    )
