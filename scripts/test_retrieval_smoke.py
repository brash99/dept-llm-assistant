from pathlib import Path

import pytest

from app.retrieval_smoke import (
    SmokeCaseResult,
    aggregate_passed,
    evaluate_smoke_case,
    load_smoke_test_config,
)
from scripts.report_vector_db_inventory import build_inventory


class RetrievalResult:
    def __init__(
        self,
        *,
        score,
        chunk_id,
        knowledge_object_id,
        object_type,
        chunk_index,
        text,
        citation,
        metadata,
    ):
        self.score = score
        self.chunk_id = chunk_id
        self.knowledge_object_id = knowledge_object_id
        self.object_type = object_type
        self.chunk_index = chunk_index
        self.text = text
        self.citation = citation
        self.metadata = metadata


def _result(
    text,
    *,
    object_type="document",
    semantic_space="institutional_evidence",
    title="Source",
    path="sources/source.pdf",
    score=0.8,
):
    return RetrievalResult(
        score=score,
        chunk_id=f"chunk-{title}-{score}",
        knowledge_object_id=f"object-{title}",
        object_type=object_type,
        chunk_index=0,
        text=text,
        citation={"title": title, "relative_path": path},
        metadata={"semantic_space": semantic_space},
    )


def test_expectation_evaluator_matches_synthetic_retrieval_results():
    case = {
        "id": "catalog",
        "query": "Communication faculty",
        "expectations": {
            "expected_terms_all": ["Communication", "2021-22"],
            "expected_object_types_any": ["department_faculty_roster_observation"],
            "expected_semantic_spaces_any": ["institutional_academics"],
            "expected_source_path_terms_any": ["catalog"],
            "expected_title_terms_any": ["roster"],
            "minimum_matching_results": 1,
            "maximum_rank_for_match": 2,
        },
    }
    results = [
        _result("unrelated"),
        _result(
            "Department of Communication faculty roster for 2021-22",
            object_type="department_faculty_roster_observation",
            semantic_space="institutional_academics",
            title="Faculty roster: Communication",
            path="data/acquisition/catalogs/2021-22.pdf",
        ),
    ]
    evaluated = evaluate_smoke_case(case, results)
    assert evaluated.passed, evaluated.failed_expectations
    assert evaluated.matching_result_ranks == [2]
    assert evaluated.result_summaries[1]["object_type"] == (
        "department_faculty_roster_observation"
    )


def test_weak_partial_match_does_not_satisfy_combined_expectations():
    case = {
        "id": "faculty",
        "query": "Edward Brash",
        "expectations": {
            "expected_terms_all": ["Edward", "Brash"],
            "expected_object_types_any": ["faculty_observation"],
            "minimum_matching_results": 1,
        },
    }
    results = [
        _result("Edward Brash", object_type="document"),
        _result("Different person", object_type="faculty_observation"),
    ]
    evaluated = evaluate_smoke_case(case, results)
    assert not evaluated.passed
    assert evaluated.matching_result_ranks == []
    assert "observed 0" in evaluated.failed_expectations[0]


def test_smoke_configuration_parses_and_rejects_unknown_expectations(tmp_path):
    repository_config = load_smoke_test_config("config/retrieval_smoke_tests.yaml")
    assert len(repository_config["cases"]) >= 9

    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(
        "cases:\n  - id: bad\n    query: query\n    expectations:\n      invented: true\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsupported expectations"):
        load_smoke_test_config(invalid)


def test_pass_aggregation_requires_cases_and_all_passed():
    passing = SmokeCaseResult("a", "q", True)
    failing = SmokeCaseResult("b", "q", False)
    assert aggregate_passed([passing])
    assert not aggregate_passed([passing, failing])
    assert not aggregate_passed([])


def test_inventory_uses_available_metadata_without_models():
    records = [
        {
            "object_type": "catalog_observation",
            "metadata": {
                "semantic_space": "institutional_catalog",
                "catalog_year": "2025-26",
                "source_type": "institutional_academic_catalog",
            },
            "citation": {"relative_path": "catalogs/2025-26.pdf"},
        },
        {
            "object_type": "document",
            "metadata": {
                "semantic_space": "institutional_evidence",
                "evidence_role": "External Standard",
                "issuing_authority": "Example Authority",
            },
            "citation": {"relative_path": "external/example.pdf"},
        },
    ]
    inventory = build_inventory(records)
    assert inventory["total_records"] == 2
    assert inventory["catalog_year"] == {"2025-26": 1}
    assert inventory["evidence_role"] == {"External Standard": 1}
    assert inventory["source_family"] == {
        "Example Authority": 1,
        "institutional_academic_catalog": 1,
    }
