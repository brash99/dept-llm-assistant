#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import argparse
import json

from app.config import load_config
from app.embed import embed_chunks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000000)
    parser.add_argument(
        "--embedding-context",
        choices=["none", "title", "title_path", "metadata"],
        default="none",
        help=(
            "Context prepended only to embedding input text. "
            "Stored chunk text is unchanged."
        ),
    )
    args = parser.parse_args()

    config = load_config()

    project_root = Path(config["project"]["root"])
    chunks_dir = project_root / config["storage"]["chunks"]
    embeddings_dir = project_root / config["storage"]["embeddings"]
    logs_dir = project_root / config["storage"]["logs"]

    embed_cfg = config.get("embedding", {})

    model_name = embed_cfg.get("model", "BAAI/bge-small-en-v1.5")
    batch_size = embed_cfg.get("batch_size", 32)
    device = embed_cfg.get("device", "cuda")

    print("=" * 70)
    print("Chunk Embedding")
    print("=" * 70)
    print(f"Chunks dir     : {chunks_dir}")
    print(f"Embeddings dir : {embeddings_dir}")
    print(f"Model          : {model_name}")
    print(f"Device         : {device}")
    print(f"Embedding context: {args.embedding_context}")
    print(f"Batch size     : {batch_size}")
    print(f"Limit          : {args.limit}")
    print()

    results = embed_chunks(
        chunks_dir=chunks_dir,
        embeddings_dir=embeddings_dir,
        model_name=model_name,
        batch_size=batch_size,
        device=device,
        limit=args.limit,
        embedding_context=args.embedding_context,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"embedding_{timestamp}.json"

    with log_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Attempted files      : {results['attempted_files']}")
    print(f"Succeeded files      : {results['succeeded_files']}")
    print(f"Failed files         : {results['failed_files']}")
    print(f"Total chunks embedded: {results['total_chunks']}")
    print(f"Embedding dimension  : {results['embedding_dimension']}")
    print(f"Log file             : {log_path}")


if __name__ == "__main__":
    main()
