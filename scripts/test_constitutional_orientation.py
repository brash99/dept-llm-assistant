from app.constitution import (
    ConstitutionalCatalog,
    ConstitutionalKnowledgeObject,
    ConstitutionalOrientationService,
)


def make_catalog() -> ConstitutionalCatalog:
    obj = ConstitutionalKnowledgeObject(
        id="constitutional:test",
        object_type="constitutional_knowledge",
        title="Strategic Compass",
        text="Test constitutional text.",
        constitutional_type="strategic_compass",
        principles=(
            "advance the power and promise of an education embedded in the liberal arts",
            "connect with our community",
            "create a stronger culture of inclusion and belonging",
            "build a foundation to thrive",
        ),
        institutional_scope=(
            "Test University",
        ),
    )

    return ConstitutionalCatalog([obj])


def test_mechanical_engineering_question_maps_to_multiple_spaces():
    service = ConstitutionalOrientationService(
        catalog=make_catalog(),
    )

    orientation = service.orient(
        "Should we create a Mechanical Engineering "
        "major to meet regional workforce demand, "
        "and what faculty, facilities, and funding "
        "would be required?"
    )

    principles = set(
        orientation.relevant_principles
    )

    assert (
        "advance the power and promise of an education embedded in the liberal arts"
        in principles
    )

    assert (
        "connect with our community"
        in principles
    )

    assert (
        "build a foundation to thrive"
        in principles
    )

    assert (
        orientation.requires_constitutional_retrieval
        is True
    )


def test_inclusion_question_maps_to_create():
    service = ConstitutionalOrientationService(
        catalog=make_catalog(),
    )

    orientation = service.orient(
        "How would this proposal improve "
        "accessibility, inclusion, and belonging?"
    )

    assert (
        orientation.matches[0].principle
        == "create a stronger culture of inclusion and belonging"
    )


def test_neutral_operational_question_can_have_no_match():
    service = ConstitutionalOrientationService(
        catalog=make_catalog(),
    )

    orientation = service.orient(
        "What is the room number for the meeting?"
    )

    assert orientation.matches == ()
    assert orientation.confidence == 0.0


def test_orientation_is_explainable():
    service = ConstitutionalOrientationService(
        catalog=make_catalog(),
    )

    orientation = service.orient(
        "What regional partnerships and workforce "
        "needs support this proposal?"
    )

    first = orientation.matches[0]

    assert first.method == "lexical_profile"
    assert first.matched_terms
    assert first.constitutional_object_id == (
        "constitutional:test"
    )
