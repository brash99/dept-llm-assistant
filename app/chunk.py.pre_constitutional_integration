from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import hashlib
import json
from collections import Counter

from app.knowledge import load_knowledge_object


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


def chunk_document(document, chunk_size=3000, overlap=300, max_chunks=None):
    raw_chunks = chunk_text(
        document.text,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    chunks = []

    for i, (text, start, end) in enumerate(raw_chunks):
        if max_chunks is not None and len(chunks) >= max_chunks:
            break

        chunk_id = make_chunk_id(document.id, i, start, end)

        citation = {
            "title": document.title,
            "relative_path": document.relative_path,
            "source_path": document.source_path,
            "file_type": document.file_type,
            "parser": document.parser,
            "start_char": start,
            "end_char": end,
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
                metadata={
                    "document_title": document.title,
                    "relative_path": document.relative_path,
                    "parser": document.parser,
                    "file_type": document.file_type,
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "max_chunks_per_document": max_chunks,
                    "created_at": now_iso(),
                },
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
    safe_hash = hashlib.sha256(document.relative_path.encode("utf-8")).hexdigest()
    return Path(chunks_dir) / f"{safe_hash}.json"


def run_chunking(
    normalized_dir,
    chunks_dir,
    limit=None,
    chunk_size=3000,
    overlap=300,
    max_chunks_per_document=None,
):
    normalized_dir = Path(normalized_dir)
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
        "chunk_size": chunk_size,
        "overlap": overlap,
        "chunk_lengths": [],
        "chunks_per_document": [],
        "largest_documents": [],
        "chunk_distribution": {},
    }

    for path in normalized_dir.glob("*.json"):
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
                    "relative_path": document.relative_path,
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

            print(f"[OK] {len(chunks):4d} chunks  {document.relative_path}")

        except Exception as exc:
            results["failed"] += 1
            results["errors"].append(
                {
                    "path": str(path),
                    "error": str(exc),
                }
            )
            print(f"[FAIL] {path}: {exc}")

    chunks_per_doc = results["chunks_per_document"]
    chunk_lengths = results["chunk_lengths"]

    results["chunk_distribution"] = dict(Counter(chunks_per_doc).most_common())

    results["average_chunks_per_document"] = (
        sum(chunks_per_doc) / len(chunks_per_doc)
        if chunks_per_doc
        else 0
    )

    results["max_chunks_per_document"] = max(chunks_per_doc) if chunks_per_doc else 0

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
