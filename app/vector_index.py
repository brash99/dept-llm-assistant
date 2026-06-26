from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List
import json
import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


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
):
    index, records, metadata = load_index(vector_db_dir)

    model = SentenceTransformer(model_name, device=device)

    query_vector = model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype("float32")

    scores, indices = index.search(query_vector, top_k)

    results = []

    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue

        record = records[int(idx)]

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

    return results
