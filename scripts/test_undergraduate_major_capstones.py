from app.undergraduate_major_capstones import (
    UndergraduateMajorCapstoneRegistry,
)
from scripts.audit_undergraduate_major_capstones import audit


def test_every_current_major_has_exactly_one_governed_capstone_record():
    registry = UndergraduateMajorCapstoneRegistry.load()
    assert len(registry.requirements) == 46
    assert len({item.major_id for item in registry.requirements}) == 46


def test_required_sequences_and_alternatives_remain_distinct():
    registry = UndergraduateMajorCapstoneRegistry.load()
    computer_engineering = registry.get("program.computer_engineering")
    assert computer_engineering.requirement_type == "required_capstone_sequence"
    assert computer_engineering.pathways[0].course_ids == (
        "CPEN 497W", "CPEN 498",
    )
    anthropology = registry.get("undergraduate_major:anthropology")
    assert anthropology.requirement_type == "thesis_or_seminar_options"
    assert {pathway.pathway_id for pathway in anthropology.pathways} == {
        "senior_seminar", "advanced_thesis",
    }


def test_no_capstone_is_not_silently_inferred():
    registry = UndergraduateMajorCapstoneRegistry.load()
    for major_id in (
        "undergraduate_major:biochemistry",
        "undergraduate_major:biology",
        "undergraduate_major:cellular_molecular_physiological_biology",
        "undergraduate_major:classical_studies",
        "undergraduate_major:integrative_biology",
        "undergraduate_major:kinesiology",
        "undergraduate_major:leadership_studies",
        "undergraduate_major:organismal_environmental_biology",
    ):
        item = registry.get(major_id)
        assert item.requirement_type == "no_identifiable_capstone"
        assert not any(pathway.course_ids for pathway in item.pathways)


def test_music_preserves_degree_pathways_and_unresolved_course_identity():
    music = UndergraduateMajorCapstoneRegistry.load().get(
        "undergraduate_major:music"
    )
    assert music.requirement_type == "multiple_pathways"
    assert {pathway.pathway_id for pathway in music.pathways} == {
        "ba_music",
        "bm_performance",
        "bm_composition",
        "bm_pre_certification",
    }
    assert any(
        pathway.requirement_type == "unresolved"
        for pathway in music.pathways
    )


def test_audit_is_complete_and_deterministic():
    first = audit(UndergraduateMajorCapstoneRegistry.load())
    second = audit(UndergraduateMajorCapstoneRegistry.load())
    assert first == second
    assert first["major_count"] == 46
    assert first["deterministic_fingerprint"]
