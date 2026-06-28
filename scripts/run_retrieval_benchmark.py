from pathlib import Path
from datetime import datetime
import json
import yaml

from app.config import load_config
from app.retrieval import retrieve


def contains_any(text, needles):
    if not needles:
        return False

    text = text.lower()
    return any(needle.lower() in text for needle in needles)


def evaluate_case(case, results):
    expected_sources = case.get("expected_sources", [])
    expected_title_contains = case.get("expected_title_contains", [])
    expected_text_contains = case.get("expected_text_contains", [])
    avoid_sources = case.get("avoid_sources", [])

    expected_rank = None
    avoid_hits = []

    for i, result in enumerate(results, start=1):
        citation = result.citation
        path = citation.get("relative_path", "")
        title = citation.get("title", "")
        text = result.text or ""

        source_hit = path in expected_sources
        title_hit = contains_any(title, expected_title_contains)
        text_hit = all(
            needle.lower() in text.lower()
            for needle in expected_text_contains
        ) if expected_text_contains else False

        if source_hit or title_hit or text_hit:
            if expected_rank is None:
                expected_rank = i

        if path in avoid_sources:
            avoid_hits.append(path)

    return {
        "top1_hit": expected_rank == 1,
        "top5_hit": expected_rank is not None and expected_rank <= 5,
        "expected_rank": expected_rank,
        "avoid_hits": avoid_hits,
        "num_avoid_hits": len(avoid_hits),
    }


def main():
    config = load_config()

    project_root = Path(config["project"]["root"])
    vector_db_dir = project_root / config["storage"]["vector_db"]
    logs_dir = project_root / config["storage"]["logs"]
    logs_dir.mkdir(parents=True, exist_ok=True)

    benchmark_path = project_root / "benchmarks" / "retrieval_benchmark.yaml"

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

        final_results, report, trace = retrieve(
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

        evaluation = evaluate_case(case, final_results)

        row = {
            "id": case["id"],
            "question": query,
            "evaluation": evaluation,
            "final_sources": [
                {
                    "rank": i,
                    "title": r.citation.get("title"),
                    "relative_path": r.citation.get("relative_path"),
                    "score": r.score,
                    "faiss_score": r.metadata.get("faiss_score"),
                    "rerank_score": r.metadata.get("rerank_score"),
                }
                for i, r in enumerate(final_results, start=1)
            ],
            "report": report.__dict__,
        }

        results_out.append(row)

        status = "PASS" if evaluation["top5_hit"] else "FAIL"
        rank = evaluation["expected_rank"]

        print(f"{status:4} {case['id']:30} rank={rank}")

    summary = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "num_cases": len(results_out),
        "top1_hits": sum(1 for r in results_out if r["evaluation"]["top1_hit"]),
        "top5_hits": sum(1 for r in results_out if r["evaluation"]["top5_hit"]),
        "avoid_hits": sum(r["evaluation"]["num_avoid_hits"] for r in results_out),
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
    print(f"Cases      : {summary['num_cases']}")
    print(f"Top-1 hits : {summary['top1_hits']}")
    print(f"Top-5 hits : {summary['top5_hits']}")
    print(f"Avoid hits : {summary['avoid_hits']}")
    print(f"Log file   : {outpath}")


if __name__ == "__main__":
    main()
