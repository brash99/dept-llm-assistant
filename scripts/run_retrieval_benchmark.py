from pathlib import Path
from datetime import datetime
import json
import yaml
import argparse

from app.config import load_config
from app.retrieval import retrieve


def contains_any(text, needles):
    if not needles:
        return False

    text = (text or "").lower()
    return any(needle.lower() in text for needle in needles)


def matches_pattern(path, patterns):
    if not patterns:
        return False

    path = path or ""
    return any(pattern in path for pattern in patterns)


def is_required_hit(case, result):
    citation = result.citation
    path = citation.get("relative_path", "") or ""
    title = citation.get("title", "") or ""
    text = result.text or ""

    required_sources = case.get("required_sources", [])
    required_title_contains = case.get("required_title_contains", [])
    required_text_contains = case.get("required_text_contains", [])

    path_hit = path in required_sources

    title_hit = (
        contains_any(title, required_title_contains)
        if required_title_contains
        else False
    )

    text_hit = (
        all(needle.lower() in text.lower() for needle in required_text_contains)
        if required_text_contains
        else False
    )

    return path_hit or title_hit or text_hit


def find_required_rank(case, results):
    for i, result in enumerate(results, start=1):
        if is_required_hit(case, result):
            return i

    return None


def evaluate_case(case, final_results, trace):
    acceptable_sources = case.get("acceptable_sources", [])
    bad_source_patterns = case.get("bad_source_patterns", [])

    stage_ranks = {
        "raw_rank": find_required_rank(case, trace.raw_candidates),
        "deduped_rank": find_required_rank(case, trace.deduped_candidates),
        "reranked_rank": find_required_rank(case, trace.reranked_candidates),
        "threshold_rank": find_required_rank(
            case,
            trace.thresholded_candidates,
        ),
        "final_rank": find_required_rank(case, final_results),
    }

    acceptable_hits = []
    bad_hits = []

    for i, result in enumerate(final_results[:5], start=1):
        path = result.citation.get("relative_path", "") or ""

        if path in acceptable_sources:
            acceptable_hits.append(path)

        if matches_pattern(path, bad_source_patterns):
            bad_hits.append(path)

    final_rank = stage_ranks["final_rank"]

    return {
        "required_in_top1": final_rank == 1,
        "required_in_top5": final_rank is not None and final_rank <= 5,
        "required_rank": final_rank,
        "stage_ranks": stage_ranks,
        "acceptable_count_top5": len(acceptable_hits),
        "acceptable_hits": acceptable_hits,
        "bad_count_top5": len(bad_hits),
        "bad_hits": bad_hits,
    }


def serialize_results(results, max_items=None):
    if max_items is not None:
        results = results[:max_items]

    return [
        {
            "rank": i,
            "title": r.citation.get("title"),
            "relative_path": r.citation.get("relative_path"),
            "score": r.score,
            "faiss_score": r.metadata.get("faiss_score"),
            "rerank_score": r.metadata.get("rerank_score"),
        }
        for i, r in enumerate(results, start=1)
    ]


def main():
    
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--benchmark",
        default="retrieval_benchmark.yaml",
        help="Benchmark YAML file in benchmarks/",
    )

    args = parser.parse_args()

    config = load_config()

    project_root = Path(config["project"]["root"])
    vector_db_dir = project_root / config["storage"]["vector_db"]
    logs_dir = project_root / config["storage"]["logs"]
    logs_dir.mkdir(parents=True, exist_ok=True)

    benchmark_path = project_root / "benchmarks" / args.benchmark

    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark = yaml.safe_load(f)

    embed_cfg = config.get("embedding", {})
    rerank_cfg = config.get("reranking", {})

    results_out = []

    print("=" * 70)
    print("Retrieval Benchmark")
    print("=" * 70)

    for case in benchmark["benchmarks"]:
        query = case["question"]

        final_results, report, trace, profile = retrieve(
            query=query,
            vector_db_dir=vector_db_dir,
            model_name=embed_cfg.get("model", "BAAI/bge-small-en-v1.5"),
            device=embed_cfg.get("device", "cuda"),
            top_k=5,
            fetch_k=50,
            dedupe_by="relative_path",
            rerank=rerank_cfg.get("enabled", False),
            reranker_model=rerank_cfg.get("model"),
            reranker_device=rerank_cfg.get("device", "cuda"),
            min_rerank_score=rerank_cfg.get("min_score"),
            return_trace=True,
        )

        evaluation = evaluate_case(case, final_results, trace)

        row = {
            "id": case["id"],
            "category": case.get("category"),
            "question": query,
            "evaluation": evaluation,
            "profile": profile.__dict__,
            "final_sources": serialize_results(final_results),
            "raw_top10": serialize_results(trace.raw_candidates, max_items=10),
            "deduped_top10": serialize_results(trace.deduped_candidates, max_items=10),
            "reranked_top10": serialize_results(trace.reranked_candidates, max_items=10),
            "threshold_top10": serialize_results(
                trace.thresholded_candidates,
                max_items=10,
            ),
            "report": report.__dict__,
        }

        results_out.append(row)

        status = "PASS" if evaluation["required_in_top5"] else "FAIL"
        ranks = evaluation["stage_ranks"]

        print(
            f"{status:4} {case['id']:30} "
            f"final={ranks['final_rank']} "
            f"raw={ranks['raw_rank']} "
            f"dedup={ranks['deduped_rank']} "
            f"rerank={ranks['reranked_rank']} "
            f"time={profile.total_seconds:.2f}s "
            f"acceptable@5={evaluation['acceptable_count_top5']} "
            f"bad@5={evaluation['bad_count_top5']}"
        )

    summary = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "num_cases": len(results_out),
        "required_top1_hits": sum(
            1 for r in results_out if r["evaluation"]["required_in_top1"]
        ),
        "required_top5_hits": sum(
            1 for r in results_out if r["evaluation"]["required_in_top5"]
        ),
        "acceptable_count_top5": sum(
            r["evaluation"]["acceptable_count_top5"] for r in results_out
        ),
        "bad_count_top5": sum(
            r["evaluation"]["bad_count_top5"] for r in results_out
        ),
        "total_seconds": sum(r["profile"]["total_seconds"] for r in results_out),
        "average_seconds": (
            sum(r["profile"]["total_seconds"] for r in results_out)
            / len(results_out)
            if results_out else 0.0
        ),
        "average_search_seconds": (
            sum(r["profile"]["search_seconds"] for r in results_out)
            / len(results_out)
            if results_out else 0.0
        ),
        "average_rerank_seconds": (
            sum(r["profile"]["rerank_seconds"] for r in results_out)
            / len(results_out)
            if results_out else 0.0
        ),
    }

    output = {
        "summary": summary,
        "results": results_out,
    }

    outpath = logs_dir / f"retrieval_benchmark_{datetime.now():%Y%m%d_%H%M%S}.json"

    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print()
    print("-" * 70)
    print("Summary")
    print("-" * 70)
    print(f"Cases               : {summary['num_cases']}")
    print(f"Required Top-1 hits : {summary['required_top1_hits']}")
    print(f"Required Top-5 hits : {summary['required_top5_hits']}")
    print(f"Acceptable@5 total  : {summary['acceptable_count_top5']}")
    print(f"Bad@5 total         : {summary['bad_count_top5']}")
    print(f"Total time          : {summary['total_seconds']:.2f}s")
    print(f"Average time/case   : {summary['average_seconds']:.2f}s")
    print(f"Average search time : {summary['average_search_seconds']:.2f}s")
    print(f"Average rerank time : {summary['average_rerank_seconds']:.2f}s")
    print(f"Log file            : {outpath}")


if __name__ == "__main__":
    main()
