from pathlib import Path

from app.config import load_config
from app.evidence import EvidenceClass, make_evidence
from app.observatory.decision_readiness.evaluators import (
    FacilitiesEvaluator,
)
from app.observatory.evidence_fitness import (
    EvidenceFitnessService,
)
from app.retrieval import retrieve


QUESTION = "Should CNU start a mechanical engineering major?"


def resolve_vector_db_path(config: dict) -> Path:
    project_root = Path(
        config.get("project", {}).get("root", ".")
    )

    vector_db = Path(config["storage"]["vector_db"])

    if vector_db.is_absolute():
        return vector_db

    return project_root / vector_db


def main() -> None:
    config = load_config()

    embedding = config.get("embedding", {})
    reranking = config.get("reranking", {})
    retrieval_config = config.get("retrieval", {})

    results, _, _ = retrieve(
        query=QUESTION,
        vector_db_dir=resolve_vector_db_path(config),
        model_name=embedding.get(
            "model",
            "BAAI/bge-base-en-v1.5",
        ),
        device=embedding.get(
            "device",
            "cuda",
        ),
        top_k=12,
        fetch_k=int(
            retrieval_config.get("fetch_k", 200)
        ),
        dedupe_by="relative_path",
        rerank=reranking.get("enabled", False),
        reranker_model=reranking.get("model"),
        reranker_device=reranking.get(
            "device",
            "cuda",
        ),
        min_rerank_score=reranking.get(
            "min_score"
        ),
        constitutional_top_k=int(
            retrieval_config.get(
                "constitutional_top_k",
                2,
            )
        ),
        empirical_top_k=int(
            retrieval_config.get(
                "empirical_top_k",
                10,
            )
        ),
    )

    evidence_items = make_evidence(results)

    empirical_items = [
        item
        for item in evidence_items
        if item.evidence_class
        != EvidenceClass.CONSTITUTIONAL
    ]

    legacy = EvidenceFitnessService.evaluate(
        QUESTION,
        evidence_items,
    )

    framework = FacilitiesEvaluator.evaluate(
        empirical_items
    )

    legacy_support = legacy.topic_support[
        "Facilities"
    ]

    legacy_score = round(
        100.0 * legacy_support["score"],
        1,
    )

    print("=" * 72)
    print("Facilities migration comparison")
    print("=" * 72)

    print()
    print("Legacy EvidenceFitnessService")
    print("  Status   :", legacy.topic_grades["Facilities"])
    print("  Score    :", legacy_score)
    print(
        "  Sources  :",
        legacy_support["sources"],
    )
    print(
        "  Keywords :",
        legacy_support["keywords"],
    )

    print()
    print("Decision Readiness evaluator")
    print("  Status   :", framework.status)
    print("  Score    :", framework.score)
    print(
        "  Sources  :",
        framework.supporting_sources,
    )
    print(
        "  Keywords :",
        framework.keyword_breadth,
    )
    print(
        "  Matches  :",
        ", ".join(framework.matched_keywords),
    )

    print()
    print("Supporting source titles:")

    for title in framework.source_titles:
        print(f"  - {title}")

    assert framework.status == legacy.topic_grades[
        "Facilities"
    ]

    assert framework.score == legacy_score

    assert (
        framework.supporting_sources
        == legacy_support["sources"]
    )

    assert (
        framework.keyword_breadth
        == legacy_support["keywords"]
    )

    print()
    print("PASS: Facilities behavior is equivalent.")
    

if __name__ == "__main__":
    main()
