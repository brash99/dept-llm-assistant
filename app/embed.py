from pathlib import Path
from datetime import datetime
import json

from sentence_transformers import SentenceTransformer


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def load_chunks_file(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def embedding_output_path(chunk_file, embeddings_dir):
    return Path(embeddings_dir) / Path(chunk_file).name


def _clean_metadata_value(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        text = str(value).strip()
        return text or None

    return None


def build_embedding_text(chunk, embedding_context="none"):
    """
    Build the text sent to the embedding model.

    The stored/displayed chunk text remains unchanged. This function only
    changes the semantic context seen by the embedding model.
    """
    mode = embedding_context or "none"

    if mode == "none":
        return chunk["text"]

    citation = chunk.get("citation", {}) or {}
    metadata = chunk.get("metadata", {}) or {}

    title = (
        citation.get("title")
        or metadata.get("title")
        or citation.get("filename")
        or metadata.get("filename")
    )

    relative_path = citation.get("relative_path") or metadata.get("relative_path")
    source_path = citation.get("source_path") or metadata.get("source_path")

    path = relative_path or source_path

    lines = []

    if mode in ("title", "title_path", "metadata") and title:
        lines.append(f"Document title: {title}")

    if mode in ("title_path", "metadata") and path:
        lines.append(f"Document path: {path}")

    if mode == "metadata":
        source_type = (
            citation.get("source_type")
            or metadata.get("source_type")
            or citation.get("parser")
            or metadata.get("parser")
        )

        file_type = (
            citation.get("file_type")
            or metadata.get("file_type")
            or citation.get("extension")
            or metadata.get("extension")
        )

        if source_type:
            lines.append(f"Document type: {source_type}")

        if file_type:
            lines.append(f"File type: {file_type}")

    if not lines:
        return chunk["text"]

    return "\n".join(lines) + "\n\n" + chunk["text"]


def embed_chunks(
    chunks_dir,
    embeddings_dir,
    model_name,
    batch_size=32,
    device="cuda",
    limit=None,
):
    chunks_dir = Path(chunks_dir)
    embeddings_dir = Path(embeddings_dir)
    embeddings_dir.mkdir(parents=True, exist_ok=True)

    model = SentenceTransformer(model_name, device=device)

    results = {
        "embedding_time": now_iso(),
        "model": model_name,
        "device": device,
        "batch_size": batch_size,
        "attempted_files": 0,
        "succeeded_files": 0,
        "failed_files": 0,
        "total_chunks": 0,
        "embedding_dimension": None,
        "outputs": [],
        "errors": [],
    }

    for path in chunks_dir.glob("*.json"):
        if limit is not None and results["attempted_files"] >= limit:
            break

        results["attempted_files"] += 1

        try:
            chunks = load_chunks_file(path)
            texts = [
                build_embedding_text(
                    chunk,
                    embedding_context=embedding_context,
                )
                for chunk in chunks
            ]

            if not texts:
                vectors = []
            else:
                vectors = model.encode(
                    texts,
                    batch_size=batch_size,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                ).tolist()

            embedded_chunks = []

            for chunk, vector in zip(chunks, vectors):
                if results["embedding_dimension"] is None:
                    results["embedding_dimension"] = len(vector)

                embedded_chunks.append(
                    {
                        "chunk_id": chunk["id"],
                        "knowledge_object_id": chunk["knowledge_object_id"],
                        "chunk_index": chunk["chunk_index"],
                        "text": chunk["text"],
                        "citation": chunk["citation"],
                        "metadata": chunk["metadata"],
                        "embedding": vector,
                        "embedding_metadata": {
                            "model": model_name,
                            "device": device,
                            "normalized": True,
                            "embedding_context": embedding_context,
                            "created_at": now_iso(),
                        },
                    }
                )

            outpath = embedding_output_path(path, embeddings_dir)

            with outpath.open("w", encoding="utf-8") as f:
                json.dump(embedded_chunks, f)

            results["succeeded_files"] += 1
            results["total_chunks"] += len(embedded_chunks)
            results["outputs"].append(str(outpath))

            print(f"[OK] {len(embedded_chunks):4d} embeddings  {path.name}")

        except Exception as exc:
            results["failed_files"] += 1
            results["errors"].append(
                {
                    "path": str(path),
                    "error": str(exc),
                }
            )
            print(f"[FAIL] {path}: {exc}")

    return results
