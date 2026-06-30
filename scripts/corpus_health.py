#!/usr/bin/env python3

from pathlib import Path

from app.config import load_config
from app.corpus_observatory import analyze_corpus


def main():
    config = load_config()
    root = Path(config["project"]["root"])
    chunks_dir = root / config["storage"]["chunks"]

    report = analyze_corpus(chunks_dir)

    print("=" * 70)
    print("Corpus Health")
    print("=" * 70)
    print(f"Chunks dir           : {report['chunks_dir']}")
    print(f"Documents            : {report['documents']}")
    print(f"Total chunks         : {report['total_chunks']}")
    print(f"Mean chunks/document : {report['mean']:.2f}")
    print(f"Median               : {report['median']}")
    print(f"Std Dev              : {report['stddev']:.2f}")
    print()
    print("Percentiles")
    print("-" * 30)
    print(f"90% : {report['p90']} chunks")
    print(f"95% : {report['p95']} chunks")
    print(f"99% : {report['p99']} chunks")

    print()
    print("Largest Documents")
    print("-" * 30)
    for r in report["largest"]:
        print(f"{r['count']:7d}  {r['type']:5s}  {r['title']}")
        print(f"         {r['path']}")

    print()
    print("Dominance")
    print("-" * 30)
    for k, frac in report["dominance"].items():
        print(f"Top {k:3d}: {100 * frac:6.2f}% of all chunks")

    print()
    print(f"Gini coefficient     : {report['gini']:.4f}")


if __name__ == "__main__":
    main()
