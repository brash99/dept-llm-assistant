#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import argparse
import json

from app.config import load_config
from app.chunk import run_chunking


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--chunk-size", type=int, default=3000)
    parser.add_argument("--overlap", type=int, default=300)
    args = parser.parse_args()

    config = load_config()

    project_root = Path(config["project"]["root"])
    normalized_dir = project_root / config["storage"]["normalized"]
    chunks_dir = project_root / config["storage"]["chunks"]
    logs_dir = project_root / config["storage"]["logs"]

    print("=" * 70)
    print("Document Chunking")
    print("=" * 70)
    print(f"Normalized dir : {normalized_dir}")
    print(f"Chunks dir     : {chunks_dir}")
    print(f"Limit          : {args.limit}")
    print(f"Chunk size     : {args.chunk_size}")
    print(f"Overlap        : {args.overlap}")
    print()

    results = run_chunking(
        normalized_dir=normalized_dir,
        chunks_dir=chunks_dir,
        limit=args.limit,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"chunking_{timestamp}.json"

    with log_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Attempted                 : {results['attempted']}")
    print(f"Succeeded                 : {results['succeeded']}")
    print(f"Failed                    : {results['failed']}")
    print(f"Documents with zero chunks: {results['documents_with_zero_chunks']}")
    print(f"Total chunks              : {results['total_chunks']}")
    print(f"Log file                  : {log_path}")


if __name__ == "__main__":
    main()
