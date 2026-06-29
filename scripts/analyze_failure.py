
import argparse
from pathlib import Path
import yaml

from app.config import load_config
from app.retrieval import retrieve

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--case", required=True)
    args = parser.parse_args()

    cfg = load_config()
    bench_path = Path(cfg["project"]["root"]) / "benchmarks" / args.benchmark
    benchmark = yaml.safe_load(bench_path.read_text())

    case = next(c for c in benchmark["cases"] if c["id"] == args.case)

    print("="*70)
    print("Benchmark Case")
    print("="*70)
    print(case["question"])
    print()

    results, report = retrieve(
        query=case["question"],
        top_k=5,
        fetch_k=50,
        return_diagnostics=True,
    )

    for stage in ("raw_candidates","deduped_candidates","reranked_candidates","final_results"):
        print("="*70)
        print(stage)
        print("="*70)
        for i, r in enumerate(report.get(stage, []), 1):
            print(f"{i}. {r.metadata.get('relative_path')} score={r.score:.4f}")
            print(r.text[:300].replace("\n"," "))
            print()

if __name__ == "__main__":
    main()
