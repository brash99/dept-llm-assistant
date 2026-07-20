from app.control_plane.contracts import (
    SemanticControlPlaneResult,
)
from app.question_scope import classify_question_scope


class SemanticControlPlane:

    def __init__(
        self,
        institutional_service,
        constitutional_service,
    ):

        self.institutional = institutional_service
        self.constitutional = constitutional_service

    def orient(self, question):

        institutional = self.institutional.orient(question)

        constitutional = self.constitutional.orient(question)
        question_scope = getattr(
            institutional,
            "question_scope",
            classify_question_scope(question),
        )

        return SemanticControlPlaneResult(

            question=question,

            institutional_orientation=institutional,

            constitutional_orientation=constitutional,

            notes=(
                "Control Plane interpretation completed before retrieval.",
                (
                    "Question scope: "
                    f"{question_scope.label}."
                ),
            ),
        )
