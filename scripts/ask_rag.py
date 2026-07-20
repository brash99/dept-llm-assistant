#!/usr/bin/env python3

from pathlib import Path
import argparse

from app.config import load_config


def main(answer_question_func=None):
    if answer_question_func is None:
        from app.rag import answer_question

        answer_question_func = answer_question

    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--fetch-k", type=int, default=None)
    parser.add_argument("--no-dedupe", action="store_true")
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Display retrieval counts and timing diagnostics.",
    )
    args = parser.parse_args()

    config = load_config()

    project_root = Path(config["project"]["root"])
    vector_db_dir = project_root / config["storage"]["vector_db"]

    embed_cfg = config.get("embedding", {})
    llm_cfg = config.get("llm", {})

    rerank_cfg = config.get("reranking", {})
    retrieval_cfg = config.get("retrieval", {})

    response = answer_question_func(
        query=args.query,
        vector_db_dir=vector_db_dir,
        model_name=embed_cfg.get("model", "BAAI/bge-small-en-v1.5"),
        embedding_device=embed_cfg.get("device", "cuda"),
        llm_base_url=llm_cfg["base_url"],
        llm_model=llm_cfg["model"],
        top_k=args.top_k,
        fetch_k=args.fetch_k,
        dedupe_by=None if args.no_dedupe else "text",
        rerank=rerank_cfg.get("enabled", False),
        reranker_model=rerank_cfg.get("model"),
        reranker_device=rerank_cfg.get("device", "cuda"),
        return_trace=args.diagnostics,
        max_per_document_family=retrieval_cfg.get(
            "max_per_document_family",
            2,
        ),
        max_per_evidence_role=retrieval_cfg.get("max_per_evidence_role", 4),
        evidence_role_relevance_margin=retrieval_cfg.get(
            "evidence_role_relevance_margin",
            0.5,
        ),
    )

    if args.diagnostics:
        answer, results, retrieval_report, trace, profile = response
    else:
        answer, results, profile = response
        retrieval_report = None
        trace = None

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

    if args.diagnostics:
        print("=" * 70)
        print("Retrieval Diagnostics")
        print("=" * 70)
        print(f"Raw candidates       : {retrieval_report.num_candidates}")
        print(f"After exact dedupe   : {retrieval_report.num_after_dedup}")
        print(f"After reranking      : {retrieval_report.num_after_rerank}")
        print(
            "After family diversity: "
            f"{retrieval_report.num_after_family_diversity}"
        )
        print(f"After threshold      : {retrieval_report.num_after_threshold}")
        print(f"Final results        : {retrieval_report.num_results}")
        print(f"Trace final results  : {len(trace.final_results)}")
        print(
            "Excluded by allocation: "
            f"{retrieval_report.num_removed_by_evidence_allocation}"
        )
        print(f"Excluded by role control: {retrieval_report.num_removed_by_role_allocation}")
        print(
            "Excluded for insufficient relevance: "
            f"{retrieval_report.num_removed_for_insufficient_relevance}"
        )
        print(f"Roles represented    : {', '.join(retrieval_report.evidence_roles_represented) or 'None'}")
        print(f"Role counts          : {retrieval_report.evidence_role_counts}")
        print(f"Expected roles       : {', '.join(retrieval_report.expected_evidence_roles) or 'Not configured'}")
        print(f"Missing roles        : {', '.join(retrieval_report.missing_evidence_roles) or 'None'}")
        print(f"Concentrated roles   : {', '.join(retrieval_report.concentrated_evidence_roles) or 'None'}")
        print(f"Role allocation changed baseline: {retrieval_report.role_aware_allocation_changed_order}")
        print()
        print("Retrieval Timing")
        print(f"Total            : {profile.total_seconds:.3f}s")
        print(f"Search           : {profile.search_seconds:.3f}s")
        print(f"Dedupe           : {profile.dedupe_seconds:.3f}s")
        print(f"Rerank           : {profile.rerank_seconds:.3f}s")
        print(f"Family diversity : {profile.family_diversity_seconds:.3f}s")
        print(f"Threshold        : {profile.threshold_seconds:.3f}s")
        print()
        print("Final Evidence Selection")
        for result in trace.final_results:
            citation = result.citation or {}
            metadata = result.metadata or {}
            authority = (
                metadata.get("issuing_authority")
                or citation.get("source_organization")
                or metadata.get("source_organization")
                or "Unknown"
            )
            print(f"[{metadata.get('final_evidence_rank')}] {citation.get('title')}")
            print(f"  Path: {citation.get('relative_path')}")
            print(f"  Object type: {result.object_type}")
            print(f"  Authority: {authority}")
            print(f"  FAISS score: {metadata.get('faiss_score', result.score)}")
            print(f"  Reranker score: {metadata.get('rerank_score')}")
            print(f"  Document family: {metadata.get('document_family_key')}")
            print(f"  Evidence role: {metadata.get('evidence_role')}")
            print(f"  Derived role: {metadata.get('derived_evidence_role')}")
            print(f"  Role source: {metadata.get('evidence_role_source')}")
            print(f"  Role confidence: {metadata.get('evidence_role_confidence')}")
            print(
                "  Added role coverage: "
                f"{metadata.get('evidence_role_added_new_coverage', False)}"
            )
            print(
                "  Role fallback selection: "
                f"{metadata.get('evidence_role_fallback_selection', False)}"
            )
            print(f"  Reason selected: {metadata.get('evidence_selection_reason')}")
            print(
                "  Constitutional fallback: "
                f"{metadata.get('constitutional_fallback', False)}"
            )

        excluded = (
            list(trace.family_removed_candidates)
            + list(trace.role_removed_candidates)
            + list(trace.insufficient_relevance_candidates)
            + list(trace.allocation_removed_candidates)
        )
        if excluded:
            print()
            print("Excluded Candidates")
            for result in excluded:
                citation = result.citation or {}
                print(f"- {citation.get('title')}: "
                      f"{result.metadata.get('evidence_exclusion_reason')}")


if __name__ == "__main__":
    main()
