from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.classification.corpus import (
    CorpusClassificationOptions,
    SemanticCorpusPopulationService,
    discover_knowledge_object_paths,
)
from app.knowledge import KnowledgeObject, load_knowledge_object, save_knowledge_object


FIXED_TIME = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)


def _write_faculty(
    path: Path,
    object_id: str,
    *,
    department: str = "Department of Physics",
    existing_identity=None,
) -> None:
    metadata = {}
    if existing_identity is not None:
        metadata["semantic_identity"] = existing_identity
    payload = {
        "id": object_id,
        "object_type": "faculty_observation",
        "title": "Ada Example",
        "text": "Published faculty profile",
        "metadata": metadata,
        "source": {"relative_path": path.name},
        "observation_id": object_id,
        "display_name": "Ada Example",
        "published_department": department,
        "snapshot_date": "2026-07-21",
        "source_file": path.name,
        "relative_source_path": path.name,
        "raw_acquisition_hash": "abc123",
        "provenance": {"source": "fixture"},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_document(path: Path, object_id: str) -> None:
    save_knowledge_object(
        KnowledgeObject(
            id=object_id,
            object_type="document",
            title="Unsupported document",
            text="Unstructured fixture",
        ),
        path,
    )


def _service() -> SemanticCorpusPopulationService:
    return SemanticCorpusPopulationService(clock=lambda: FIXED_TIME)


def _options(input_root, report_dir, **values):
    return CorpusClassificationOptions(
        input_roots=(input_root,), report_dir=report_dir, **values
    )


def _jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_recursive_discovery_is_sorted_and_deduplicated(tmp_path):
    first = tmp_path / "input" / "b" / "second.json"
    second = tmp_path / "input" / "a" / "first.json"
    _write_document(first, "two")
    _write_document(second, "one")

    discovered = discover_knowledge_object_paths(
        (tmp_path / "input", tmp_path / "input" / "a")
    )

    assert discovered == (second, first)


def test_dry_run_produces_manifest_queues_and_coverage_without_mutation(tmp_path):
    input_root = tmp_path / "input"
    faculty = input_root / "nested" / "faculty.json"
    document = input_root / "document.json"
    _write_faculty(faculty, "faculty-1")
    _write_document(document, "document-1")
    before = faculty.read_bytes()

    report = _service().run(_options(input_root, tmp_path / "reports"))

    assert report.overall.processed == 2
    assert report.overall.classified == 1
    assert report.overall.changed == 1
    assert report.overall.unsupported == 1
    assert faculty.read_bytes() == before
    manifest = _jsonl(tmp_path / "reports" / "classification_manifest.jsonl")
    assert len(manifest) == 2
    faculty_record = next(item for item in manifest if item["knowledge_object_id"] == "faculty-1")
    assert faculty_record["application_mode"] == "dry_run"
    assert faculty_record["applied"] is False
    assert faculty_record["classifier_versions"] == {
        "faculty_observation_classifier": "1"
    }
    assert faculty_record["policy_version"] == "1"
    assert faculty_record["accepted_assertions"]
    assert _jsonl(tmp_path / "reports" / "unsupported_objects.jsonl")[0][
        "knowledge_object_id"
    ] == "document-1"
    assert (tmp_path / "reports" / "review_required.jsonl").exists()
    assert (tmp_path / "reports" / "conflicts.jsonl").exists()
    assert (tmp_path / "reports" / "audit_sample.jsonl").exists()
    summary = json.loads(
        (tmp_path / "reports" / "classification_summary.json").read_text()
    )
    assert summary["field_metrics"]["object_type"]["coverage"] == 1.0
    assert "Semantic Field Coverage" in (
        tmp_path / "reports" / "classification_report.md"
    ).read_text()


def test_apply_is_atomic_safe_and_idempotent(tmp_path):
    input_root = tmp_path / "input"
    faculty = input_root / "faculty.json"
    _write_faculty(faculty, "faculty-1")
    first_report = tmp_path / "first-report"

    first = _service().run(
        _options(input_root, first_report, apply=True)
    )
    loaded = load_knowledge_object(faculty)

    assert first.overall.changed == 1
    assert loaded.id == "faculty-1"
    assert loaded.semantic_identity.object_type == "faculty_observation"
    assert len(loaded.metadata["classification_provenance"]) == 1
    assert not list(input_root.glob(".*.tmp"))
    first_bytes = faculty.read_bytes()

    second = _service().run(
        _options(input_root, tmp_path / "second-report", apply=True)
    )
    assert second.overall.changed == 0
    assert second.overall.unchanged == 1
    assert faculty.read_bytes() == first_bytes
    assert len(load_knowledge_object(faculty).metadata["classification_provenance"]) == 1


def test_conflicted_field_is_not_applied_but_accepted_fields_are(tmp_path):
    input_root = tmp_path / "input"
    faculty = input_root / "faculty.json"
    _write_faculty(
        faculty,
        "faculty-1",
        department="Department of Physics",
        existing_identity={
            "object_type": "faculty_observation",
            "institutional_entities": [
                {
                    "entity_type": "department",
                    "entity_id": "department:english",
                    "published_name": "Department of English",
                }
            ],
        },
    )

    report = _service().run(
        _options(input_root, tmp_path / "reports", apply=True)
    )
    loaded = load_knowledge_object(faculty)
    entities = [item.entity_id for item in loaded.semantic_identity.institutional_entities]

    assert report.overall.conflicted == 1
    assert entities == ["department:english"]
    assert loaded.semantic_identity.temporal_scope.as_of == "2026-07-21"
    conflict = _jsonl(tmp_path / "reports" / "conflicts.jsonl")[0]
    assert conflict["field"] == "institutional_entities"
    assert conflict["policy_decision"] == "conflict"


def test_resume_skips_completed_ids_for_the_same_mode(tmp_path):
    input_root = tmp_path / "input"
    _write_faculty(input_root / "one.json", "faculty-1")
    _write_faculty(input_root / "two.json", "faculty-2")
    report_dir = tmp_path / "reports"

    first = _service().run(
        _options(input_root, report_dir, limit=1)
    )
    second = _service().run(
        _options(input_root, report_dir, resume=True)
    )

    assert first.overall.processed == 1
    assert second.overall.resumed == 1
    assert second.overall.processed == 1
    manifest = _jsonl(report_dir / "classification_manifest.jsonl")
    assert {item["knowledge_object_id"] for item in manifest} == {
        "faculty-1",
        "faculty-2",
    }


def test_manifest_is_reproducible_with_fixed_clock(tmp_path):
    input_root = tmp_path / "input"
    _write_faculty(input_root / "faculty.json", "faculty-1")
    first_dir = tmp_path / "report-one"
    second_dir = tmp_path / "report-two"

    _service().run(_options(input_root, first_dir))
    _service().run(_options(input_root, second_dir))

    assert (first_dir / "classification_manifest.jsonl").read_bytes() == (
        second_dir / "classification_manifest.jsonl"
    ).read_bytes()


def test_object_type_and_id_filters_are_applied_before_limit(tmp_path):
    input_root = tmp_path / "input"
    _write_document(input_root / "a.json", "document-1")
    _write_faculty(input_root / "b.json", "faculty-1")
    _write_faculty(input_root / "c.json", "faculty-2")

    report = _service().run(
        _options(
            input_root,
            tmp_path / "reports",
            object_types=("faculty_observation",),
            knowledge_object_ids=("faculty-2",),
            limit=1,
        )
    )
    assert report.overall.processed == 1
    assert _jsonl(tmp_path / "reports" / "classification_manifest.jsonl")[0][
        "knowledge_object_id"
    ] == "faculty-2"
