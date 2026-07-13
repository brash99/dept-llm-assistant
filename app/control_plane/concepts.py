from dataclasses import dataclass


@dataclass(frozen=True)
class InstitutionalConcept:
    """
    A concept discussed in an institutional question but not asserted as an
    existing institutional entity.

    Example: Mechanical Engineering may be recognized as a proposed academic
    program even when it is absent from the institutional program catalog.
    """

    name: str
    concept_type: str
    asserted: bool = False
    confidence: float = 0.0
    extraction_method: str = "unknown"
