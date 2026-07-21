#!/usr/bin/env python3
"""Run declarative, LLM-free retrieval smoke tests against a built ISO index."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_config
from app.retrieval import retrieve
from app.retrieval_smoke import (
    SmokeCaseResult,
    aggregate_passed,
    evaluate_smoke_case,
    load_smoke_test_config,
)


def _default_vector_db(config: Dict[str, Any]) -> Path:
    return Path(config["project"]["root"]) / config["storage"]["vector_db"]


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vector-db", type=Path, default=None)
    parser.add_argument(
        "--config", type=Path, default=Path("config/retrieval_smoke_tests.yaml")
    )
    parser.add_argument("--device", default=None)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--fetch-k", type=int, default=None)
    rerank = parser.add_mutually_exclusive_group()
    rerank.add_argument("--rerank", action="store_true")
    rerank.add_argument("--no-rerank", action="store_true")
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def _quotas(case, defaults, top_k):
    constitutional = int(case.get(
        "constitutional_top_k", defaults.get("constitutional_top_k", 2)
    ))
    empirical = int(case.get("empirical_top_k", defaults.get("empirical_top_k", 10)))
    if top_k is None:
        return constitutional, empirical
    if constitutional and not empirical:
        return top_k, 0
    if empirical and not constitutional:
        return 0, top_k
    return min(constitutional, top_k), max(0, top_k - constitutional)


def main(argv=None) -> int:
    args = _parse_args(argv)
    settings = load_config()
    smoke_config = load_smoke_test_config(args.config)
    defaults = smoke_config.get("defaults") or {}
    cases = smoke_config["cases"]
    if args.case_ids:
        requested = set(args.case_ids)
        known = {case["id"] for case in cases}
        unknown = requested - known
        if unknown:
            print("Unknown case(s): " + ", ".join(sorted(unknown)), file=sys.stderr)
            return 2
        cases = [case for case in cases if case["id"] in requested]

    vector_db = args.vector_db or _default_vector_db(settings)
    embedding = settings.get("embedding", {})
    retrieval_config = settings.get("retrieval", {})
    reranking = settings.get("reranking", {})
    device = args.device or embedding.get("device", "cpu")
    rerank_enabled = bool(args.rerank and not args.no_rerank)
    case_results: List[SmokeCaseResult] = []
    case_reports = []

    for case in cases:
        constitutional_top_k, empirical_top_k = _quotas(case, defaults, args.top_k)
        fetch_k = int(args.fetch_k or case.get("fetch_k") or defaults.get("fetch_k", 100))
        try:
            results, report, trace, profile = retrieve(
                query=case["query"],
                vector_db_dir=vector_db,
                model_name=embedding.get("model", "BAAI/bge-base-en-v1.5"),
                device=device,
                top_k=constitutional_top_k + empirical_top_k,
                fetch_k=fetch_k,
                dedupe_by=case.get("dedupe_by", "text"),
                rerank=rerank_enabled,
                reranker_model=reranking.get("model") if rerank_enabled else None,
                reranker_device=args.device or reranking.get("device", device),
                min_rerank_score=(
                    reranking.get("min_score") if rerank_enabled else None
                ),
                return_trace=True,
                constitutional_top_k=constitutional_top_k,
                empirical_top_k=empirical_top_k,
                max_per_document_family=retrieval_config.get(
                    "max_per_document_family"
                ),
                decision_type=case.get("decision_type"),
                max_per_evidence_role=retrieval_config.get("max_per_evidence_role"),
                evidence_role_relevance_margin=retrieval_config.get(
                    "evidence_role_relevance_margin", 0.5
                ),
            )
            evaluated = evaluate_smoke_case(case, results)
            case_results.append(evaluated)
            case_reports.append(
                {
                    "case": evaluated.to_dict(),
                    "retrieval_report": asdict(report),
                    "timing": asdict(profile),
                    "trace_counts": {
                        "raw": len(trace.raw_candidates),
                        "deduped": len(trace.deduped_candidates),
                        "family_diversified": len(trace.family_diversified_candidates),
                        "thresholded": len(trace.thresholded_candidates),
                        "final": len(trace.final_results),
                    },
                }
            )
        except Exception as exc:
            evaluated = SmokeCaseResult(
                case_id=case["id"],
                query=case["query"],
                passed=False,
                failed_expectations=[
                    f"Retrieval execution failed: {type(exc).__name__}: {exc}"
                ],
            )
            case_results.append(evaluated)
            case_reports.append({"case": evaluated.to_dict()})

    passed = aggregate_passed(case_results)
    payload = {
        "passed": passed,
        "vector_db": str(vector_db),
        "reranking_enabled": rerank_enabled,
        "cases_run": len(case_results),
        "cases_passed": sum(result.passed for result in case_results),
        "cases_failed": sum(not result.passed for result in case_results),
        "results": case_reports,
    }
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"Retrieval smoke tests: {'PASS' if passed else 'FAIL'} "
            f"({payload['cases_passed']}/{payload['cases_run']} passed)"
        )
        print(f"Vector DB: {vector_db}")
        print(f"Embedding device: {device} | reranking: {rerank_enabled}")
        for item in case_reports:
            case_result = item["case"]
            print(f"\n[{'PASS' if case_result['passed'] else 'FAIL'}] {case_result['case_id']}")
            print(f"Query: {case_result['query']}")
            for failure in case_result["failed_expectations"]:
                print(f"  FAILED: {failure}")
            if args.verbose:
                for match in case_result["matched_expectations"]:
                    print(f"  matched: {match}")
            for result in case_result["result_summaries"][:5]:
                print(
                    f"  #{result['rank']} {result['score']:.4f} "
                    f"{result['object_type']} [{result['semantic_space'] or '<none>'}] "
                    f"{result['title'] or result['source_path']}"
                )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
