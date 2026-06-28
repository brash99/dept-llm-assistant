from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List
import json
import pickle
import re
import hashlib

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# ----------------------------------------------------------------------
# Runtime caches
# ----------------------------------------------------------------------
# These prevent benchmark runs and Streamlit sessions from reloading the
# FAISS index, chunk records, metadata, and embedding model for every query.
_INDEX_CACHE = {}
_MODEL_CACHE = {}


def get_cached_index(vector_db_dir):
    cache_key = str(Path(vector_db_dir).resolve())

    if cache_key not in _INDEX_CACHE:
        _INDEX_CACHE[cache_key] = load_index(vector_db_dir)

    return _INDEX_CACHE[cache_key]


def get_cached_model(model_name, device):
    cache_key = (model_name, device)

    if cache_key not in _MODEL_CACHE:
        _MODEL_CACHE[cache_key] = SentenceTransformer(
            model_name,
            device=device,
        )

    return _MODEL_CACHE[cache_key]


def clear_runtime_caches():
    """Clear loaded FAISS/model caches. Useful after rebuilding vector_db."""
    _INDEX_CACHE.clear()
    _MODEL_CACHE.clear()


def text_fingerprint(text, max_chars=1500):
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    normalized = normalized[:max_chars]
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

@dataclass
class RetrievalResult:
    score: float
    chunk_id: str
    knowledge_object_id: str
    chunk_index: int
    text: str
    citation: Dict[str, Any]
    metadata: Dict[str, Any]


def load_embedding_files(embeddings_dir):
    embeddings_dir = Path(embeddings_dir)

    vectors = []
    records = []

    for path in embeddings_dir.glob("*.json"):
        with path.open("r", encoding="utf-8") as f:
            embedded_chunks = json.load(f)

        for item in embedded_chunks:
            vectors.append(item["embedding"])

            records.append(
                {
                    "chunk_id": item["chunk_id"],
                    "knowledge_object_id": item["knowledge_object_id"],
                    "chunk_index": item["chunk_index"],
                    "text": item["text"],
                    "citation": item["citation"],
                    "metadata": item["metadata"],
                    "embedding_metadata": item["embedding_metadata"],
                }
            )

    if not vectors:
        raise RuntimeError(f"No embeddings found in {embeddings_dir}")

    matrix = np.array(vectors, dtype="float32")

    return matrix, records


def build_faiss_index(embeddings_dir, vector_db_dir):
    vector_db_dir = Path(vector_db_dir)
    vector_db_dir.mkdir(parents=True, exist_ok=True)

    matrix, records = load_embedding_files(embeddings_dir)

    dimension = matrix.shape[1]

    # Embeddings are already normalized, so inner product == cosine similarity.
    index = faiss.IndexFlatIP(dimension)
    index.add(matrix)

    index_path = vector_db_dir / "index.faiss"
    records_path = vector_db_dir / "records.pkl"
    metadata_path = vector_db_dir / "metadata.json"

    faiss.write_index(index, str(index_path))

    with records_path.open("wb") as f:
        pickle.dump(records, f)

    metadata = {
        "num_vectors": int(matrix.shape[0]),
        "dimension": int(dimension),
        "index_type": "IndexFlatIP",
        "distance": "cosine_similarity_via_inner_product",
        "index_path": str(index_path),
        "records_path": str(records_path),
    }

    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata


def load_index(vector_db_dir):
    vector_db_dir = Path(vector_db_dir)

    index = faiss.read_index(str(vector_db_dir / "index.faiss"))

    with (vector_db_dir / "records.pkl").open("rb") as f:
        records = pickle.load(f)

    with (vector_db_dir / "metadata.json").open("r", encoding="utf-8") as f:
        metadata = json.load(f)

    return index, records, metadata

def search_index(
    query,
    vector_db_dir,
    model_name,
    device="cuda",
    top_k=5,
    fetch_k=None,
    dedupe_by="text",
):
    index, records, metadata = get_cached_index(vector_db_dir)

    model = get_cached_model(model_name, device)

    query_vector = model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype("float32")

    if fetch_k is None:
        fetch_k = max(top_k * 5, top_k)

    fetch_k = min(fetch_k, index.ntotal)

    scores, indices = index.search(query_vector, fetch_k)

    results = []
    seen = set()

    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue

        record = records[int(idx)]
        citation = record["citation"]

        if dedupe_by is not None:
            if dedupe_by == "relative_path":
                key = citation.get("relative_path")
            elif dedupe_by == "title":
                key = citation.get("title")
            elif dedupe_by == "knowledge_object_id":
                key = record.get("knowledge_object_id")
            elif dedupe_by == "text":
                key = text_fingerprint(record["text"])
            else:
                key = citation.get(dedupe_by) or record.get(dedupe_by)

            if key in seen:
                continue

            seen.add(key)

        results.append(
            RetrievalResult(
                score=float(score),
                chunk_id=record["chunk_id"],
                knowledge_object_id=record["knowledge_object_id"],
                chunk_index=record["chunk_index"],
                text=record["text"],
                citation=record["citation"],
                metadata=record["metadata"],
            )
        )

        if len(results) >= top_k:
            break

    return results
