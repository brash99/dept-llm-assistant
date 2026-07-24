"""Structural validation for an already-built ISO FAISS vector database."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

REQUIRED_RECORD_FIELDS = (
    "chunk_id",
    "knowledge_object_id",
    "object_type",
    "chunk_index",
    "text",
    "citation",
    "metadata",
)


@dataclass
class VectorDBValidationReport:
    vector_db: str
    valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    index_count: int = 0
    record_count: int = 0
    dimension: int = 0
    index_type: str = ""
    metadata_num_vectors: int | None = None
    metadata_dimension: int | None = None
    metadata_index_type: str | None = None
    sample_size_requested: int = 0
    sampled_records: int = 0
    semantic_spaces: Dict[str, int] = field(default_factory=dict)
    object_types: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _sample_indices(count: int, sample_size: int) -> List[int]:
    if count <= 0 or sample_size <= 0:
        return []
    size = min(count, sample_size)
    if size == 1:
        return [0]
    return sorted({round(index * (count - 1) / (size - 1)) for index in range(size)})


def _usable_citation(citation: Any) -> bool:
    return isinstance(citation, dict) and any(
        citation.get(key)
        for key in ("title", "relative_path", "source_path", "profile_url")
    )


def validate_vector_db(
    vector_db: Path | str,
    *,
    sample_size: int = 1000,
) -> VectorDBValidationReport:
    """Validate global index invariants and a bounded deterministic sample."""
    root = Path(vector_db)
    report = VectorDBValidationReport(
        vector_db=str(root), sample_size_requested=sample_size
    )
    if sample_size < 0:
        report.errors.append("sample_size must be nonnegative")
        return report

    required_files = ("index.faiss", "records.pkl", "metadata.json")
    missing = [name for name in required_files if not (root / name).is_file()]
    if missing:
        report.errors.extend(f"Missing required vector DB file: {name}" for name in missing)
        return report

    try:
        # Import only after artifact checks so missing-snapshot diagnostics do
        # not require FAISS or sentence-transformers to be installed.
        from app.vector_index import load_index

        index, records, metadata = load_index(root)
    except Exception as exc:
        report.errors.append(f"Unable to load vector database: {type(exc).__name__}: {exc}")
        return report

    report.index_count = int(index.ntotal)
    report.dimension = int(index.d)
    report.index_type = type(index).__name__
    if not isinstance(records, list):
        report.errors.append(
            f"records.pkl must contain a list; found {type(records).__name__}"
        )
        records = []
    if not isinstance(metadata, dict):
        report.errors.append(
            f"metadata.json must contain an object; found {type(metadata).__name__}"
        )
        metadata = {}

    report.record_count = len(records)
    report.metadata_num_vectors = metadata.get("num_vectors")
    report.metadata_dimension = metadata.get("dimension")
    report.metadata_index_type = metadata.get("index_type")

    if report.index_count != report.record_count:
        report.errors.append(
            f"FAISS vector count ({report.index_count}) does not equal record count "
            f"({report.record_count})"
        )
    if report.metadata_num_vectors != report.index_count:
        report.errors.append(
            f"metadata num_vectors ({report.metadata_num_vectors!r}) does not equal "
            f"FAISS vector count ({report.index_count})"
        )
    if report.metadata_dimension != report.dimension:
        report.errors.append(
            f"metadata dimension ({report.metadata_dimension!r}) does not equal "
            f"FAISS dimension ({report.dimension})"
        )
    if report.metadata_index_type != report.index_type:
        report.errors.append(
            f"metadata index_type ({report.metadata_index_type!r}) does not match "
            f"loaded index type ({report.index_type})"
        )

    sampled_ids = set()
    for position in _sample_indices(len(records), sample_size):
        record = records[position]
        report.sampled_records += 1
        if not isinstance(record, dict):
            report.errors.append(
                f"Sampled record {position} is {type(record).__name__}, not an object"
            )
            continue
        missing_fields = [field for field in REQUIRED_RECORD_FIELDS if field not in record]
        if missing_fields:
            report.errors.append(
                f"Sampled record {position} is missing fields: {', '.join(missing_fields)}"
            )
        chunk_id = record.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            report.errors.append(f"Sampled record {position} has an empty chunk_id")
        elif chunk_id in sampled_ids:
            report.errors.append(
                f"Sampled chunk_id {chunk_id!r} is duplicated within the validation sample"
            )
        else:
            sampled_ids.add(chunk_id)
        text = record.get("text")
        if not isinstance(text, str) or not text.strip():
            report.errors.append(f"Sampled record {position} has no usable text")
        if not _usable_citation(record.get("citation")):
            report.errors.append(
                f"Sampled record {position} has no usable citation/provenance locator"
            )
        record_metadata = record.get("metadata")
        if not isinstance(record_metadata, dict) or not record_metadata:
            report.errors.append(f"Sampled record {position} has no usable metadata")

    # These global inventories are cheap relative to loading records.pkl and
    # ensure new semantic layers are visible even when not hit by the sample.
    for record in records:
        if not isinstance(record, dict):
            continue
        object_type = str(record.get("object_type") or "<missing>")
        report.object_types[object_type] = report.object_types.get(object_type, 0) + 1
        record_metadata = record.get("metadata") or {}
        semantic_space = str(record_metadata.get("semantic_space") or "<missing>")
        report.semantic_spaces[semantic_space] = (
            report.semantic_spaces.get(semantic_space, 0) + 1
        )

    report.object_types = dict(sorted(report.object_types.items()))
    report.semantic_spaces = dict(sorted(report.semantic_spaces.items()))
    report.valid = not report.errors
    return report


__all__ = ["VectorDBValidationReport", "validate_vector_db"]
