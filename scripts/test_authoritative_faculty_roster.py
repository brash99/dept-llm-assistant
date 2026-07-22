from __future__ import annotations

import json
from pathlib import Path

from app.adapters.faculty_roster_adapter import FacultyRosterCSVAdapter
from app.authoritative_faculty_roster import FacultyRosterSchema, denominator_readiness
from scripts.audit_faculty_roster_readiness import audit
from scripts.ingest_faculty_roster import main as ingest_main


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "scripts/fixtures/authoritative_faculty_roster.csv"
SCHEMA = ROOT / "config/faculty_roster_schema.yaml"


def _directory(identifier, person_id, name, email):
    return {
        "id": identifier,
        "object_type": "faculty_observation",
        "person_id": person_id,
        "display_name": name,
        "email": email,
        "snapshot_date": "2026-07-21",
        "provenance": {"source": "synthetic-directory"},
    }


def _identity_objects():
    return (
        _directory("patricia", "P001", "Patricia Siewe Seuchie", "patricia@example.edu"),
        _directory("james", "P002", "James P. Kelly", "james@example.edu"),
        _directory("shinhye", "P003", "Shinhye Kim", "shinhye@example.edu"),
        _directory("jessica", "PX99", "Jessica Kelly", "jessica@example.edu"),
    )


def _adapt():
    return FacultyRosterCSVAdapter(
        FIXTURE, FacultyRosterSchema.load(SCHEMA),
        identity_objects=_identity_objects(),
    ).adapt()


def test_schema_contract_loads_aliases_and_is_deterministic():
    first = FacultyRosterSchema.load(SCHEMA)
    second = FacultyRosterSchema.load(SCHEMA)
    assert first.deterministic_fingerprint == second.deterministic_fingerprint
    assert "institutional_person_identifier" in first.required_fields
    assert set(first.temporal_alternatives) == {"effective_date", "snapshot_date"}
    assert "person_id" in first.column_aliases["institutional_person_identifier"]


def test_fixture_classification_duplicate_and_fte_validation():
    result = _adapt()
    assert result.summary["source_row_count"] == 13
    assert result.summary["accepted_observation_count"] == 9
    assert result.summary["quarantined_row_count"] == 3
    assert result.summary["rejected_row_count"] == 1
    assert result.summary["duplicate_source_record_id_count"] == 1
    assert result.summary["duplicate_position_count"] == 1
    assert result.summary["identity_conflict_count"] == 1
    by_record = {row.source_record_id: row for row in result.rows if row.source_record_id}
    assert by_record["R009"].classification == "quarantined"
    assert "invalid_fte:appointment_fte" in by_record["R009"].reasons
    duplicate = [row for row in result.rows if "duplicate_source_record_id" in row.reasons]
    assert len(duplicate) == 1 and duplicate[0].classification == "rejected"


def test_identifier_email_name_alias_precedence_and_conflicts():
    result = _adapt()
    observations = {item.source_record_id: item for item in result.observations}
    patricia = observations["R001"]
    assert patricia.faculty_identity_id == "faculty_identity:patricia_siewe_seuchie"
    assert patricia.identity_link_method == "institutional_identifier"
    assert "identifier_link" in patricia.evidence_fitness
    assert observations["R002"].faculty_identity_id == "faculty_identity:james_p_kelly"
    assert observations["R004"].faculty_identity_id == "faculty_identity:shinhye_kim"
    conflict = next(row for row in result.rows if row.source_record_id == "R010")
    assert conflict.classification == "quarantined"
    assert any(reason.startswith("identity_conflict:") for reason in conflict.reasons)
    assert conflict.observation is None


def test_explicit_facts_are_preserved_without_population_inference():
    observations = {item.source_record_id: item for item in _adapt().observations}
    primary = observations["R002"]
    secondary = observations["R003"]
    assert primary.primary_secondary == "Primary"
    assert secondary.primary_secondary == "Secondary"
    assert primary.appointment_fte == "1.0"
    assert secondary.appointment_fte == "0.25"
    assert observations["R005"].administrative_fte == "1.0"
    assert observations["R006"].employment_status == "Emerita"
    assert observations["R007"].effective_date == "2027-01-10"
    assert observations["R008"].effective_end_date == "2024-05-31"
    assert all("explicit_faculty_home" not in item.evidence_fitness for item in observations.values())
    encoded = json.dumps([item.to_dict() for item in observations.values()]).casefold()
    for forbidden in ("active_employment", "denominator_eligible", "inferred_tenure", "inferred_faculty_home"):
        assert forbidden not in encoded


def test_unresolved_unit_is_limited_not_silently_repaired():
    row = next(row for row in _adapt().rows if row.source_record_id == "R011")
    assert row.classification == "accepted_with_limitations"
    assert row.observation.academic_unit_id is None
    assert row.observation.appointment_academic_unit == "Unresolved Synthetic Unit"
    assert "academic_unit_unresolved" in row.reasons


def test_invalid_date_rejected_and_no_fuzzy_identity_matching(tmp_path):
    source = tmp_path / "roster.csv"
    source.write_text(
        "person_id,employee_name,effective_date,employee_status,appointment_type,department,source_authority,record_id\n"
        "P900,Patricia Siewe Seuchi,07/01/2026,Full Time,Faculty,Department of History,HR,BAD1\n",
        encoding="utf-8",
    )
    result = FacultyRosterCSVAdapter(
        source, FacultyRosterSchema.load(SCHEMA), identity_objects=_identity_objects()
    ).adapt()
    assert result.rows[0].classification == "rejected"
    assert "invalid_date:effective_date" in result.rows[0].reasons
    assert result.rows[0].observation is None


def test_ingestion_outputs_are_byte_identical(tmp_path):
    identity_root = tmp_path / "identities"
    identity_root.mkdir()
    for index, value in enumerate(_identity_objects()):
        (identity_root / f"{index}.json").write_text(json.dumps(value), encoding="utf-8")
    outputs = [tmp_path / "one", tmp_path / "two"]
    for output in outputs:
        assert ingest_main([
            "--input", str(FIXTURE), "--schema", str(SCHEMA),
            "--identity-root", str(identity_root), "--output-dir", str(output),
        ]) == 0
    for filename in (
        "faculty_roster_ingestion.json", "faculty_roster_ingestion.md",
        "faculty_roster_observations.jsonl", "faculty_roster_row_manifest.jsonl",
    ):
        assert (outputs[0] / filename).read_bytes() == (outputs[1] / filename).read_bytes()


def test_dry_run_writes_nothing(tmp_path):
    output = tmp_path / "dry"
    identity_root = tmp_path / "empty"
    identity_root.mkdir()
    assert ingest_main([
        "--input", str(FIXTURE), "--schema", str(SCHEMA),
        "--identity-root", str(identity_root), "--output-dir", str(output), "--dry-run",
    ]) == 0
    assert not output.exists()


def test_readiness_without_roster_is_explicitly_blocked():
    payload = audit(None)
    assert payload["authoritative_roster_present"] is False
    assert payload["production_denominator_ready"] is False
    assert all(
        item["status"] == "blocked_by_missing_evidence"
        for item in payload["denominator_readiness"].values()
    )
    fixture_readiness = denominator_readiness(_adapt().summary)
    assert fixture_readiness["active_faculty"]["status"] == "unsafe_to_infer"
