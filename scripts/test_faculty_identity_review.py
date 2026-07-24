from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.faculty_identity import (
    FacultyIdentity,
    FacultyIdentityService,
    FacultySourceObservation,
    IdentityAliasRegistry,
)
from app.faculty_identity_review import (
    FacultyIdentityMatchReviewService,
    load_match_reviews,
    save_match_review,
)


def _source(identifier, system, name):
    return FacultySourceObservation(
        observation_reference=identifier,
        knowledge_object_id=identifier,
        object_type=(
            "course_offering_observation"
            if system == "schedule" else "faculty_observation"
        ),
        source_system=system,
        observed_name=name,
        normalized_name=name.casefold(),
        identifiers=(),
        temporal_label="2025_fall" if system == "schedule" else "2026-07-21",
        source_path=f"fixture/{identifier}",
    )


def _identity(identifier, name, source):
    return FacultyIdentity(
        identity_id=f"faculty_identity:{identifier}",
        display_name=name,
        observed_names=(name,),
        normalized_names=(name.casefold(),),
        source_observations=(source,),
        matching_methods=("exact_normalized_name",),
        confidence=0.9,
        ambiguous=False,
        ambiguity_reason=None,
        provenance={},
        deterministic_fingerprint=identifier,
    )


def _objects(schedule_name, workforce_name, email=""):
    return (
        {
            "id": "schedule",
            "object_type": "course_offering_observation",
            "academic_term": "2025_fall",
            "subject": "CPSC",
            "course_code": "CPSC 101",
            "section": "1",
            "crn": "1",
            "instructor_raw": schedule_name,
            "credits": 3,
            "enrollment": 20,
        },
        {
            "id": "directory",
            "object_type": "faculty_observation",
            "snapshot_date": "2026-07-21",
            "display_name": workforce_name,
            "published_titles": ["Professor"],
            "published_department": "School of Engineering and Computing",
            "email": email,
            "profile_url": "https://example.edu/faculty/profile",
        },
    )


def _proposal(schedule_name, workforce_name, email=""):
    objects = _objects(schedule_name, workforce_name, email)
    identities = (
        _identity("schedule", schedule_name, _source("schedule", "schedule", schedule_name)),
        _identity("workforce", workforce_name, _source("directory", "faculty_directory", workforce_name)),
    )
    decisions = ({
        "faculty_identity_id": "faculty_identity:workforce",
        "display_name": workforce_name,
        "workforce_disposition": "include",
        "analytical_academic_unit_id": "academic_unit:sec",
    },)
    proposals = FacultyIdentityMatchReviewService().propose(
        objects, identities, decisions
    )
    assert proposals
    return proposals[0]


@pytest.mark.parametrize(
    ("schedule_name", "workforce_name", "email"),
    (
        ("Chris Kreider", "Christopher Kreider", "chris.kreider@example.edu"),
        ("Keith Perkins", "Brian Keith Perkins", "keith.perkins@example.edu"),
        ("Md Akib Zabed Khan", "Akib Khan", "akibzabed.khan@example.edu"),
        ("Toni Riedl", "Anton Riedl", "riedl@example.edu"),
        ("Will Phelps", "William Phelps", "william.phelps@example.edu"),
    ),
)
def test_bounded_candidate_generation_finds_review_cases(
    schedule_name, workforce_name, email
):
    proposal = _proposal(schedule_name, workforce_name, email)
    assert proposal.schedule_name == schedule_name
    assert proposal.workforce_name == workforce_name
    assert proposal.workforce_academic_unit_id == "academic_unit:sec"
    assert proposal.score >= 55
    assert "exact_family_name" in proposal.proposal_reasons
    assert proposal.schedule_section_count == 1
    assert proposal.schedule_sch == 60


def _alias_fixture(path):
    path.write_text(
        "schema_version: 1\n"
        "registry_id: test.aliases\n"
        "identities: []\n",
        encoding="utf-8",
    )


def test_approval_writes_governed_alias_and_review(tmp_path):
    alias_path = tmp_path / "aliases.yaml"
    review_path = tmp_path / "reviews.yaml"
    _alias_fixture(alias_path)
    proposal = _proposal("Will Phelps", "William Phelps", "william.phelps@example.edu")
    save_match_review(
        proposal, "approved", "Institutional Reviewer",
        alias_path=alias_path, review_path=review_path,
        review_date="2026-07-23",
    )
    registry = IdentityAliasRegistry.load(alias_path)
    alias = registry.aliases[0]
    assert alias.identity_key == "workforce"
    assert alias.canonical_display_name == "William Phelps"
    assert set(alias.observed_names) == {"Will Phelps", "William Phelps"}
    reviews = load_match_reviews(review_path)
    assert reviews[0]["decision"] == "approved"
    assert reviews[0]["reviewer"] == "Institutional Reviewer"


@pytest.mark.parametrize("decision", ("rejected", "needs_more_evidence"))
def test_nonapproval_preserves_alias_registry(tmp_path, decision):
    alias_path = tmp_path / "aliases.yaml"
    review_path = tmp_path / "reviews.yaml"
    _alias_fixture(alias_path)
    before = alias_path.read_bytes()
    proposal = _proposal("Will Phelps", "William Phelps")
    save_match_review(
        proposal, decision, "Reviewer",
        alias_path=alias_path, review_path=review_path,
    )
    assert alias_path.read_bytes() == before
    assert load_match_reviews(review_path)[0]["decision"] == decision


def test_approved_alias_merges_without_changing_raw_observations(tmp_path):
    alias_path = tmp_path / "aliases.yaml"
    review_path = tmp_path / "reviews.yaml"
    _alias_fixture(alias_path)
    objects = _objects("Will Phelps", "William Phelps")
    proposal = _proposal("Will Phelps", "William Phelps")
    before = yaml.safe_dump(objects)
    save_match_review(
        proposal, "approved", "Reviewer",
        alias_path=alias_path, review_path=review_path,
    )
    audit = FacultyIdentityService(IdentityAliasRegistry.load(alias_path)).audit(objects)
    assert len(audit.identities) == 1
    assert audit.identities[0].identity_id == "faculty_identity:workforce"
    assert set(audit.identities[0].observed_names) == {"Will Phelps", "William Phelps"}
    assert yaml.safe_dump(objects) == before


def test_different_family_name_is_not_proposed():
    objects = _objects("Will Phelps", "William Smith")
    identities = (
        _identity("schedule", "Will Phelps", _source("schedule", "schedule", "Will Phelps")),
        _identity("workforce", "William Smith", _source("directory", "faculty_directory", "William Smith")),
    )
    decisions = ({
        "faculty_identity_id": "faculty_identity:workforce",
        "workforce_disposition": "include",
        "analytical_academic_unit_id": "academic_unit:sec",
    },)
    assert FacultyIdentityMatchReviewService().propose(
        objects, identities, decisions
    ) == ()


def test_conflicting_governed_alias_is_rejected_without_overwrite(tmp_path):
    alias_path = tmp_path / "aliases.yaml"
    review_path = tmp_path / "reviews.yaml"
    alias_path.write_text(
        "schema_version: 1\n"
        "registry_id: test.aliases\n"
        "identities:\n"
        "  - identity_key: another_person\n"
        "    canonical_display_name: Another Person\n"
        "    observed_names: [Will Phelps]\n"
        "    confidence: 1.0\n"
        "    evidence:\n"
        "      source: fixture\n"
        "      assertion: Reviewed fixture alias.\n",
        encoding="utf-8",
    )
    before = alias_path.read_bytes()
    with pytest.raises(ValueError, match="Duplicate governed faculty alias"):
        save_match_review(
            _proposal("Will Phelps", "William Phelps"),
            "approved",
            "Reviewer",
            alias_path=alias_path,
            review_path=review_path,
        )
    assert alias_path.read_bytes() == before
    assert not review_path.exists()
