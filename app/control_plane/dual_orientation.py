from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from app.constitution import (
    ConstitutionalOrientation,
    ConstitutionalOrientationService,
)
from app.control_plane.orientation import (
    InstitutionalOrientation,
    ProgramOrientationService,
)


@dataclass(frozen=True)
class SemanticControlPlaneResult:
    """
    Unified, pre-retrieval interpretation of an institutional question.

    The result preserves two independent semantic spaces:

    - institutional orientation: entities, proposed concepts, and neighbors
    - constitutional orientation: potentially relevant values and priorities

    It performs no retrieval, alignment judgment, or recommendation.
    """

    question: str
    institutional_orientation: InstitutionalOrientation
    constitutional_orientation: ConstitutionalOrientation
    notes: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ValueError(
                "Semantic Control Plane question must not be empty."
            )

    @property
    def confidence(self) -> float:
        return max(
            self.institutional_orientation.confidence,
            self.constitutional_orientation.confidence,
        )

    @property
    def requires_constitutional_retrieval(self) -> bool:
        return (
            self.constitutional_orientation
            .requires_constitutional_retrieval
        )

    def to_dict(self) -> Dict[str, Any]:
        institutional = self.institutional_orientation

        return {
            "question": self.question,
            "institutional_orientation": {
                "resolved_entities": [
                    {
                        "id": entity.id,
                        "name": entity.name,
                        "degree_type": entity.degree_type,
                        "department": entity.department,
                        "school": entity.school,
                    }
                    for entity in institutional.resolved_entities
                ],
                "proposed_concepts": [
                    {
                        "name": concept.name,
                        "concept_type": concept.concept_type,
                        "extraction_method": (
                            concept.extraction_method
                        ),
                        "confidence": concept.confidence,
                    }
                    for concept in institutional.proposed_concepts
                ],
                "semantic_neighbors": [
                    {
                        "program": neighbor.program.name,
                        "score": neighbor.score,
                        "method": neighbor.method,
                    }
                    for neighbor in institutional.semantic_neighbors
                ],
                "notes": list(institutional.notes),
                "confidence": institutional.confidence,
            },
            "constitutional_orientation": (
                self.constitutional_orientation.to_dict()
            ),
            "notes": list(self.notes),
            "confidence": self.confidence,
            "requires_constitutional_retrieval": (
                self.requires_constitutional_retrieval
            ),
        }


class SemanticControlPlaneService:
    """
    Coordinates ISO's empirical and constitutional interpreters.

    Both orientations are produced before retrieval and remain independently
    inspectable.
    """

    def __init__(
        self,
        *,
        institutional_service: ProgramOrientationService,
        constitutional_service: ConstitutionalOrientationService,
    ) -> None:
        self.institutional_service = institutional_service
        self.constitutional_service = constitutional_service

    def orient(
        self,
        question: str,
    ) -> SemanticControlPlaneResult:
        if not question.strip():
            raise ValueError(
                "Question must not be empty."
            )

        institutional = (
            self.institutional_service.orient(
                question
            )
        )

        constitutional = (
            self.constitutional_service.orient(
                question
            )
        )

        return SemanticControlPlaneResult(
            question=question,
            institutional_orientation=institutional,
            constitutional_orientation=constitutional,
            notes=(
                "Dual-space interpretation completed "
                "before institutional evidence retrieval.",
            ),
        )
