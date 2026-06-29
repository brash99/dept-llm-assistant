from pathlib import Path
import argparse
import yaml

from app.config import load_config
from app.retrieval import retrieve


def print_case(case):
    print("=" * 70)
    print("Benchmark Case")
    print("=" * 70)
    print(f"ID       : {case.get('id')}")
    print(f"Category : {case.get('category')}")
    print()
    print(case["question"])
    print()

    if case.get("required_sources"):
        print("Required sources:")
        for source in case["required_sources"]:
            print(f"  - {source}")
        print()

    if case.get("acceptable_sources"):
        print("Acceptable sources:")
        for source in case["acceptable_sources"]:
            print(f"  - {source}")
        print()

    if case.get("bad_source_patterns"):
        print("Bad source patterns:")
        for pattern in case["bad_source_patterns"]:
            print(f"  - {pattern}")
        print()


def print_stage(title, results, max_items=20):
    print("=" * 70)
    print(title)
    print("=" * 70)

    if not results:
        print("(none)")
        print()
        return

    for i, result in enumerate(results[:max_items], start=1):
        citation = result.citation
        metadata = result.metadata

        title_text = citation.get("title") or metadata.get("document_title") or "Untitled"
        path = citation.get("relative_path") or metadata.get("relative_path") or "Unknown path"

        faiss_score = metadata.get("faiss_score")
        rerank_score = metadata.get("rerank_score")

        score_parts = [f"score={result.score:.4f}"]

        if faiss_score is not None:
            score_parts.append(f"faiss={faiss_score:.4f}")

        if rerank_score is not None:
            score_parts.append(f"rerank={rerank_score:.4f}")

        print(f"{i}. {title_text}")
        print(f"   Path: {path}")
        print(f"   {' | '.join(score_parts)}")

        preview = (result.text or "").replace("\n", " ").strip()
        if preview:
            print()
            print(f"   {preview[:500]}")

        print()

    if len(results) > max_items:
        print(f"... {len(results) - max_items} more results not shown")
        print()


def find_case(benchmark, case_id):
    for case in benchmark.get("benchmarks", []):
        if case.get("id") == case_id:
            return case

    available = [case.get("id") for case in benchmark.get("benchmarks", [])]
    raise ValueError(
        f"Benchmark case not found: {case_id}\n"
        f"Available cases: {', '.join(available)}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Analyze retrieval stages for a single benchmark case."
    )

    parser.add_argument(
        "--benchmark",
        default="retrieval_benchmark.yaml",
        help="Benchmark YAML file relative to the benchmarks/ directory.",
    )

    parser.add_argument(
        "--case",
        required=True,
        help="Benchmark case id to analyze.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Final number of retrieved results.",
    )

    parser.add_argument(
        "--fetch-k",
        type=int,
        default=50,
        help="Number of raw candidates to fetch before reranking.",
    )

    parser.add_argument(
        "--max-items",
        type=int,
        default=20,
        help="Maximum number of results to print per stage.",
    )

    args = parser.parse_args()

    config = load_config()

    project_root = Path(config["project"]["root"])
    benchmark_path = project_root / "benchmarks" / args.benchmark

    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark = yaml.safe_load(f)

    case = find_case(benchmark, args.case)

    embed_cfg = config.get("embedding", {})
    rerank_cfg = config.get("reranking", {})

    vector_db_dir = project_root / config["storage"]["vector_db"]

    print_case(case)

    results, report, trace, profile = retrieve(
        query=case["question"],
        vector_db_dir=vector_db_dir,
        model_name=embed_cfg.get("model", "BAAI/bge-small-en-v1.5"),
        device=embed_cfg.get("device", "cuda"),
        top_k=args.top_k,
        fetch_k=args.fetch_k,
        dedupe_by="relative_path",
        rerank=rerank_cfg.get("enabled", False),
        reranker_model=rerank_cfg.get("model"),
        reranker_device=rerank_cfg.get("device", "cuda"),
        min_rerank_score=rerank_cfg.get("min_score"),
        return_trace=True,
    )

    print("=" * 70)
    print("Retrieval Report")
    print("=" * 70)
    print(report)
    print()

    print("=" * 70)
    print("Timing")
    print("=" * 70)
    print(f"Total     : {profile.total_seconds:.3f}s")
    print(f"Search    : {profile.search_seconds:.3f}s")
    print(f"Dedupe    : {profile.dedupe_seconds:.3f}s")
    print(f"Rerank    : {profile.rerank_seconds:.3f}s")
    print(f"Threshold : {profile.threshold_seconds:.3f}s")
    print()

    print_stage("Raw FAISS Candidates", trace.raw_candidates, args.max_items)
    print_stage("After Deduplication", trace.deduped_candidates, args.max_items)
    print_stage("After Reranking", trace.reranked_candidates, args.max_items)

    thresholded = getattr(trace, "thresholded_candidates", trace.reranked_candidates)
    print_stage("After Threshold", thresholded, args.max_items)

    print_stage("Final Results", results, args.max_items)


if __name__ == "__main__":
    main()
