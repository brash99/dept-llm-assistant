#!/usr/bin/env python3

from pathlib import Path
import argparse

from app.config import load_config
from app.vector_index import search_index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    config = load_config()

    project_root = Path(config["project"]["root"])
    vector_db_dir = project_root / config["storage"]["vector_db"]

    embed_cfg = config.get("embedding", {})
    model_name = embed_cfg.get("model", "BAAI/bge-small-en-v1.5")
    device = embed_cfg.get("device", "cuda")

    print("=" * 70)
    print("Semantic Chunk Search")
    print("=" * 70)
    print(f"Query : {args.query}")
    print(f"Model : {model_name}")
    print(f"Top K : {args.top_k}")
    print()

    results = search_index(
        query=args.query,
        vector_db_dir=vector_db_dir,
        model_name=model_name,
        device=device,
        top_k=args.top_k,
    )

    for i, result in enumerate(results, start=1):
        citation = result.citation

        print("=" * 70)
        print(f"Result {i}")
        print("=" * 70)
        print(f"Score : {result.score:.4f}")
        print(f"Title : {citation.get('title')}")
        print(f"Path  : {citation.get('relative_path')}")
        print(f"Chars : {citation.get('start_char')}–{citation.get('end_char')}")
        print()
        print(result.text[:1200].strip())

        if len(result.text) > 1200:
            print()
            print("...")


if __name__ == "__main__":
    main()
