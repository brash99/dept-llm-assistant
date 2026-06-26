from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import hashlib
import json

from app.knowledge import load_knowledge_object


@dataclass
class Chunk:
    id: str
    document_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    metadata: Dict[str, Any]


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def make_chunk_id(document_id, chunk_index, text):
    base = f"{document_id}:{chunk_index}:{text}"
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


def chunk_document(document, chunk_size=3000, overlap=300):
    raw_chunks = chunk_text(
        document.text,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    chunks = []

    for i, (text, start, end) in enumerate(raw_chunks):
        chunk_id = make_chunk_id(document.id, i, text)

        chunks.append(
            Chunk(
                id=chunk_id,
                document_id=document.id,
                chunk_index=i,
                text=text,
                start_char=start,
                end_char=end,
                metadata={
                    "document_title": document.title,
                    "relative_path": document.relative_path,
                    "parser": document.parser,
                    "file_type": document.file_type,
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "created_at": now_iso(),
                },
            )
        )

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


def run_chunking(normalized_dir, chunks_dir, limit=None, chunk_size=3000, overlap=300):
    normalized_dir = Path(normalized_dir)
    chunks_dir = Path(chunks_dir)

    results = {
        "attempted": 0,
        "succeeded": 0,
        "failed": 0,
        "documents_with_zero_chunks": 0,
        "total_chunks": 0,
        "errors": [],
        "outputs": [],
        "chunk_size": chunk_size,
        "overlap": overlap,
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

    return results
