from app.control_plane.catalog import ProgramCatalog
from app.undergraduate_majors import UndergraduateMajorRegistry
from scripts.audit_undergraduate_majors import audit


CURRENT_CATALOG_MAJORS = {
    "Accounting", "American Studies", "Anthropology", "Art History",
    "Biochemistry", "Biology", "Cellular, Molecular and Physiological Biology",
    "Chemistry", "Classical Studies", "Communication",
    "Computational and Applied Mathematics", "Computer Engineering",
    "Computer Science", "Criminology", "Cybersecurity", "Economics",
    "Electrical Engineering", "English", "Environmental Studies", "Finance",
    "French", "German", "Global Commerce and Culture", "Health Studies",
    "History", "Information Science", "Integrative Biology",
    "Interdisciplinary Studies", "International Affairs", "Kinesiology",
    "Leadership Studies", "Management", "Marketing", "Mathematics", "Music",
    "Neuroscience", "Organismal and Environmental Biology", "Philosophy",
    "Physics", "Political Science", "Psychology", "Social Work", "Sociology",
    "Spanish", "Studio Art", "Theater",
}


def test_registry_contains_complete_current_catalog_inventory():
    registry = UndergraduateMajorRegistry.load()
    current = {item.display_name for item in registry.majors if item.status == "current"}
    assert current == CURRENT_CATALOG_MAJORS
    assert len(registry.majors) == 50


def test_existing_sec_program_ids_are_reused_without_duplicates():
    registry = UndergraduateMajorRegistry.load()
    existing = ProgramCatalog.from_yaml(
        registry.source_path.parent / "institutional_programs.yaml"
    )
    expected = {item.id for item in existing.all()}
    assert expected == {
        item.major_id for item in registry.majors
        if any(
            evidence.source_type == "governed_program_registry"
            for evidence in item.evidence
        )
    }


def test_authoritative_administrative_assertions_are_all_preserved():
    registry = UndergraduateMajorRegistry.load()
    assertions = [
        evidence for item in registry.majors for evidence in item.evidence
        if evidence.source_type == "authoritative_administrative_mapping"
    ]
    assert len(assertions) == 50
    assert all(item.owner_code for item in assertions)


def test_conflicting_ownership_is_not_silently_resolved():
    registry = UndergraduateMajorRegistry.load()
    neuroscience = registry.resolve_name("Neuroscience")
    assert neuroscience.ownership_status == "conflicting_authoritative_assertions"
    assert neuroscience.owning_academic_unit_id is None
    assert {item.owner_code for item in neuroscience.owner_assertions} == {
        "IDST", "PSYC",
    }
    studio = registry.resolve_name("Studio Art")
    assert studio.owning_academic_unit_id == (
        "academic_unit:department_music_theatre_dance"
    )
    assert studio.ownership_status == (
        "resolved_with_conflicting_catalog_structure"
    )
    assert {item.owner_code for item in studio.owner_assertions} == {"MTD", "FAAH"}


def test_unresolved_and_possible_discontinued_records_remain_visible():
    registry = UndergraduateMajorRegistry.load()
    assert registry.resolve_name("Health Sciences").ownership_status == "unresolved"
    possible = {
        item.display_name for item in registry.majors
        if item.status == "possible_discontinued"
    }
    assert possible == {
        "Environmental Biology", "Fine Arts", "Information Systems",
        "Organismal Biology",
    }


def test_aliases_degrees_and_provenance_are_preserved():
    registry = UndergraduateMajorRegistry.load()
    music = registry.resolve_name("Music (BM)")
    assert music.display_name == "Music"
    assert music.degrees == ("Bachelor of Arts", "Bachelor of Music")
    assert registry.resolve_name("Applied Physics").major_id == "program.physics"
    assert all(item.evidence for item in registry.majors)


def test_validation_report_is_complete_and_deterministic():
    first_registry = UndergraduateMajorRegistry.load()
    second_registry = UndergraduateMajorRegistry.load()
    first = audit(first_registry)
    second = audit(second_registry)
    assert first == second
    assert first["major_count"] == 50
    assert first["current_major_count"] == 46
    assert first["possible_discontinued_count"] == 4
    assert first["source_assertion_counts"] == {
        "authoritative_administrative_mapping": 50,
        "governed_program_registry": 6,
        "official_catalog": 46,
    }
    assert first["majors_missing_from_registry"] == []
    assert first["current_owner_unresolved_count"] == 2
    assert first["effective_dates_known_count"] == 0
    assert first_registry.deterministic_fingerprint == (
        second_registry.deterministic_fingerprint
    )


def test_registry_does_not_claim_capstone_requirements():
    encoded = str(UndergraduateMajorRegistry.load().majors).casefold()
    assert "capstone" not in encoded
