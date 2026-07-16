from pathlib import Path

from app.config import load_config
from app.evidence import EvidenceClass, make_evidence
from app.observatory.decision_readiness.registry import (
    registry,
)
from app.observatory.evidence_fitness import (
    EvidenceFitnessService,
)
from app.retrieval import retrieve


QUESTION = "Should CNU start a mechanical engineering major?"


def resolve_project_path(
    config: dict,
    value: str,
) -> Path:
    path = Path(value)

    if path.is_absolute():
        return path

    project_root = Path(
        config.get("project", {}).get(
            "root",
            ".",
        )
    )

    return project_root / path


def main() -> None:
    config = load_config()

    embedding = config.get("embedding", {})
    reranking = config.get("reranking", {})
    retrieval_config = config.get(
        "retrieval",
        {},
    )

    results, _, _ = retrieve(
        query=QUESTION,
        vector_db_dir=resolve_project_path(
            config,
            config["storage"]["vector_db"],
        ),
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
            retrieval_config.get(
                "fetch_k",
                200,
            )
        ),
        dedupe_by="relative_path",
        rerank=reranking.get(
            "enabled",
            False,
        ),
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

    evaluators = registry.get(
        "academic_program"
    )

    assert evaluators, (
        "No academic_program evaluators registered."
    )

    failures = []

    print("=" * 96)
    print("Academic Program evaluator migration")
    print("=" * 96)

    for evaluator in evaluators:
        framework = evaluator.evaluate(
            empirical_items
        )

        topic = evaluator.spec.name

        legacy_grade = legacy.topic_grades[
            topic
        ]

        legacy_support = legacy.topic_support[
            topic
        ]

        legacy_score = round(
            100.0 * legacy_support["score"],
            1,
        )

        print()
        print(topic)
        print("-" * len(topic))
        print(
            f"Legacy    : "
            f"{legacy_grade:8} "
            f"score={legacy_score:5.1f} "
            f"sources={legacy_support['sources']:2} "
            f"keywords={legacy_support['keywords']:2}"
        )
        print(
            f"Framework : "
            f"{framework.status:8} "
            f"score={framework.score:5.1f} "
            f"sources={framework.supporting_sources:2} "
            f"keywords={framework.keyword_breadth:2}"
        )

        comparisons = {
            "status": (
                framework.status,
                legacy_grade,
            ),
            "score": (
                framework.score,
                legacy_score,
            ),
            "sources": (
                framework.supporting_sources,
                legacy_support["sources"],
            ),
            "keywords": (
                framework.keyword_breadth,
                legacy_support["keywords"],
            ),
        }

        for field, (
            framework_value,
            legacy_value,
        ) in comparisons.items():
            if framework_value != legacy_value:
                failures.append(
                    (
                        topic,
                        field,
                        framework_value,
                        legacy_value,
                    )
                )

    print()
    print("=" * 96)

    if failures:
        print("FAILURES")

        for (
            topic,
            field,
            framework_value,
            legacy_value,
        ) in failures:
            print(
                f"{topic} / {field}: "
                f"framework={framework_value!r}, "
                f"legacy={legacy_value!r}"
            )

        raise SystemExit(1)

    print(
        "PASS: all Academic Program evaluators "
        "are behaviorally equivalent."
    )


if __name__ == "__main__":
    main()
