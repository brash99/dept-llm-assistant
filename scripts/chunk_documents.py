#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import argparse
import json

from app.config import load_config
from app.chunk import run_chunking


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000000)
    parser.add_argument("--chunk-size", type=int, default=None)
    parser.add_argument("--overlap", type=int, default=None)
    parser.add_argument("--max-chunks-per-document", type=int, default=None)
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        help="Override the configured chunk destination (useful for validation).",
    )
    parser.add_argument(
        "--logs-dir",
        type=Path,
        help="Override the configured log destination (useful for validation).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print one success record per Knowledge Object.",
    )
    args = parser.parse_args()

    config = load_config()
    chunk_cfg = config.get("chunking", {})

    chunk_size = args.chunk_size or chunk_cfg.get("chunk_size", 3000)
    overlap = args.overlap or chunk_cfg.get("overlap", 300)

    if args.max_chunks_per_document is not None:
        max_chunks = args.max_chunks_per_document
    else:
        max_chunks = chunk_cfg.get("max_chunks_per_document")

    configured_root = Path(config["project"]["root"])
    project_root = configured_root if configured_root.exists() else PROJECT_ROOT
    normalized_dir = project_root / config["storage"]["normalized"]
    constitutional_dir = project_root / config["storage"]["constitutional"]
    source_dirs = [
        normalized_dir,
        constitutional_dir,
    ]
    chunks_dir = args.chunks_dir or (project_root / config["storage"]["chunks"])
    logs_dir = args.logs_dir or (project_root / config["storage"]["logs"])
    logs_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Document Chunking")
    print("=" * 70)
    print("Source dirs:")
    for source_dir in source_dirs:
        print(f"  - {source_dir}")
    print(f"Chunks dir     : {chunks_dir}")
    print(f"Limit          : {args.limit}")
    print(f"Chunk size     : {chunk_size}")
    print(f"Overlap        : {overlap}")
    print(f"Max chunks/doc : {max_chunks}")
    print()

    results = run_chunking(
        source_dirs=source_dirs,
        chunks_dir=chunks_dir,
        limit=args.limit,
        chunk_size=chunk_size,
        overlap=overlap,
        max_chunks_per_document=max_chunks,
        verbose=args.verbose,
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
    print(f"Truncated documents       : {results['truncated_documents']}")
    print(f"Total chunks              : {results['total_chunks']}")
    print(f"Average chunks/document   : {results['average_chunks_per_document']:.2f}")
    print(f"Max chunks/document       : {results['max_chunks_per_document']}")
    print(f"Average chunk length      : {results['average_chunk_length']:.1f}")
    print(f"Min chunk length          : {results['min_chunk_length']}")
    print(f"Max chunk length          : {results['max_chunk_length']}")

    print()
    print("Documents by Object Type")
    print("-" * 70)
    for object_type, count in sorted(results["documents_by_object_type"].items()):
        print(f"{object_type:44s}: {count:8,d}")

    if args.verbose:
        print()
        print("Chunk Distribution")
        print("-" * 70)
        for num_chunks, count in results["chunk_distribution"].items():
            print(f"{num_chunks:>4} chunks : {count:8,d} documents")

        print()
        print("Largest Documents by Chunk Count")
        print("-" * 70)
        for item in results["largest_documents"][:5]:
            truncated = " TRUNCATED" if item.get("truncated") else ""
            print(
                f"{item['num_chunks']:>4} chunks  "
                f"{item['text_length']:>8,d} chars  "
                f"{item['relative_path']}{truncated}"
            )

    print(f"Log file                  : {log_path}")


if __name__ == "__main__":
    main()
