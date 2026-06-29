from pathlib import Path
from datetime import datetime
from collections import defaultdict
import argparse
import json

import yaml

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



def rank_displacement(before, after):
    """
    Positive means reranking moved the required document closer to the top.
    Negative means reranking moved it farther away.
    None means the required document was absent from one of the stages.
    """
    if before is None or after is None:
        return None
    return before - after


def score_spread(results, field="score", top_n=5):
    """
    Return max-min score spread among the first top_n results.

    field="score" uses the Result.score value.
    Any other field is read from Result.metadata.
    """
    vals = []

    for result in results[:top_n]:
        if field == "score":
            value = result.score
        else:
            value = result.metadata.get(field)

        if value is not None:
            vals.append(value)

    if len(vals) < 2:
        return None

    return max(vals) - min(vals)


def evaluate_case(case, final_results, trace):
    acceptable_sources = case.get("acceptable_sources", [])
    bad_source_patterns = case.get("bad_source_patterns", [])

    stage_ranks = {
        "raw_rank": find_required_rank(case, trace.raw_candidates),
        "deduped_rank": find_required_rank(case, trace.deduped_candidates),
        "reranked_rank": find_required_rank(case, trace.reranked_candidates),
        "threshold_rank": find_required_rank(case, trace.thresholded_candidates),
        "final_rank": find_required_rank(case, final_results),
    }

    raw_rank = stage_ranks["raw_rank"]
    reranked_rank = stage_ranks["reranked_rank"]

    reranker_helped = (
        raw_rank is not None
        and reranked_rank is not None
        and reranked_rank < raw_rank
    )

    reranker_hurt = (
        raw_rank is not None
        and reranked_rank is not None
        and reranked_rank > raw_rank
    )

    rerank_displacement = rank_displacement(raw_rank, reranked_rank)

    faiss_score_spread_top5 = score_spread(
        trace.raw_candidates,
        field="score",
        top_n=5,
    )

    rerank_score_spread_top5 = score_spread(
        trace.reranked_candidates,
        field="rerank_score",
        top_n=5,
    )

    acceptable_hits = []
    bad_hits = []

    for result in final_results[:5]:
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
        "reranker_helped": reranker_helped,
        "reranker_hurt": reranker_hurt,
        "rerank_displacement": rerank_displacement,
        "faiss_score_spread_top5": faiss_score_spread_top5,
        "rerank_score_spread_top5": rerank_score_spread_top5,
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


def summarize_by_category(results_out):
    category_stats = defaultdict(
        lambda: {
            "cases": 0,
            "top1": 0,
            "top5": 0,
            "acceptable": 0,
            "bad": 0,
            "reranker_helped": 0,
            "reranker_hurt": 0,
            "reranker_no_change": 0,
            "total_seconds": 0.0,
        }
    )

    for result in results_out:
        category = result.get("category") or "uncategorized"
        stats = category_stats[category]
        evaluation = result["evaluation"]
        profile = result.get("profile", {})

        stats["cases"] += 1

        if evaluation.get("required_in_top1"):
            stats["top1"] += 1

        if evaluation.get("required_in_top5"):
            stats["top5"] += 1

        stats["acceptable"] += evaluation.get("acceptable_count_top5", 0)
        stats["bad"] += evaluation.get("bad_count_top5", 0)

        if evaluation.get("reranker_helped"):
            stats["reranker_helped"] += 1
        elif evaluation.get("reranker_hurt"):
            stats["reranker_hurt"] += 1
        else:
            stats["reranker_no_change"] += 1

        stats["total_seconds"] += profile.get("total_seconds", 0.0)

    return dict(category_stats)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--benchmark",
        default="retrieval_benchmark.yaml",
        help="Benchmark YAML file relative to the benchmarks/ directory.",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config()

    project_root = Path(config["project"]["root"])
    vector_db_dir = project_root / config["storage"]["vector_db"]
    logs_dir = project_root / config["storage"]["logs"]
    logs_dir.mkdir(parents=True, exist_ok=True)

    benchmark_path = project_root / "benchmarks" / args.benchmark

    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark = yaml.safe_load(f)

    benchmark_cases = benchmark["benchmarks"]

    embed_cfg = config.get("embedding", {})
    rerank_cfg = config.get("reranking", {})

    results_out = []

    print("=" * 70)
    print("Retrieval Benchmark")
    print("=" * 70)

    for case in benchmark_cases:
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
            f"disp={evaluation['rerank_displacement']} "
            f"time={profile.total_seconds:.2f}s "
            f"acceptable@5={evaluation['acceptable_count_top5']} "
            f"bad@5={evaluation['bad_count_top5']}"
        )

    total_seconds = sum(r["profile"]["total_seconds"] for r in results_out)

    summary = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "benchmark": str(benchmark_path),
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
        "total_seconds": total_seconds,
        "average_seconds": total_seconds / len(results_out) if results_out else 0.0,
        "average_search_seconds": (
            sum(r["profile"]["search_seconds"] for r in results_out) / len(results_out)
            if results_out else 0.0
        ),
        "average_rerank_seconds": (
            sum(r["profile"]["rerank_seconds"] for r in results_out) / len(results_out)
            if results_out else 0.0
        ),
        "reranker_helped": sum(
            1 for r in results_out
            if r["evaluation"].get("reranker_helped")
        ),
        "reranker_hurt": sum(
            1 for r in results_out
            if r["evaluation"].get("reranker_hurt")
        ),
        "reranker_no_change": sum(
            1 for r in results_out
            if not r["evaluation"].get("reranker_helped")
            and not r["evaluation"].get("reranker_hurt")
        ),
        "faiss_only_top5_hits": sum(
            1 for r in results_out
            if (
                r["evaluation"]["stage_ranks"].get("raw_rank") is not None
                and r["evaluation"]["stage_ranks"].get("raw_rank") <= 5
            )
        ),
        "reranked_top5_hits": sum(
            1 for r in results_out
            if (
                r["evaluation"]["stage_ranks"].get("reranked_rank") is not None
                and r["evaluation"]["stage_ranks"].get("reranked_rank") <= 5
            )
        ),
    }

    category_summary = summarize_by_category(results_out)

    output = {
        "summary": summary,
        "category_summary": category_summary,
        "results": results_out,
    }

    outpath = logs_dir / f"retrieval_benchmark_{datetime.now():%Y%m%d_%H%M%S}.json"

    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print()
    print("-" * 70)
    print("Category Summary")
    print("-" * 70)

    for category in sorted(category_summary):
        stats = category_summary[category]
        average_time = (
            stats["total_seconds"] / stats["cases"]
            if stats["cases"] else 0.0
        )

        print(
            f"{category:16} "
            f"cases={stats['cases']:2d} "
            f"top1={stats['top1']:2d} "
            f"top5={stats['top5']:2d} "
            f"acceptable={stats['acceptable']:2d} "
            f"bad@5={stats['bad']:2d} "
            f"helped={stats['reranker_helped']:2d} "
            f"hurt={stats['reranker_hurt']:2d} "
            f"same={stats['reranker_no_change']:2d} "
            f"avg_time={average_time:.2f}s"
        )

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

    print()
    print("-" * 70)
    print("Reranker Analysis")
    print("-" * 70)
    print(f"Helped required rank : {summary['reranker_helped']}")
    print(f"Hurt required rank   : {summary['reranker_hurt']}")
    print(f"No change            : {summary['reranker_no_change']}")
    print(f"FAISS-only Top-5     : {summary['faiss_only_top5_hits']}")
    print(f"Reranked Top-5       : {summary['reranked_top5_hits']}")

    print(f"Log file            : {outpath}")


if __name__ == "__main__":
    main()
