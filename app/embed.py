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
            texts = [chunk["text"] for chunk in chunks]

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
