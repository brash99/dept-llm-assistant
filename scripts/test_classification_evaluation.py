from __future__ import annotations

from pathlib import Path

from app.classification.evaluation import (
    ClassificationEvaluationService,
    EvaluationCase,
    ExpectedAssertion,
    QualityGates,
    load_evaluation_cases,
)
from app.classification.policy import AuditPolicy


CASES = Path("config/classification_evaluation_cases.yaml")


def test_evaluation_dataset_loads_all_supported_families_and_ambiguity():
    cases = load_evaluation_cases(CASES)
    object_types = {case.fixture["object_type"] for case in cases}
    assert len(cases) == 8
    assert {
        "constitutional_knowledge",
        "faculty_observation",
        "course_offering_observation",
        "catalog_observation",
        "academic_unit_observation",
        "department_faculty_roster_observation",
        "document",
    } <= object_types


def test_evaluation_metrics_and_initial_quality_gates_pass():
    report = ClassificationEvaluationService(
        audit_policy=AuditPolicy(seed="test-seed")
    ).evaluate(load_evaluation_cases(CASES))

    assert report.passed is True
    assert report.metrics.number_of_cases == 8
    assert report.metrics.exact.precision == 1.0
    assert report.metrics.exact.recall == 1.0
    assert report.metrics.false_positive_count == 0
    assert report.metrics.forbidden_assertion_count == 0
    assert report.metrics.number_of_abstentions == 1
    assert report.metrics.conflict_assertions == 1
    assert "object_type" in report.metrics.by_field
    assert "adapter" in report.metrics.by_method
    assert "faculty_observation" in report.metrics.by_object_type
    assert report.audit_selection["selected_keys"]
    assert report.to_dict()["passed"] is True
    assert "Exact precision: 1.000" in report.to_text(verbose=True)


def test_quality_gate_failure_is_reported_without_opaque_score():
    case = EvaluationCase(
        case_id="deliberately_incomplete_expectation",
        fixture={
            "object_type": "faculty_observation",
            "display_name": "Ada Example",
            "snapshot_date": "2026-07-21",
        },
        expected_assertions=(
            ExpectedAssertion("object_type", "faculty_observation"),
        ),
    )
    report = ClassificationEvaluationService().evaluate(
        (case,),
        quality_gates=QualityGates(minimum_precision=1.0),
    )
    assert report.passed is False
    assert report.metrics.false_positive_count == 2
    assert any("Precision" in failure for failure in report.quality_gate_failures)
    assert report.cases[0].false_positives


def test_loader_rejects_duplicate_case_ids(tmp_path):
    path = tmp_path / "cases.yaml"
    path.write_text(
        "cases:\n"
        "  - case_id: duplicate\n"
        "    fixture: {object_type: document}\n"
        "  - case_id: duplicate\n"
        "    fixture: {object_type: document}\n",
        encoding="utf-8",
    )
    try:
        load_evaluation_cases(path)
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("Duplicate evaluation case IDs must fail")
