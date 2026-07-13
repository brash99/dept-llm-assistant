from pathlib import Path

from app.control_plane.catalog import ProgramCatalog
from app.control_plane.orientation import ProgramOrientationService
from app.control_plane.resolver import ProgramResolver


class FakeNeighborhoodService:
    """
    Test double that avoids loading sentence-transformers or a GPU.
    """

    def __init__(self):
        self.calls = []

    def neighbors(
        self,
        query_text,
        exclude_program_id=None,
        limit=5,
    ):
        self.calls.append(
            {
                "query_text": query_text,
                "exclude_program_id": exclude_program_id,
                "limit": limit,
            }
        )
        return []


def build_service():
    catalog = ProgramCatalog.from_yaml(
        Path("config/institutional_programs.yaml")
    )
    resolver = ProgramResolver(catalog)
    neighborhood_service = FakeNeighborhoodService()

    service = ProgramOrientationService(
        resolver=resolver,
        neighborhood_service=neighborhood_service,
        neighbor_limit=5,
    )

    return service, neighborhood_service


def test_existing_program_is_resolved_as_asserted_entity():
    service, neighborhood_service = build_service()

    orientation = service.orient(
        "What additional resources would be required for "
        "Electrical Engineering?"
    )

    assert orientation.has_resolved_entities
    assert not orientation.has_proposed_concepts
    assert len(orientation.resolved_entities) == 1
    assert orientation.resolved_entities[0].name == "Electrical Engineering"
    assert orientation.resolution.found
    assert orientation.confidence == 1.0

    call = neighborhood_service.calls[0]
    assert call["exclude_program_id"] == orientation.resolved_entities[0].id
    assert "Resolved existing academic program" in call["query_text"]


def test_new_program_is_recognized_as_proposed_concept():
    service, neighborhood_service = build_service()

    orientation = service.orient(
        "What additional resources would be required to start a "
        "Mechanical Engineering program?"
    )

    assert not orientation.has_resolved_entities
    assert orientation.has_proposed_concepts
    assert len(orientation.proposed_concepts) == 1

    concept = orientation.proposed_concepts[0]

    assert concept.name == "Mechanical Engineering"
    assert concept.concept_type == "academic_program"
    assert concept.asserted is False
    assert concept.confidence == 0.85
    assert orientation.confidence == 0.85

    call = neighborhood_service.calls[0]
    assert call["exclude_program_id"] is None
    assert (
        "Proposed academic program concept: Mechanical Engineering."
        in call["query_text"]
    )


def test_existing_program_is_not_mislabeled_as_proposed():
    service, _ = build_service()

    orientation = service.orient(
        "Should we add resources to the Electrical Engineering program?"
    )

    assert orientation.has_resolved_entities
    assert not orientation.has_proposed_concepts
    assert orientation.resolved_entities[0].name == "Electrical Engineering"


def test_non_program_question_remains_unresolved():
    service, _ = build_service()

    orientation = service.orient(
        "How has undergraduate enrollment changed over the last five years?"
    )

    assert not orientation.has_resolved_entities
    assert not orientation.has_proposed_concepts
    assert orientation.confidence == 0.0


def test_empty_question_is_rejected():
    service, _ = build_service()

    try:
        service.orient("   ")
    except ValueError as error:
        assert str(error) == "Question must not be empty."
    else:
        raise AssertionError("Expected ValueError for empty question.")
