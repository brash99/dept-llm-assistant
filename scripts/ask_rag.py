#!/usr/bin/env python3

from pathlib import Path
import argparse

from app.config import load_config
from app.rag import answer_question


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--fetch-k", type=int, default=None)
    parser.add_argument("--no-dedupe", action="store_true")
    args = parser.parse_args()

    config = load_config()

    project_root = Path(config["project"]["root"])
    vector_db_dir = project_root / config["storage"]["vector_db"]

    embed_cfg = config.get("embedding", {})
    llm_cfg = config.get("llm", {})

    rerank_cfg = config.get("reranking", {})

    answer, results = answer_question(
        query=args.query,
        vector_db_dir=vector_db_dir,
        model_name=embed_cfg.get("model", "BAAI/bge-small-en-v1.5"),
        embedding_device=embed_cfg.get("device", "cuda"),
        llm_base_url=llm_cfg["base_url"],
        llm_model=llm_cfg["model"],
        top_k=args.top_k,
        fetch_k=args.fetch_k,
        dedupe_by=None if args.no_dedupe else "relative_path",
        rerank=rerank_cfg.get("enabled", False),
        reranker_model=rerank_cfg.get("model"),
        reranker_device=rerank_cfg.get("device", "cuda"),
    )

    print("=" * 70)
    print("Answer")
    print("=" * 70)
    print(answer)
    print()

    print("=" * 70)
    print("Sources")
    print("=" * 70)

    for i, result in enumerate(results, start=1):
        citation = result.citation
        print(f"[Source {i}] score={result.score:.4f}")
        print(f"Title: {citation.get('title')}")
        print(f"Path : {citation.get('relative_path')}")
        print()


if __name__ == "__main__":
    main()
