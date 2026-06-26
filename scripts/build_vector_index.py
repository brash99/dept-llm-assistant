#!/usr/bin/env python3

from pathlib import Path
import json

from app.config import load_config
from app.vector_index import build_faiss_index


def main():
    config = load_config()

    project_root = Path(config["project"]["root"])
    embeddings_dir = project_root / config["storage"]["embeddings"]
    vector_db_dir = project_root / config["storage"]["vector_db"]

    print("=" * 70)
    print("Build Vector Index")
    print("=" * 70)
    print(f"Embeddings dir : {embeddings_dir}")
    print(f"Vector DB dir  : {vector_db_dir}")
    print()

    metadata = build_faiss_index(
        embeddings_dir=embeddings_dir,
        vector_db_dir=vector_db_dir,
    )

    print("Index built.")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
