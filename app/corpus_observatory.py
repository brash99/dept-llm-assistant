import json
import statistics
from pathlib import Path
from collections import Counter, defaultdict


def _percentile(values, p):
    if not values:
        return 0
    idx = min(len(values) - 1, int(p * len(values)))
    return values[idx]


def _gini(values):
    if not values or sum(values) == 0:
        return 0.0
    vals = sorted(values)
    n = len(vals)
    weighted = sum(i * x for i, x in enumerate(vals, 1))
    return (2 * weighted) / (n * sum(vals)) - (n + 1) / n


def analyze_corpus(chunks_dir, largest_n=25):
    chunks_dir = Path(chunks_dir)

    records = []
    parser_counts = Counter()
    type_counts = Counter()
    folder_counts = Counter()

    for p in chunks_dir.glob("*.json"):
        with p.open(encoding="utf-8") as f:
            chunks = json.load(f)

        if chunks:
            meta = chunks[0].get("metadata", {})
            citation = chunks[0].get("citation", {})
        else:
            meta = {}
            citation = {}

        count = len(chunks)
        rel_path = meta.get("relative_path") or citation.get("relative_path") or ""
        file_type = meta.get("file_type") or citation.get("file_type") or ""
        parser = meta.get("parser") or citation.get("parser") or ""
        top_folder = rel_path.split("/", 1)[0] if rel_path else "(unknown)"

        record = {
            "count": count,
            "title": meta.get("document_title") or citation.get("title") or "",
            "path": rel_path,
            "type": file_type,
            "parser": parser,
            "file": p.name,
        }
        records.append(record)

        parser_counts[parser] += count
        type_counts[file_type] += count
        folder_counts[top_folder] += count

    counts = sorted(r["count"] for r in records)
    total = sum(counts)

    records_sorted = sorted(records, key=lambda r: r["count"], reverse=True)

    return {
        "chunks_dir": str(chunks_dir),
        "documents": len(records),
        "total_chunks": total,
        "mean": statistics.mean(counts) if counts else 0,
        "median": statistics.median(counts) if counts else 0,
        "stddev": statistics.stdev(counts) if len(counts) > 1 else 0,
        "p90": _percentile(counts, 0.90),
        "p95": _percentile(counts, 0.95),
        "p99": _percentile(counts, 0.99),
        "gini": _gini(counts),
        "largest": records_sorted[:largest_n],
        "dominance": {
            k: (sum(r["count"] for r in records_sorted[:k]) / total if total else 0)
            for k in [1, 5, 10, 100]
        },
        "by_type": type_counts.most_common(),
        "by_parser": parser_counts.most_common(),
        "by_folder": folder_counts.most_common(),
    }
