from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import pickle

import numpy as np
import pytest

faiss = pytest.importorskip("faiss", reason="FAISS is required for pipeline tests")

from app.classification.corpus import atomic_save_knowledge_object
from app.knowledge import KnowledgeObject
from app.semantic_pipeline import (
    ArtifactState, BuildHooks, INCOMPLETE_NAME, MANIFEST_NAME,
    SemanticPipelineService, verify_pipeline,
)
from scripts.semantic_pipeline import main


FAMILIES = (
    ("cnu_institutional_research", "institutional_operating_record"),
    ("curated_external_evidence", "external_reference"),
    ("schev_publications", "external_state_context"),
    ("sec_google_drive", "academic_unit_reporting_record"),
    ("sec_google_drive", "academic_unit_planning_material"),
    ("sec_google_drive", "academic_program_review_evidence"),
    ("sec_google_drive", "academic_unit_operating_record"),
)


def _config(root: Path) -> Path:
    path = root / "config" / "settings.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"""project:\n  root: {root}\nstorage:\n  normalized: normalized\n  constitutional: constitutional\n  schedule_observations: schedules\n  faculty_observations: faculty\n  catalog_observations: catalogs\n  chunks: derived/chunks\n  embeddings: derived/embeddings\n  vector_db: derived/vector_db\nembedding:\n  model: fixture-model\n  batch_size: 4\n  device: cpu\nchunking:\n  chunk_size: 200\n  overlap: 20\n  max_chunks_per_document: null\n""",
        encoding="utf-8",
    )
    return path


def _objects(root: Path):
    normalized = root / "normalized"
    normalized.mkdir(parents=True)
    for name in ("constitutional", "schedules", "faculty", "catalogs"):
        (root / name).mkdir(parents=True, exist_ok=True)
    for index, (family, role) in enumerate(FAMILIES):
        identity = {
            "object_type": "document", "source_family": family,
            "institutional_role": role, "document_type": f"fixture_type_{index}",
        }
        if index % 2 == 0:
            identity["authority"] = {
                "issuing_authority": f"Fixture Authority {index}",
                "authority_class": "fixture_authority",
            }
        obj = KnowledgeObject(
            id=f"object-{index}", object_type="document", title=f"Fixture {index}",
            text=f"Published factual fixture evidence {index}.",
            metadata={"semantic_identity": identity},
            source={"relative_path": f"fixture/{index}.txt"},
        )
        atomic_save_knowledge_object(obj, normalized / f"object-{index}.json")


def _fake_embed(**kwargs):
    chunks_dir = Path(kwargs["chunks_dir"]); output = Path(kwargs["embeddings_dir"])
    output.mkdir(parents=True, exist_ok=True); total = 0
    for path in sorted(chunks_dir.glob("*.json")):
        chunks = json.loads(path.read_text())
        values = []
        for chunk in chunks:
            vector = [1.0, 0.0, 0.0, 0.0]
            values.append({
                "chunk_id": chunk["id"], "knowledge_object_id": chunk["knowledge_object_id"],
                "object_type": chunk["object_type"], "chunk_index": chunk["chunk_index"],
                "text": chunk["text"], "citation": chunk["citation"], "metadata": chunk["metadata"],
                "embedding": vector,
                "embedding_metadata": {
                    "model": kwargs["model_name"], "device": kwargs["device"],
                    "normalized": True, "embedding_context": kwargs["embedding_context"],
                    "created_at": "2026-07-21T12:00:00+00:00",
                },
            }); total += 1
        (output / path.name).write_text(json.dumps(values), encoding="utf-8")
    return {
        "model": kwargs["model_name"], "device": kwargs["device"],
        "embedding_dimension": 4, "total_chunks": total,
        "attempted_files": total, "succeeded_files": total, "failed_files": 0,
        "errors": [],
    }


def _fake_index(**kwargs):
    embeddings = Path(kwargs["embeddings_dir"]); output = Path(kwargs["vector_db_dir"])
    output.mkdir(parents=True, exist_ok=True); records = []; vectors = []
    for path in sorted(embeddings.glob("*.json")):
        for item in json.loads(path.read_text()):
            vectors.append(item["embedding"])
            records.append({key: item[key] for key in (
                "chunk_id", "knowledge_object_id", "object_type", "chunk_index",
                "text", "citation", "metadata", "embedding_metadata",
            )})
    matrix = np.asarray(vectors, dtype="float32")
    index = faiss.IndexFlatIP(matrix.shape[1]); index.add(matrix)
    faiss.write_index(index, str(output / "index.faiss"))
    with (output / "records.pkl").open("wb") as handle: pickle.dump(records, handle)
    metadata = {
        "num_vectors": len(records), "dimension": int(matrix.shape[1]),
        "index_type": "IndexFlatIP", "distance": "cosine_similarity_via_inner_product",
    }
    (output / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return metadata


def _service(root, *, hooks=None, run_id="run-1"):
    config = _config(root)
    _objects(root)
    if hooks is None:
        from app.chunk import run_chunking
        hooks = BuildHooks(run_chunking, _fake_embed, _fake_index)
    return SemanticPipelineService(
        config, hooks=hooks, dependency_checker=lambda name: True,
        clock=lambda: datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc),
        run_id_factory=lambda: run_id,
    )


def _build(root, **kwargs):
    service = _service(root, **kwargs)
    result = service.rebuild()
    return service, result


def test_status_missing_artifacts_and_portable_config_root(tmp_path):
    service = _service(tmp_path)
    report = service.status()
    assert report.paths.repository_root == tmp_path
    assert report.normalized.state == ArtifactState.CURRENT
    assert report.chunks.state == ArtifactState.MISSING
    assert report.embeddings.state == ArtifactState.MISSING
    assert report.vector_index.state == ArtifactState.MISSING


def test_dry_run_is_mutation_free_and_reports_preflight(tmp_path):
    service = _service(tmp_path)
    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    report = service.rebuild(dry_run=True)
    after = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    assert before == after
    assert report["mutations_performed"] is False
    assert report["normalized_object_count"] == 7
    assert report["embedding_model"] == "fixture-model"
    assert report["planned_stages"] == ["chunks", "embeddings", "vector_index", "verification"]


def test_successful_staging_promotion_backup_manifest_and_status(tmp_path):
    for name in ("chunks", "embeddings", "vector_db"):
        path = tmp_path / "derived" / name; path.mkdir(parents=True)
        (path / "old-marker").write_text("old", encoding="utf-8")
    service, result = _build(tmp_path)
    assert Path(result["manifest"]).is_file()
    for backup in result["backup_paths"].values():
        assert (Path(backup) / "old-marker").read_text() == "old"
    manifest = json.loads(Path(result["manifest"]).read_text())
    assert manifest["normalized_object_count"] == 7
    assert manifest["chunk_count"] == manifest["embedding_count"] == 7
    assert manifest["embedding_model"] == "fixture-model"
    assert manifest["validation"]["valid"] is True
    assert all(value["valid"] for value in manifest["semantic_metadata_coverage"]["families"].values())
    status = service.status()
    assert status.chunks.state == ArtifactState.CURRENT
    assert status.embeddings.state == ArtifactState.CURRENT
    assert status.vector_index.state == ArtifactState.CURRENT


def test_verify_checks_counts_vectors_and_semantic_identity(tmp_path):
    service, _ = _build(tmp_path)
    report = service.verify()
    assert report.valid, report.errors
    assert report.chunk_count == report.embedding_count == report.vector_count == 7
    assert report.metadata_record_count == 7
    assert report.vector_smoke_queries == 3
    assert report.semantic_chunk_coverage["source_family"] == 7
    assert report.semantic_index_coverage["institutional_role"] == 7
    assert len(report.family_checks) == 7


def test_status_detects_inconsistent_vector_metadata(tmp_path):
    service, _ = _build(tmp_path)
    metadata_path = tmp_path / "derived/vector_db/metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["num_vectors"] = 999
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    status = service.status()
    assert status.vector_index.state == ArtifactState.INCONSISTENT
    assert any("num_vectors" in reason for reason in status.vector_index.reasons)


def test_status_detects_chunk_semantic_metadata_drift(tmp_path):
    service, _ = _build(tmp_path)
    chunk_path = next((tmp_path / "derived/chunks").glob("*.json"))
    chunks = json.loads(chunk_path.read_text())
    chunks[0]["metadata"]["semantic_identity"]["source_family"] = "tampered"
    chunk_path.write_text(json.dumps(chunks), encoding="utf-8")
    status = service.status()
    assert status.chunks.state == ArtifactState.INCONSISTENT
    assert status.embeddings.state == ArtifactState.STALE


@pytest.mark.parametrize("failed_stage", ("chunk", "embed", "index"))
def test_stage_failure_never_replaces_production(tmp_path, failed_stage):
    from app.chunk import run_chunking
    production = {}
    for name in ("chunks", "embeddings", "vector_db"):
        path = tmp_path / "derived" / name; path.mkdir(parents=True)
        marker = path / "known-good"; marker.write_text(name, encoding="utf-8")
        production[name] = marker

    def bad_chunk(**kwargs): return {"failed": 1, "total_chunks": 0, "errors": ["fixture"]}
    def bad_embed(**kwargs): return {"failed_files": 1, "total_chunks": 0, "errors": ["fixture"]}
    def bad_index(**kwargs): raise RuntimeError("fixture index failure")
    hooks = BuildHooks(
        bad_chunk if failed_stage == "chunk" else run_chunking,
        bad_embed if failed_stage == "embed" else _fake_embed,
        bad_index if failed_stage == "index" else _fake_index,
    )
    service = _service(tmp_path, hooks=hooks)
    with pytest.raises(RuntimeError): service.rebuild()
    assert all(path.read_text() == name for name, path in production.items())
    assert service.status().incomplete_staging_runs == ("run-1",)


def test_incomplete_staging_requires_explicit_cleanup(tmp_path):
    service = _service(tmp_path)
    incomplete = service.paths.staging_root / "old-run"
    incomplete.mkdir(parents=True); (incomplete / INCOMPLETE_NAME).write_text("{}")
    with pytest.raises(RuntimeError, match="Incomplete staging runs"):
        service.rebuild()
    service.run_id_factory = lambda: "new-run"
    result = service.rebuild(cleanup_staging=True)
    assert result["run_id"] == "new-run"
    assert not incomplete.exists()


def test_stale_status_when_normalized_dependency_changes(tmp_path):
    service, _ = _build(tmp_path)
    extra = KnowledgeObject("extra", "document", "Extra", "Extra fact")
    atomic_save_knowledge_object(extra, tmp_path / "normalized" / "extra.json")
    status = service.status()
    assert status.chunks.state == ArtifactState.STALE
    assert status.embeddings.state == ArtifactState.STALE
    assert status.vector_index.state == ArtifactState.STALE


def test_verify_detects_count_mismatch_and_nan(tmp_path):
    service, _ = _build(tmp_path)
    embedding_file = next(service.paths.embeddings.glob("*.json"))
    values = json.loads(embedding_file.read_text()); values[0]["embedding"][0] = float("nan")
    embedding_file.write_text(json.dumps(values), encoding="utf-8")
    report = service.verify()
    assert not report.valid
    assert any("NaN" in error for error in report.errors)

    values.pop(); embedding_file.write_text(json.dumps(values), encoding="utf-8")
    report = service.verify()
    assert not report.valid
    assert any("ID sets differ" in error or "vector count" in error for error in report.errors)


def test_manifest_dependency_fields_are_deterministic(tmp_path):
    first, first_result = _build(tmp_path, run_id="first")
    first_manifest = json.loads(Path(first_result["manifest"]).read_text())
    first.run_id_factory = lambda: "second"
    second_result = first.rebuild()
    second_manifest = json.loads(Path(second_result["manifest"]).read_text())
    stable = (
        "normalized_object_count", "normalized_fingerprint", "chunk_count",
        "chunk_fingerprint", "embedding_count", "embedding_fingerprint",
        "embedding_model", "embedding_dimension", "embedding_context",
        "faiss_vector_count", "metadata_record_count", "index_record_fingerprint",
    )
    assert {key: first_manifest[key] for key in stable} == {key: second_manifest[key] for key in stable}


def test_cli_exit_codes_for_status_and_bad_config(tmp_path, capsys):
    service = _service(tmp_path)
    assert main(["--config", str(tmp_path / "config/settings.yaml"), "status", "--json"]) == 0
    assert '"normalized"' in capsys.readouterr().out
    assert main(["--config", str(tmp_path / "missing.yaml"), "status"]) == 2
