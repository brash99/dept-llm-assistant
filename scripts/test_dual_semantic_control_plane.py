from dataclasses import dataclass

from app.constitution import (
    ConstitutionalCatalog,
    ConstitutionalKnowledgeObject,
    ConstitutionalOrientationService,
)
from app.control_plane.dual_orientation import (
    SemanticControlPlaneResult,
    SemanticControlPlaneService,
)


@dataclass(frozen=True)
class FakeInstitutionalOrientation:
    resolved_entities: tuple = ()
    proposed_concepts: tuple = ()
    semantic_neighbors: tuple = ()
    notes: tuple = ()
    confidence: float = 0.0


class FakeInstitutionalService:
    def __init__(self, confidence=0.0):
        self.confidence = confidence

    def orient(self, question):
        return FakeInstitutionalOrientation(
            notes=(
                "Fake institutional orientation.",
            ),
            confidence=self.confidence,
        )


def make_constitutional_service():
    obj = ConstitutionalKnowledgeObject(
        id="constitutional:test",
        object_type="constitutional_knowledge",
        title="Strategic Compass",
        text="Test constitutional source.",
        constitutional_type="strategic_compass",
        principles=(
            "advance the power and promise of an education embedded in the liberal arts",
            "connect with our community",
            "create a stronger culture of inclusion and belonging",
            "build a foundation to thrive",
        ),
        institutional_scope=(
            "Christopher Newport University",
        ),
    )

    return ConstitutionalOrientationService(
        catalog=ConstitutionalCatalog([obj]),
    )


def test_dual_control_plane_preserves_both_orientations():
    service = SemanticControlPlaneService(
        institutional_service=(
            FakeInstitutionalService(
                confidence=0.25
            )
        ),
        constitutional_service=(
            make_constitutional_service()
        ),
    )

    result = service.orient(
        "Should CNU create a Mechanical Engineering "
        "major for regional workforce needs, and what "
        "facilities and funding would be required?"
    )

    assert isinstance(
        result,
        SemanticControlPlaneResult,
    )

    assert (
        result.institutional_orientation.confidence
        == 0.25
    )

    assert (
        result.constitutional_orientation.matches
    )

    assert (
        result.requires_constitutional_retrieval
        is True
    )

    assert result.confidence >= 0.25


def test_dual_control_plane_keeps_spaces_separate():
    service = SemanticControlPlaneService(
        institutional_service=(
            FakeInstitutionalService()
        ),
        constitutional_service=(
            make_constitutional_service()
        ),
    )

    result = service.orient(
        "How would this improve inclusion "
        "and belonging?"
    )

    assert (
        result.constitutional_orientation
        .matches[0]
        .principle
        == "create a stronger culture of inclusion and belonging"
    )

    assert (
        result.institutional_orientation
        .resolved_entities
        == ()
    )


def test_dual_control_plane_rejects_empty_question():
    service = SemanticControlPlaneService(
        institutional_service=(
            FakeInstitutionalService()
        ),
        constitutional_service=(
            make_constitutional_service()
        ),
    )

    try:
        service.orient("   ")
    except ValueError as error:
        assert "must not be empty" in str(error)
    else:
        raise AssertionError(
            "Expected empty question to fail."
        )
