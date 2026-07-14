from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from app.knowledge import KnowledgeObject


class ConstitutionalType(str, Enum):
    """
    Canonical semantic roles for institutional constitutional knowledge.
    """

    MISSION = "mission"
    VISION = "vision"
    STRATEGIC_COMPASS = "strategic_compass"
    STRATEGIC_PLAN = "strategic_plan"
    ACADEMIC_MASTER_PLAN = "academic_master_plan"
    BOARD_PRIORITY = "board_priority"
    INSTITUTIONAL_VALUE = "institutional_value"
    LEARNING_OUTCOME = "learning_outcome"
    GOVERNANCE_PRINCIPLE = "governance_principle"
    OTHER = "other"


@dataclass
class ConstitutionalKnowledgeObject(KnowledgeObject):
    """
    A canonical institutional observation whose semantic role is normative.

    Constitutional Knowledge Objects preserve what an institution explicitly
    declares that it values, prioritizes, aspires to become, or expects its
    decision-makers to consider.

    They do not contain a derived judgment about whether a proposal aligns
    with those values. Alignment remains the responsibility of services.
    """

    constitutional_type: str = ConstitutionalType.OTHER.value
    principles: Tuple[str, ...] = field(default_factory=tuple)
    institutional_scope: Tuple[str, ...] = field(default_factory=tuple)
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    source_knowledge_object_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.object_type != "constitutional_knowledge":
            raise ValueError(
                "ConstitutionalKnowledgeObject.object_type must be "
                "'constitutional_knowledge'."
            )

        try:
            ConstitutionalType(self.constitutional_type)
        except ValueError as exc:
            allowed = ", ".join(
                item.value
                for item in ConstitutionalType
            )

            raise ValueError(
                "Unknown constitutional_type "
                f"{self.constitutional_type!r}. "
                f"Allowed values: {allowed}"
            ) from exc

        self.principles = tuple(self.principles)
        self.institutional_scope = tuple(
            self.institutional_scope
        )

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "ConstitutionalKnowledgeObject":
        payload = dict(data)

        payload["principles"] = tuple(
            payload.get("principles", ())
        )

        payload["institutional_scope"] = tuple(
            payload.get(
                "institutional_scope",
                (),
            )
        )

        return cls(**payload)
