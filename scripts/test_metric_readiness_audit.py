import json

from app.metric_readiness_audit import (
    MetricReadinessAuditService,
    load_normalized_objects,
)
from scripts.audit_metric_readiness import main


def _schedule(identifier="s1", **overrides):
    value = {
        "id": identifier,
        "object_type": "course_offering_observation",
        "academic_term": "2022_fall",
        "subject": "CPSC",
        "credits": 3.0,
        "enrollment": 20,
        "status": "Active",
        "instructor_raw": "Doe, Jane",
        "instructor_type": {"normalized_value": "full_time", "conflicting": False},
        "provenance": {"source": "fixture"},
    }
    value.update(overrides)
    return value


def test_audit_is_deterministic_and_does_not_compute_sch():
    values = (
        _schedule(),
        {
            "id": "f1", "object_type": "faculty_observation",
            "display_name": "Jane Doe", "published_department": "SEC",
            "snapshot_date": "2026-07-21", "provenance": {"source": "fixture"},
        },
    )
    service = MetricReadinessAuditService()
    first = service.audit(values, normalized_root="storage/normalized")
    second = service.audit(reversed(values), normalized_root="storage/normalized")
    assert first.deterministic_fingerprint == second.deterministic_fingerprint
    assert first.sch_readiness["readiness_status"] == "partially_implemented_not_metric_ready"
    assert "student_credit_hours" not in first.sch_readiness
    assert first.sch_readiness["input_coverage_counts"]["credits_and_enrollment_present"] == 1
    assert first.sch_readiness["input_coverage_counts"]["sch_inputs_and_workforce_unit_mapped"] == 1


def test_unit_audit_reports_governed_references_unknown_ids_and_unresolved_labels():
    value = {
        "id": "f1", "object_type": "faculty_observation",
        "published_department": "Unregistered Example Unit",
        "metadata": {"semantic_identity": {
            "institutional_entities": [{
                "entity_type": "academic_unit",
                "entity_id": "academic_unit:not_governed",
            }],
        }},
    }
    result = MetricReadinessAuditService().audit((value,)).institutional_units
    assert "academic_unit:not_governed" in result["referenced_but_not_governed"]
    assert {
        item["published_label"]: item["observation_count"]
        for item in result["unresolved_published_unit_labels"]
    }["Unregistered Example Unit"] == 1
    sec = next(
        unit for unit in result["governed_academic_units"]
        if unit["unit_id"] == "academic_unit:sec"
    )
    assert sec["formal_unit_type"] == "dependent_school"
    assert "department_equivalent" in sec["operational_roles"]
    assert result["temporal_model_limitations"]


def test_faculty_capability_matrix_does_not_promote_section_type_to_employment():
    result = MetricReadinessAuditService().audit((_schedule(),)).faculty_observation
    schedule = result["evidence_sources"]["institutional_schedule"]["capabilities"]
    assert schedule["employment_category"] == "missing_section_scoped_instructor_type_is_not_employment"
    assert schedule["appointment_fte"] == "missing"
    assert schedule["teaching_assignment"] == "implemented_section_and_term_scoped"


def test_sch_special_cases_and_denominators_remain_explicitly_blocked():
    report = MetricReadinessAuditService().audit((_schedule(),))
    special = report.sch_readiness["special_case_readiness"]
    assert special["cross_listed_courses"].startswith("missing_")
    assert special["team_taught_sections"].startswith("missing_")
    assert report.denominator_readiness["sch_per_full_time_faculty"]["status"].startswith("blocked_")
    assert report.denominator_readiness["sch_per_teaching_fte"]["status"].startswith("blocked_")
    assert report.denominator_readiness["sch_per_active_instructor"]["status"].startswith("partially_")


def test_loader_and_cli_write_compact_deterministic_reports(tmp_path, capsys):
    root = tmp_path / "normalized"
    root.mkdir()
    (root / "schedule.json").write_text(json.dumps(_schedule()), encoding="utf-8")
    objects, integrity = load_normalized_objects(root)
    assert len(objects) == 1
    assert integrity["invalid_json_count"] == 0
    output = tmp_path / "reports"
    assert main(["--normalized-root", str(root), "--output-dir", str(output)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["normalized_objects"] == 1
    assert (output / "metric_readiness_audit.json").is_file()
    assert (output / "metric_readiness_audit.md").is_file()
    first = json.loads((output / "metric_readiness_audit.json").read_text())
    assert main(["--normalized-root", str(root), "--output-dir", str(output)]) == 0
    capsys.readouterr()
    second = json.loads((output / "metric_readiness_audit.json").read_text())
    assert first["audit"]["deterministic_fingerprint"] == second["audit"]["deterministic_fingerprint"]


def test_invalid_json_fails_without_dumping_file_inventory(tmp_path, capsys):
    root = tmp_path / "normalized"
    root.mkdir()
    (root / "bad.json").write_text("{", encoding="utf-8")
    assert main(["--normalized-root", str(root)]) == 2
    output = json.loads(capsys.readouterr().out)
    assert output == {"error": "invalid_normalized_json", "invalid_json_count": 1}
