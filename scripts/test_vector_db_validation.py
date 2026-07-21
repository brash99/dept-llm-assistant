import json
from pathlib import Path
import pickle

import numpy as np
import pytest

faiss = pytest.importorskip("faiss", reason="FAISS is required for vector DB tests")

from app.vector_db_validation import validate_vector_db


def _record(index, **overrides):
    value = {
        "chunk_id": f"chunk-{index}",
        "knowledge_object_id": f"object-{index}",
        "object_type": "document",
        "chunk_index": 0,
        "text": f"Evidence text {index}",
        "citation": {"title": f"Source {index}", "relative_path": f"source/{index}.pdf"},
        "metadata": {"semantic_space": "institutional_evidence"},
    }
    value.update(overrides)
    return value


def _write_vector_db(path: Path, *, vectors=3, records=None, metadata=None):
    path.mkdir()
    index = faiss.IndexFlatIP(4)
    index.add(np.eye(vectors, 4, dtype="float32"))
    faiss.write_index(index, str(path / "index.faiss"))
    records = records if records is not None else [_record(i) for i in range(vectors)]
    with (path / "records.pkl").open("wb") as handle:
        pickle.dump(records, handle)
    metadata = metadata if metadata is not None else {
        "num_vectors": vectors,
        "dimension": 4,
        "index_type": "IndexFlatIP",
    }
    (path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")


def test_valid_structural_report(tmp_path):
    root = tmp_path / "vector_db"
    _write_vector_db(root)
    report = validate_vector_db(root, sample_size=3)
    assert report.valid, report.errors
    assert report.index_count == report.record_count == 3
    assert report.dimension == 4
    assert report.object_types == {"document": 3}
    assert report.semantic_spaces == {"institutional_evidence": 3}


def test_vector_record_count_mismatch_is_actionable(tmp_path):
    root = tmp_path / "vector_db"
    _write_vector_db(root, records=[_record(0), _record(1)])
    report = validate_vector_db(root)
    assert not report.valid
    assert any("does not equal record count" in error for error in report.errors)


def test_missing_files_are_reported_without_loading(tmp_path):
    report = validate_vector_db(tmp_path / "missing")
    assert not report.valid
    assert len(report.errors) == 3
    assert all("Missing required vector DB file" in error for error in report.errors)


def test_malformed_metadata_is_reported(tmp_path):
    root = tmp_path / "vector_db"
    _write_vector_db(root, metadata=["not", "an", "object"])
    report = validate_vector_db(root)
    assert not report.valid
    assert any("metadata.json must contain an object" in error for error in report.errors)
    assert any("metadata dimension" in error for error in report.errors)


REAL_VECTOR_DB = Path("storage/vector_db")


@pytest.mark.skipif(
    not all((REAL_VECTOR_DB / name).is_file() for name in ("index.faiss", "records.pkl", "metadata.json")),
    reason="real vector database artifacts are not available in this checkout",
)
def test_real_vector_db_structural_integration():
    report = validate_vector_db(REAL_VECTOR_DB, sample_size=100)
    assert report.valid, "\n".join(report.errors)
