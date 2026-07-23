from __future__ import annotations

import json

import pytest

from app.faculty_identity import (
    FacultyIdentityService,
    IdentityAliasRegistry,
    normalize_person_name,
)
from scripts.audit_faculty_identity import main
from scripts.a100_testing_scripts.validate_faculty_identity_governance_precedence import (
    _partition_unit_labels,
)


def _directory(identifier, name, **extra):
    return {
        "id": identifier,
        "object_type": "faculty_observation",
        "display_name": name,
        "snapshot_date": "2026-07-21",
        "provenance": {"source": "faculty-directory"},
        **extra,
    }


def _catalog(identifier, name):
    return {
        "id": identifier,
        "object_type": "catalog_faculty_observation",
        "published_name": name,
        "catalog_year": "2025-26",
        "provenance": {"source": "academic-catalog"},
    }


def _schedule(identifier, name):
    return {
        "id": identifier,
        "object_type": "course_offering_observation",
        "instructor_raw": name,
        "academic_term": "2025_fall",
        "course_code": "TEST 101",
        "provenance": {"source": "schedule.csv"},
    }


def _roster(identifier, *names):
    return {
        "id": identifier,
        "object_type": "department_faculty_roster_observation",
        "catalog_year": "2025-26",
        "academic_unit": "Department of Examples",
        "entries": [
            {"published_name": name, "published_category": "Faculty"}
            for name in names
        ],
        "provenance": {"source": "academic-catalog"},
    }


def test_name_normalization_supports_order_punctuation_and_retains_published_form():
    forward = normalize_person_name("Robert E. Colvin")
    reversed_name = normalize_person_name("Colvin, Robert E.")
    assert forward.normalized_name == reversed_name.normalized_name == "robert e colvin"
    assert forward.published_name == "Robert E. Colvin"
    assert reversed_name.published_name == "Colvin, Robert E."
    assert normalize_person_name("Dr. Robert Earl Colvin").normalized_name == (
        "robert earl colvin"
    )
    assert normalize_person_name("Staff") is None
    assert normalize_person_name("Doe, Jane | Smith, John") is None


def test_bob_colvin_is_one_identity_across_sources_without_appointment_inference():
    values = (
        _directory("directory:bob", "Bob Colvin"),
        _catalog("catalog:robert", "Robert Colvin"),
        _roster("roster:colvin", "Robert E. Colvin"),
        _schedule("schedule:colvin", "Colvin, Robert Earl"),
        _catalog("catalog:initial", "R. Colvin"),
    )
    result = FacultyIdentityService().audit(values)
    assert len(result.identities) == 1
    identity = result.identities[0]
    assert identity.identity_id == "faculty_identity:bob_colvin"
    assert identity.display_name == "Robert Colvin"
    assert len(identity.source_observations) == 5
    assert set(identity.observed_names) == {
        "Bob Colvin", "Robert Colvin", "Robert E. Colvin",
        "Colvin, Robert Earl", "R. Colvin",
    }
    assert "explicit_governed_alias" in identity.matching_methods
    encoded = json.dumps(identity.to_dict()).casefold()
    for prohibited in (
        "appointment_type", "employment_status", "tenure", "fte",
        "faculty_home", "administrative_appointment",
    ):
        assert prohibited not in encoded


def test_exact_identifier_can_link_names_but_similar_names_do_not_merge():
    values = (
        _directory("one", "Alex Morgan", email="alex@example.edu"),
        _directory("two", "A. Morgan", email="alex@example.edu"),
        _catalog("three", "Alexa Morgan"),
        _catalog("four", "Alex Morton"),
    )
    result = FacultyIdentityService().audit(values)
    clusters = {
        frozenset(item.observed_names): item for item in result.identities
    }
    linked = clusters[frozenset({"Alex Morgan", "A. Morgan"})]
    assert "exact_identifier" in linked.matching_methods
    assert frozenset({"Alexa Morgan"}) in clusters
    assert frozenset({"Alex Morton"}) in clusters
    assert result.summary["duplicate_identity_id_count"] == 0


def test_reviewed_aliases_resolve_before_initial_and_middle_name_rules():
    values = (
        _directory("patricia", "Patricia Siewe Seuchie"),
        _catalog("patricia-short", "Patricia Seuchie"),
        _catalog("patricia-full", "Patricia Angele Siewe Seuchie"),
        _directory("james", "James P. Kelly"),
        _catalog("james-initials", "J. P. Kelly"),
        _directory("jessica", "Jessica Kelly"),
        _directory("shinhye", "Shinhye Kim"),
        _catalog("shinhye-initial", "S. Kim"),
        _directory("seung", "Seung-Hye Kim"),
        _directory("cynthia-canonical", "Cynthia Vacca Davis"),
        _schedule("cynthia-schedule", "Cynthia Davis"),
        _catalog("cynthia-other-middle", "Cynthia Lewis Davis"),
        _directory("ann-canonical", "Ann Mazzocca Bellecci"),
        _schedule("ann-schedule", "Ann Bellecci"),
        _catalog("ann-other-middle", "Ann Louise Bellecci"),
    )
    result = FacultyIdentityService().audit(values)
    by_id = {item.identity_id: item for item in result.identities}
    assert set(by_id["faculty_identity:patricia_siewe_seuchie"].observed_names) == {
        "Patricia Siewe Seuchie", "Patricia Seuchie",
        "Patricia Angele Siewe Seuchie",
    }
    assert not by_id["faculty_identity:patricia_siewe_seuchie"].ambiguous
    assert len([
        identity for identity in result.identities
        if any("Patricia" in name for name in identity.observed_names)
    ]) == 1
    assert not any(
        identity.identity_id != "faculty_identity:patricia_siewe_seuchie"
        and "Patricia Angele Siewe Seuchie" in identity.observed_names
        for identity in result.identities
    )
    assert set(by_id["faculty_identity:james_p_kelly"].observed_names) == {
        "James P. Kelly", "J. P. Kelly",
    }
    assert "Jessica Kelly" not in by_id["faculty_identity:james_p_kelly"].observed_names
    assert set(by_id["faculty_identity:shinhye_kim"].observed_names) == {
        "Shinhye Kim", "S. Kim",
    }
    assert "Seung-Hye Kim" not in by_id["faculty_identity:shinhye_kim"].observed_names
    assert not by_id["faculty_identity:james_p_kelly"].ambiguous
    assert not by_id["faculty_identity:shinhye_kim"].ambiguous
    assert set(by_id["faculty_identity:cynthia_vacca_davis"].observed_names) == {
        "Cynthia Vacca Davis", "Cynthia Davis",
    }
    assert set(by_id["faculty_identity:ann_mazzocca_bellecci"].observed_names) == {
        "Ann Mazzocca Bellecci", "Ann Bellecci",
    }
    for identity_id, schedule_id in (
        ("faculty_identity:cynthia_vacca_davis", "cynthia-schedule"),
        ("faculty_identity:ann_mazzocca_bellecci", "ann-schedule"),
    ):
        identity = by_id[identity_id]
        assert not identity.ambiguous
        assert any(
            source.knowledge_object_id == schedule_id
            and source.source_system == "schedule"
            for source in identity.source_observations
        )
    assert not any(
        identity.identity_id not in {
            "faculty_identity:cynthia_vacca_davis",
            "faculty_identity:ann_mazzocca_bellecci",
        }
        and any(name in {"Cynthia Davis", "Ann Bellecci"} for name in identity.observed_names)
        for identity in result.identities
    )
    assert result.summary["duplicate_identity_id_count"] == 0


def test_ungoverned_middle_name_collision_remains_ambiguous():
    result = FacultyIdentityService().audit((
        _catalog("short", "Marla Jones"),
        _catalog("anne", "Marla Anne Jones"),
        _catalog("beth", "Marla Beth Jones"),
    ))
    short = next(
        identity for identity in result.identities
        if identity.observed_names == ("Marla Jones",)
    )
    assert short.ambiguous
    assert short.ambiguity_reason == "multiple_compatible_middle_name_candidates"


def test_conflicting_governed_keys_joined_by_identifier_remain_ambiguous():
    result = FacultyIdentityService().audit((
        _directory(
            "cynthia", "Cynthia Vacca Davis", email="shared@example.edu"
        ),
        _directory(
            "ann", "Ann Mazzocca Bellecci", email="shared@example.edu"
        ),
    ))
    assert len(result.identities) == 1
    identity = result.identities[0]
    assert identity.ambiguous
    assert identity.ambiguity_reason == "conflicting_governed_identity_aliases"
    assert "exact_identifier" in identity.matching_methods


def test_alias_registry_rejects_duplicate_aliases(tmp_path):
    registry = tmp_path / "aliases.yaml"
    registry.write_text("""
registry_id: duplicate-test
identities:
  - identity_key: one
    canonical_display_name: Jane Doe
    observed_names: [Jane Doe]
    confidence: 1.0
    evidence: {source: review:one, assertion: reviewed}
  - identity_key: two
    canonical_display_name: Janet Doe
    observed_names: [Jane Doe]
    confidence: 1.0
    evidence: {source: review:two, assertion: reviewed}
""", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate governed faculty alias"):
        IdentityAliasRegistry.load(registry)


def test_no_fuzzy_name_matching_is_introduced():
    result = FacultyIdentityService().audit((
        _directory("one", "Patricia Siewe Seuchie"),
        _catalog("typo", "Patricia Siewe Seuchi"),
        _directory("kim", "Shinhye Kim"),
        _catalog("similar", "Shinhee Kim"),
    ))
    assert len(result.identities) == 4


def test_identity_validator_reports_unit_ambiguity_without_hiding_real_gaps():
    ambiguous, blocking = _partition_unit_labels((
        {"classification": "ambiguous", "published_label": "Multiple roles"},
        {"classification": "genuinely_unresolved", "published_label": "Unknown unit"},
    ))
    assert [item["published_label"] for item in ambiguous] == ["Multiple roles"]
    assert [item["published_label"] for item in blocking] == ["Unknown unit"]


def test_bounded_middle_matching_and_ambiguous_initials_do_not_guess():
    values = (
        _catalog("a", "Robert E. Smith"),
        _catalog("b", "Robert Earl Smith"),
        _catalog("c", "Richard Smith"),
        _catalog("d", "R. Smith"),
        _catalog("e", "Jordan A. Lee"),
        _catalog("f", "Jordan Avery Lee"),
        _catalog("g", "Jordan B. Lee"),
        _catalog("h", "Jordan Blake Lee"),
    )
    result = FacultyIdentityService().audit(values)
    smith = [item for item in result.identities if "Smith" in item.display_name]
    assert any(set(item.observed_names) == {
        "Robert E. Smith", "Robert Earl Smith"
    } for item in smith)
    initial = next(item for item in smith if item.observed_names == ("R. Smith",))
    assert initial.ambiguous
    assert initial.ambiguity_reason == "multiple_given_name_candidates_for_initial"
    lee_clusters = [item for item in result.identities if "Lee" in item.display_name]
    assert len(lee_clusters) == 4


def test_identity_audit_reports_sources_clusters_and_is_deterministic():
    values = (
        _directory("d1", "Jane Doe"),
        _catalog("c1", "Jane Doe"),
        _roster("r1", "Doe, Jane", "John Roe"),
        _schedule("s1", "Jane Doe"),
        _schedule("s2", "Staff"),
    )
    service = FacultyIdentityService()
    first = service.audit(values)
    second = service.audit(reversed(values))
    assert first.deterministic_fingerprint == second.deterministic_fingerprint
    assert first.summary["identity_bearing_observation_count"] == 5
    assert first.summary["identity_count"] == 2
    assert first.summary["single_observation_identity_count"] == 1
    assert first.summary["multi_observation_identity_count"] == 1
    assert first.summary["excluded_missing_or_placeholder_name_count"] == 1
    assert first.summary["source_system_coverage"] == {
        "catalog_faculty": 1,
        "department_roster": 2,
        "faculty_directory": 1,
        "schedule": 1,
    }


def test_cli_writes_compact_json_markdown_and_identity_manifest(tmp_path, capsys):
    root = tmp_path / "normalized"
    root.mkdir()
    for index, value in enumerate((
        _directory("d1", "Bob Colvin"),
        _catalog("c1", "Robert Colvin"),
    )):
        (root / f"{index}.json").write_text(json.dumps(value), encoding="utf-8")
    output = tmp_path / "audit"
    assert main([
        "--normalized-root", str(root), "--output-dir", str(output)
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["identity_count"] == 1
    assert printed["duplicate_identity_id_count"] == 0
    assert (output / "faculty_identity_audit.json").is_file()
    assert (output / "faculty_identity_audit.md").is_file()
    identities = (output / "faculty_identities.jsonl").read_text().splitlines()
    assert len(identities) == 1
    assert json.loads(identities[0])["identity_id"] == "faculty_identity:bob_colvin"
