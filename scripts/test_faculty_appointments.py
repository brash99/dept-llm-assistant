from __future__ import annotations

import json

from app.faculty_appointments import FacultyAppointmentObservationService
from scripts.audit_faculty_appointments import main


def _directory(identifier, name="Jane Doe", titles=("Professor",), unit="Communication", **extra):
    return {
        "id": identifier,
        "object_type": "faculty_observation",
        "display_name": name,
        "published_titles": list(titles),
        "published_department": unit,
        "snapshot_date": "2026-07-21",
        "relative_source_path": f"faculty/{identifier}.html",
        "provenance": {"source": "faculty-directory"},
        **extra,
    }


def _catalog(identifier, name="Jane Doe", title="Associate Professor", unit="Communication", year="2025-26", **extra):
    return {
        "id": identifier,
        "object_type": "catalog_faculty_observation",
        "published_name": name,
        "published_title": title,
        "academic_unit": unit,
        "catalog_year": year,
        "relative_source_path": f"catalogs/{year}.pdf",
        "provenance": {"source": "catalog"},
        **extra,
    }


def _roster(identifier, name="Jane Doe", category="Faculty", unit="Communication", year="2025-26"):
    return {
        "id": identifier,
        "object_type": "department_faculty_roster_observation",
        "academic_unit": unit,
        "catalog_year": year,
        "entries": [{"published_name": name, "published_category": category}],
        "provenance": {"source": "catalog"},
    }


def _schedule(identifier, name="Jane Doe"):
    return {
        "id": identifier,
        "object_type": "course_offering_observation",
        "instructor_raw": name,
        "instructor_type": {"normalized_value": "full_time"},
        "academic_term": "2025_fall",
        "course_code": "TEST 101",
        "provenance": {"source": "schedule"},
    }


def test_directory_title_emits_source_scoped_faculty_appointment():
    result = FacultyAppointmentObservationService().audit((
        _directory("d1", titles=("Assistant Professor",)),
    ))
    assert len(result.faculty_appointments) == 1
    appointment = result.faculty_appointments[0]
    assert appointment.published_titles == ("Assistant Professor",)
    assert appointment.normalized_ranks == ("assistant_professor",)
    assert appointment.temporal_label == "2026-07-21"
    assert appointment.academic_unit_id == "academic_unit:department_communication_studies"
    assert appointment.current_status_claim is None
    assert "published_unit_is_not_faculty_home_assertion" in appointment.evidence_limitations


def test_patricia_directory_observation_links_to_governed_identity():
    result = FacultyAppointmentObservationService().audit((
        _directory("patricia-directory", name="Patricia Seuchie"),
        _catalog(
            "patricia-catalog",
            name="Patricia Angele Siewe Seuchie",
        ),
    ))
    patricia = [
        item for item in result.faculty_appointments
        if item.observed_person_name == "Patricia Seuchie"
    ]
    assert len(patricia) == 1
    assert patricia[0].faculty_identity_id == (
        "faculty_identity:patricia_siewe_seuchie"
    )
    assert result.summary["identity_unlinked_observation_count"] == 0
    assert result.summary["ambiguous_or_unlinked_record_count"] == 0


def test_catalog_and_roster_are_edition_claims_not_current_employment():
    result = FacultyAppointmentObservationService().audit((
        _catalog("c1", title="Associate Professor", appointment_year="2018"),
        _roster("r1", category="Faculty"),
    ))
    catalog = next(item for item in result.faculty_appointments if item.source_system == "catalog_faculty")
    roster = next(item for item in result.faculty_appointments if item.source_system == "department_roster")
    assert catalog.temporal_label == roster.temporal_label == "2025-26"
    assert catalog.appointment_year_published == "2018"
    assert catalog.current_status_claim is None
    assert "catalog_edition_claim" in catalog.evidence_fitness
    assert roster.appointment_category_published == "Faculty"
    assert "department_roster_claim" in roster.evidence_fitness


def test_schedule_is_teaching_assignment_and_never_faculty_appointment():
    result = FacultyAppointmentObservationService().audit((_schedule("s1"),))
    assert result.faculty_appointments == ()
    assert result.administrative_appointments == ()
    assert result.employment_statuses == ()
    assert result.summary["teaching_assignment_not_appointment_count"] == 1
    assert result.summary["evidence_fitness_counts"]["teaching_assignment_not_appointment"] == 1


def test_combined_administrative_title_creates_separate_observation():
    result = FacultyAppointmentObservationService().audit((
        _directory("d1", titles=("Professor and Department Chair",)),
    ))
    assert len(result.faculty_appointments) == 1
    assert result.faculty_appointments[0].normalized_ranks == ("professor",)
    assert len(result.administrative_appointments) == 1
    admin = result.administrative_appointments[0]
    assert admin.normalized_administrative_role == "department_chair"
    assert admin.published_administrative_title == "Professor and Department Chair"
    assert "administrative_title_is_not_faculty_home_assertion" in admin.evidence_limitations


def test_program_and_office_leadership_do_not_become_faculty_home():
    result = FacultyAppointmentObservationService().audit((
        _directory("honors", titles=("Professor; Director of Honors",), unit="Psychology"),
        _directory("orca", name="John Roe", titles=("Director of ORCA",), unit="Office of Research and Creative Activity"),
    ))
    honors = next(item for item in result.administrative_appointments if "Honors" in item.published_administrative_title)
    orca = next(item for item in result.administrative_appointments if "ORCA" in item.published_administrative_title)
    assert honors.normalized_administrative_role == "program_director"
    assert honors.administrative_unit_id == "academic_unit:honors_program"
    assert orca.administrative_unit_id == "academic_unit:office_research_creative_activity"
    encoded = json.dumps([honors.to_dict(), orca.to_dict()]).casefold()
    assert "faculty_home_unit" not in encoded
    assert "denominator_eligible" not in encoded


def test_explicit_emeritus_retired_and_former_status_only():
    result = FacultyAppointmentObservationService().audit((
        _directory("e1", titles=("Professor Emerita",)),
        _catalog("r1", name="John Roe", title="Retired Professor"),
        _catalog("f1", name="Alex Poe", title="Former Vice Provost"),
        _catalog("n1", name="Kim Moe", title="Professor"),
    ))
    statuses = {(item.observed_person_name, item.normalized_status) for item in result.employment_statuses}
    assert ("Jane Doe", "emerita") in statuses
    assert ("John Roe", "retired") in statuses
    assert ("Alex Poe", "former") in statuses
    assert not any(name == "Kim Moe" for name, _ in statuses)
    assert any(
        item.normalized_administrative_role == "vice_provost"
        for item in result.administrative_appointments
    )


def test_ambiguous_identity_preserves_appointment_without_forced_link():
    values = (
        _catalog("r", name="Robert Smith", title="Professor"),
        _catalog("x", name="Richard Smith", title="Professor"),
        _catalog("i", name="R. Smith", title="Professor"),
    )
    result = FacultyAppointmentObservationService().audit(values)
    initial = next(
        item for item in result.faculty_appointments
        if item.observed_person_name == "R. Smith"
    )
    assert initial.faculty_identity_id is None
    assert "identity_unresolved" in initial.evidence_fitness
    assert result.summary["ambiguous_or_unlinked_record_count"] == 1
    assert result.summary["identity_review_queue_count"] == 1
    queue = result.identity_review_queue[0]
    assert queue["observed_person_name"] == "R. Smith"
    assert {item["display_name"] for item in queue["deterministic_candidates"]} == {
        "Robert Smith", "Richard Smith",
    }
    assert all(
        "given_initial" in item["candidate_methods"]
        for item in queue["deterministic_candidates"]
    )


def test_rank_unknown_title_and_explicit_current_claim_are_conservative():
    result = FacultyAppointmentObservationService().audit((
        _directory("u1", titles=("Scholar and Coordinator",)),
        _directory("a1", name="John Roe", titles=("Current Lecturer",)),
    ))
    unknown = next(item for item in result.faculty_appointments if item.observed_person_name == "Jane Doe")
    current = next(item for item in result.faculty_appointments if item.observed_person_name == "John Roe")
    assert unknown.published_titles == ("Scholar and Coordinator",)
    assert unknown.normalized_ranks == ()
    assert "combined_or_unknown_title_not_normalized_as_rank" in unknown.evidence_limitations
    assert current.normalized_ranks == ("lecturer",)
    assert current.current_status_claim == "current"
    assert "explicit_current_directory_claim" in current.evidence_fitness


def test_extraction_is_deterministic_unique_and_contains_no_inferred_fte():
    values = (
        _directory("d1", titles=("Professor and Chair",)),
        _catalog("c1", title="Professor Emeritus"),
        _roster("r1", category="Lecturer"),
        _schedule("s1"),
    )
    service = FacultyAppointmentObservationService()
    first = service.audit(values)
    second = service.audit(reversed(values))
    assert first.deterministic_fingerprint == second.deterministic_fingerprint
    ids = [
        *(item.observation_id for item in first.faculty_appointments),
        *(item.observation_id for item in first.administrative_appointments),
        *(item.observation_id for item in first.employment_statuses),
    ]
    assert len(ids) == len(set(ids))
    assert first.summary["duplicate_observation_id_count"] == 0
    encoded = json.dumps([
        *(item.to_dict() for item in first.faculty_appointments),
        *(item.to_dict() for item in first.administrative_appointments),
        *(item.to_dict() for item in first.employment_statuses),
    ]).casefold()
    assert '"appointment_fte":' not in encoded
    assert '"teaching_fte":' not in encoded
    assert '"denominator_eligibility":' not in encoded


def test_denominator_readiness_remains_blocked_or_unsafe():
    result = FacultyAppointmentObservationService().audit((_directory("d1"),))
    assert set(result.denominator_readiness) == {
        "full_time_faculty", "instructional_faculty", "tenure_line_faculty",
        "faculty_fte", "active_faculty", "current_faculty_by_unit",
    }
    assert all(
        value["status"] in {
            "partially_supported", "blocked_by_missing_evidence", "unsafe_to_infer"
        }
        for value in result.denominator_readiness.values()
    )


def test_cli_writes_compact_reports_and_manifests(tmp_path, capsys):
    source = tmp_path / "normalized"
    source.mkdir()
    values = (_directory("d1"), _schedule("s1"))
    for index, value in enumerate(values):
        (source / f"{index}.json").write_text(json.dumps(value), encoding="utf-8")
    output = tmp_path / "reports"
    assert main([
        "--normalized-root", str(source), "--output-dir", str(output)
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["faculty_appointment_observation_count"] == 1
    assert printed["teaching_assignment_not_appointment_count"] == 1
    for filename in (
        "faculty_appointment_audit.json", "faculty_appointment_audit.md",
        "faculty_appointment_observations.jsonl",
        "administrative_appointment_observations.jsonl",
        "employment_status_observations.jsonl",
        "identity_review_queue.jsonl",
    ):
        assert (output / filename).is_file()
