from dataclasses import dataclass, field
from typing import Tuple

from app.constitution.orientation import (
    ConstitutionalOrientation,
)

from app.semantic_control_plane.orientation import (
    InstitutionalOrientation,
)


@dataclass(frozen=True)
class SemanticControlPlaneResult:
    """
    Unified interpretation of an institutional question.

    The Control Plane performs no retrieval and no reasoning.

    It simply answers two questions:

        What institutional concepts is this about?

        What institutional values might be relevant?

    """

    question: str

    institutional_orientation: InstitutionalOrientation

    constitutional_orientation: ConstitutionalOrientation

    notes: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def confidence(self):

        return max(
            self.institutional_orientation.confidence,
            self.constitutional_orientation.confidence,
        )

EOF

