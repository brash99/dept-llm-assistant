from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Iterable, Optional
import hashlib
import json
from collections import Counter

from app.knowledge import load_knowledge_object


CONSTITUTIONAL_METADATA_FIELDS = (
    "constitutional_type",
    "principles",
    "institutional_scope",
    "effective_from",
    "effective_until",
    "source_knowledge_object_id",
)

EXTERNAL_PROVENANCE_FIELDS = (
    "external_provenance",
    "issuing_authority",
    "authority_class",
    "evidence_role",
    "decision_types",
    "evidence_domains",
    "canonical_url",
    "geographic_scope",
)

SCHEDULE_OBJECT_TYPE = "course_offering_observation"
SCHEDULE_SEMANTIC_SPACE = "institutional_operations"


@dataclass
class Chunk:
    id: str
    knowledge_object_id: str
    object_type: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    citation: Dict[str, Any]
    metadata: Dict[str, Any]


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def make_chunk_id(knowledge_object_id, chunk_index, start_char, end_char):
    base = f"{knowledge_object_id}:{chunk_index}:{start_char}:{end_char}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def chunk_text(text, chunk_size=3000, overlap=300):
    chunks = []

    if not text.strip():
        return chunks

    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append((chunk, start, end))

        if end == text_len:
            break

        start = end - overlap

    return chunks


def _mapping_value(mapping, key, default=None):
    if isinstance(mapping, dict):
        return mapping.get(key, default)
    return default


def _document_field(document, field, default=None):
    """
    Resolve a field across ordinary and constitutional Knowledge Objects.

    Ordinary objects expose several source fields directly. Constitutional
    objects preserve them primarily in their source and metadata mappings.
    """
    value = getattr(document, field, None)
    if value is not None:
        return value

    source = getattr(document, "source", {}) or {}
    value = _mapping_value(source, field)
    if value is not None:
        return value

    metadata = getattr(document, "metadata", {}) or {}
    value = _mapping_value(metadata, field)
    if value is not None:
        return value

    return default


def _document_metadata(document) -> Dict[str, Any]:
    """
    Return source-object metadata that should survive chunking.

    KnowledgeObject implementations may expose fields as attributes or inside
    source/metadata mappings. We support both forms.
    """
    source_metadata = getattr(document, "metadata", {}) or {}

    metadata = {
        "document_title": document.title,
        "relative_path": _document_field(document, "relative_path"),
        "parser": _document_field(document, "parser"),
        "file_type": _document_field(document, "file_type"),
    }

    for field in CONSTITUTIONAL_METADATA_FIELDS:
        value = getattr(document, field, None)

        if value is None:
            value = source_metadata.get(field)

        if value is not None:
            metadata[field] = value

    for field in EXTERNAL_PROVENANCE_FIELDS:
        value = source_metadata.get(field)
        if value is not None:
            metadata[field] = value

    semantic_space = source_metadata.get("semantic_space")
    if semantic_space is not None:
        metadata["semantic_space"] = semantic_space

    constitutional_notes = source_metadata.get("constitutional_notes")
    if constitutional_notes is not None:
        metadata["constitutional_notes"] = constitutional_notes

    return metadata


def _present(value) -> bool:
    return value is not None and value != ""


def _schedule_value(observation, field, default=None):
    value = getattr(observation, field, None)
    return value if _present(value) else default


def render_course_offering_observation(observation) -> str:
    """Render one schedule observation as concise factual retrieval text."""
    term = _schedule_value(observation, "academic_term")
    course_code = _schedule_value(observation, "course_code")
    title = _schedule_value(observation, "course_title")

    heading = "Scheduled course offering"
    if term:
        heading += f" for {term}"
    lines = [f"{heading}."]

    if course_code:
        course = course_code
        if title:
            course += f" — {title}"
        lines.append(f"Course: {course}.")

    credits = _schedule_value(
        observation,
        "credits_raw",
        _schedule_value(observation, "credits"),
    )
    for label, value in (
        ("Section", _schedule_value(observation, "section")),
        ("CRN", _schedule_value(observation, "crn")),
        ("Credits", credits),
        ("Instructor", _schedule_value(observation, "instructor_raw")),
        (
            "Instructional method",
            _schedule_value(observation, "instructional_method"),
        ),
        ("Modality", _schedule_value(observation, "modality")),
        ("Meeting days", _schedule_value(observation, "meeting_days")),
        ("Meeting time", _schedule_value(observation, "meeting_time_raw")),
        (
            "Meeting date range",
            _schedule_value(observation, "meeting_date_range_raw"),
        ),
        ("Start date", _schedule_value(observation, "start_date")),
        ("End date", _schedule_value(observation, "end_date")),
        ("Location", _schedule_value(observation, "location_raw")),
        ("Campus", _schedule_value(observation, "campus")),
        ("Enrollment", _schedule_value(observation, "enrollment")),
        ("Capacity", _schedule_value(observation, "capacity")),
        (
            "Seats available",
            _schedule_value(observation, "seats_available"),
        ),
        ("Waitlist", _schedule_value(observation, "waitlist")),
        ("Status", _schedule_value(observation, "status")),
        (
            "Liberal Learning Core designation",
            _schedule_value(observation, "llc_area_raw"),
        ),
        ("Notes", _schedule_value(observation, "notes")),
    ):
        if _present(value):
            lines.append(f"{label}: {value}.")

    return "\n".join(lines)


def _schedule_metadata(observation) -> Dict[str, Any]:
    source = getattr(observation, "source", {}) or {}
    provenance = getattr(observation, "provenance", {}) or {}
    source_path = (
        _mapping_value(provenance, "source_path")
        or _mapping_value(source, "path")
    )
    source_type = _mapping_value(source, "kind")

    values = {
        "document_title": observation.title,
        "knowledge_object_id": observation.id,
        "knowledge_object_type": observation.object_type,
        "semantic_space": SCHEDULE_SEMANTIC_SPACE,
        "term": _schedule_value(observation, "academic_term"),
        "subject": _schedule_value(observation, "subject"),
        "course_number": _schedule_value(observation, "course_number"),
        "course_code": _schedule_value(observation, "course_code"),
        "section": _schedule_value(observation, "section"),
        "crn": _schedule_value(observation, "crn"),
        "instructor_text": _schedule_value(observation, "instructor_raw"),
        "source_type": source_type,
        "source_path": source_path,
        "relative_path": source_path,
        "source_row": _schedule_value(observation, "source_row"),
        "source_sha256": _mapping_value(provenance, "source_sha256"),
        "adapter": _mapping_value(provenance, "adapter"),
        "adapter_version": _mapping_value(provenance, "adapter_version"),
        "normalized_at": getattr(observation, "normalized_at", None),
    }
    return {key: value for key, value in values.items() if _present(value)}


def chunk_course_offering_observation(observation):
    """Produce exactly one deterministic primary chunk for one section."""
    text = render_course_offering_observation(observation)
    metadata = {
        **_schedule_metadata(observation),
        "chunk_size": None,
        "overlap": 0,
        "max_chunks_per_document": 1,
        "document_truncated": False,
        "original_chunk_count": 1,
        "indexed_chunk_count": 1,
    }
    source_path = metadata.get("source_path")
    citation = {
        "title": observation.title,
        "relative_path": source_path,
        "source_path": source_path,
        "source_type": metadata.get("source_type"),
        "source_row": metadata.get("source_row"),
        "crn": metadata.get("crn"),
        "start_char": 0,
        "end_char": len(text),
    }
    citation = {
        key: value for key, value in citation.items() if _present(value)
    }
    return [
        Chunk(
            id=make_chunk_id(observation.id, 0, 0, len(text)),
            knowledge_object_id=observation.id,
            object_type=observation.object_type,
            chunk_index=0,
            text=text,
            start_char=0,
            end_char=len(text),
            citation=citation,
            metadata=metadata,
        )
    ]


def chunk_document(document, chunk_size=3000, overlap=300, max_chunks=None):
    if document.object_type == SCHEDULE_OBJECT_TYPE:
        return chunk_course_offering_observation(document)

    raw_chunks = chunk_text(
        document.text,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    chunks = []
    inherited_metadata = _document_metadata(document)

    for i, (text, start, end) in enumerate(raw_chunks):
        if max_chunks is not None and len(chunks) >= max_chunks:
            break

        chunk_id = make_chunk_id(document.id, i, start, end)

        citation = {
            "title": document.title,
            "relative_path": _document_field(document, "relative_path"),
            "source_path": _document_field(
                document,
                "source_path",
                _document_field(document, "path"),
            ),
            "file_type": _document_field(document, "file_type"),
            "parser": _document_field(document, "parser"),
            "start_char": start,
            "end_char": end,
        }

        chunk_metadata = {
            **inherited_metadata,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "max_chunks_per_document": max_chunks,
            "created_at": now_iso(),
        }

        chunks.append(
            Chunk(
                id=chunk_id,
                knowledge_object_id=document.id,
                object_type=document.object_type,
                chunk_index=i,
                text=text,
                start_char=start,
                end_char=end,
                citation=citation,
                metadata=chunk_metadata,
            )
        )

    truncated = max_chunks is not None and len(raw_chunks) > len(chunks)

    for chunk in chunks:
        chunk.metadata["document_truncated"] = truncated
        chunk.metadata["original_chunk_count"] = len(raw_chunks)
        chunk.metadata["indexed_chunk_count"] = len(chunks)

    return chunks


def save_chunks(chunks, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [asdict(chunk) for chunk in chunks]

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def chunk_output_path(document, chunks_dir):
    """
    Derive storage identity from the Knowledge Object ID, not its path.

    Hashing keeps filenames portable even when IDs contain characters such
    as the colon in constitutional:<hash>.
    """
    safe_hash = hashlib.sha256(document.id.encode("utf-8")).hexdigest()
    return Path(chunks_dir) / f"{safe_hash}.json"


def _normalize_source_dirs(
    source_dirs: Optional[Iterable],
    normalized_dir=None,
):
    """
    Support the new source_dirs interface while temporarily retaining the
    old normalized_dir argument for compatibility with older callers.
    """
    if source_dirs is None:
        if normalized_dir is None:
            raise ValueError(
                "run_chunking requires source_dirs or normalized_dir"
            )
        source_dirs = [normalized_dir]

    if isinstance(source_dirs, (str, Path)):
        source_dirs = [source_dirs]

    directories = [Path(path) for path in source_dirs]

    if not directories:
        raise ValueError("source_dirs must contain at least one directory")

    return directories


def run_chunking(
    source_dirs=None,
    chunks_dir=None,
    limit=None,
    chunk_size=3000,
    overlap=300,
    max_chunks_per_document=None,
    normalized_dir=None,
):
    source_dirs = _normalize_source_dirs(
        source_dirs=source_dirs,
        normalized_dir=normalized_dir,
    )

    if chunks_dir is None:
        raise ValueError("chunks_dir is required")

    chunks_dir = Path(chunks_dir)

    results = {
        "attempted": 0,
        "succeeded": 0,
        "failed": 0,
        "documents_with_zero_chunks": 0,
        "total_chunks": 0,
        "max_chunks_per_document_setting": max_chunks_per_document,
        "truncated_documents": 0,
        "errors": [],
        "outputs": [],
        "source_dirs": [str(path) for path in source_dirs],
        "documents_by_source_dir": {},
        "documents_by_object_type": {},
        "chunk_size": chunk_size,
        "overlap": overlap,
        "chunk_lengths": [],
        "chunks_per_document": [],
        "largest_documents": [],
        "chunk_distribution": {},
    }

    object_type_counts = Counter()
    source_dir_counts = Counter()

    for source_dir in source_dirs:
        if not source_dir.exists():
            results["failed"] += 1
            results["errors"].append(
                {
                    "path": str(source_dir),
                    "error": "Source directory does not exist",
                }
            )
            print(f"[WARN] Source directory does not exist: {source_dir}")
            continue

        for path in sorted(source_dir.rglob("*.json")):
            if limit is not None and results["attempted"] >= limit:
                break

            results["attempted"] += 1

            try:
                document = load_knowledge_object(path)

                chunks = chunk_document(
                    document,
                    chunk_size=chunk_size,
                    overlap=overlap,
                    max_chunks=max_chunks_per_document,
                )

                chunk_count = len(chunks)
                chunk_lengths = [len(chunk.text) for chunk in chunks]

                if chunks and chunks[0].metadata.get("document_truncated"):
                    results["truncated_documents"] += 1

                results["chunks_per_document"].append(chunk_count)
                results["chunk_lengths"].extend(chunk_lengths)

                results["largest_documents"].append(
                    {
                        "knowledge_object_id": document.id,
                        "object_type": document.object_type,
                        "relative_path": _document_field(
                            document,
                            "relative_path",
                        ),
                        "title": document.title,
                        "num_chunks": chunk_count,
                        "text_length": len(document.text),
                        "truncated": (
                            chunks[0].metadata.get("document_truncated")
                            if chunks
                            else False
                        ),
                    }
                )

                if len(chunks) == 0:
                    results["documents_with_zero_chunks"] += 1

                outpath = chunk_output_path(document, chunks_dir)
                save_chunks(chunks, outpath)

                results["succeeded"] += 1
                results["total_chunks"] += len(chunks)
                results["outputs"].append(str(outpath))

                object_type_counts[document.object_type] += 1
                source_dir_counts[str(source_dir)] += 1

                print(
                    f"[OK] {len(chunks):4d} chunks  "
                    f"{document.object_type:28s}  "
                    f"{_document_field(document, 'relative_path', document.id)}"
                )

            except Exception as exc:
                results["failed"] += 1
                results["errors"].append(
                    {
                        "path": str(path),
                        "error": str(exc),
                    }
                )
                print(f"[FAIL] {path}: {exc}")

        if limit is not None and results["attempted"] >= limit:
            break

    chunks_per_doc = results["chunks_per_document"]
    chunk_lengths = results["chunk_lengths"]

    results["documents_by_source_dir"] = dict(source_dir_counts)
    results["documents_by_object_type"] = dict(object_type_counts)
    results["chunk_distribution"] = dict(
        Counter(chunks_per_doc).most_common()
    )

    results["average_chunks_per_document"] = (
        sum(chunks_per_doc) / len(chunks_per_doc)
        if chunks_per_doc
        else 0
    )

    results["max_chunks_per_document"] = (
        max(chunks_per_doc)
        if chunks_per_doc
        else 0
    )

    results["average_chunk_length"] = (
        sum(chunk_lengths) / len(chunk_lengths)
        if chunk_lengths
        else 0
    )

    results["min_chunk_length"] = min(chunk_lengths) if chunk_lengths else 0
    results["max_chunk_length"] = max(chunk_lengths) if chunk_lengths else 0

    results["largest_documents"] = sorted(
        results["largest_documents"],
        key=lambda item: item["num_chunks"],
        reverse=True,
    )[:10]

    return results
