"""Declarative expectation evaluation for retrieval smoke tests."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from app.vector_index import RetrievalResult
else:
    RetrievalResult = Any


SUPPORTED_EXPECTATIONS = {
    "expected_terms_any",
    "expected_terms_all",
    "expected_object_types_any",
    "expected_semantic_spaces_any",
    "expected_source_path_terms_any",
    "expected_title_terms_any",
    "minimum_matching_results",
    "maximum_rank_for_match",
}


@dataclass
class SmokeCaseResult:
    case_id: str
    query: str
    passed: bool
    matched_expectations: List[str] = field(default_factory=list)
    failed_expectations: List[str] = field(default_factory=list)
    matching_result_ranks: List[int] = field(default_factory=list)
    result_summaries: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_smoke_test_config(path: Path | str) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("Smoke-test configuration must contain a cases list")
    seen = set()
    for index, case in enumerate(data["cases"]):
        if not isinstance(case, dict):
            raise ValueError(f"Smoke-test case {index} must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"Smoke-test case {index} requires a nonempty id")
        if case_id in seen:
            raise ValueError(f"Duplicate smoke-test case id: {case_id}")
        seen.add(case_id)
        if not isinstance(case.get("query"), str) or not case["query"].strip():
            raise ValueError(f"Smoke-test case {case_id} requires a nonempty query")
        expectations = case.get("expectations", {})
        if not isinstance(expectations, dict):
            raise ValueError(f"Smoke-test case {case_id} expectations must be an object")
        unsupported = set(expectations) - SUPPORTED_EXPECTATIONS
        if unsupported:
            raise ValueError(
                f"Smoke-test case {case_id} has unsupported expectations: "
                + ", ".join(sorted(unsupported))
            )
    return data


def _contains_any(value: str, terms: Iterable[str]) -> bool:
    lowered = value.casefold()
    return any(str(term).casefold() in lowered for term in terms)


def _contains_all(value: str, terms: Iterable[str]) -> bool:
    lowered = value.casefold()
    return all(str(term).casefold() in lowered for term in terms)


def _result_fields(result: RetrievalResult) -> Dict[str, str]:
    citation = result.citation or {}
    metadata = result.metadata or {}
    title = str(citation.get("title") or metadata.get("document_title") or "")
    path = str(citation.get("relative_path") or citation.get("source_path") or "")
    return {
        "text": str(result.text or ""),
        "title": title,
        "path": path,
        "object_type": str(result.object_type or ""),
        "semantic_space": str(metadata.get("semantic_space") or ""),
        "combined": "\n".join((str(result.text or ""), title, path)),
    }


def _matches_result(result: RetrievalResult, expectations: Mapping[str, Any]) -> bool:
    fields = _result_fields(result)
    checks = []
    if expectations.get("expected_terms_any"):
        checks.append(_contains_any(fields["combined"], expectations["expected_terms_any"]))
    if expectations.get("expected_terms_all"):
        checks.append(_contains_all(fields["combined"], expectations["expected_terms_all"]))
    if expectations.get("expected_object_types_any"):
        checks.append(
            fields["object_type"] in set(map(str, expectations["expected_object_types_any"]))
        )
    if expectations.get("expected_semantic_spaces_any"):
        checks.append(
            fields["semantic_space"]
            in set(map(str, expectations["expected_semantic_spaces_any"]))
        )
    if expectations.get("expected_source_path_terms_any"):
        checks.append(_contains_any(fields["path"], expectations["expected_source_path_terms_any"]))
    if expectations.get("expected_title_terms_any"):
        checks.append(_contains_any(fields["title"], expectations["expected_title_terms_any"]))
    return all(checks) if checks else True


def summarize_result(result: RetrievalResult, rank: int) -> Dict[str, Any]:
    fields = _result_fields(result)
    return {
        "rank": rank,
        "score": float(result.score),
        "chunk_id": result.chunk_id,
        "title": fields["title"],
        "source_path": fields["path"],
        "object_type": fields["object_type"],
        "semantic_space": fields["semantic_space"],
        "evidence_role": (result.metadata or {}).get("evidence_role"),
        "constitutional_fallback": bool(
            (result.metadata or {}).get("constitutional_fallback")
        ),
    }


def evaluate_smoke_case(
    case: Mapping[str, Any],
    results: Sequence[RetrievalResult],
) -> SmokeCaseResult:
    expectations = dict(case.get("expectations") or {})
    ranks = [
        rank
        for rank, result in enumerate(results, start=1)
        if _matches_result(result, expectations)
    ]
    matched: List[str] = []
    failed: List[str] = []

    minimum = int(expectations.get("minimum_matching_results", 1))
    description = f"minimum_matching_results={minimum} (observed {len(ranks)})"
    (matched if len(ranks) >= minimum else failed).append(description)

    if "maximum_rank_for_match" in expectations:
        maximum_rank = int(expectations["maximum_rank_for_match"])
        observed = min(ranks) if ranks else None
        description = f"maximum_rank_for_match={maximum_rank} (observed {observed})"
        (matched if observed is not None and observed <= maximum_rank else failed).append(
            description
        )

    for key in sorted(
        set(expectations)
        - {"minimum_matching_results", "maximum_rank_for_match"}
    ):
        values = expectations[key]
        description = f"{key}={values!r}"
        # Individual expectations are reported separately for diagnosis.
        single = {key: values}
        satisfied = any(_matches_result(result, single) for result in results)
        (matched if satisfied else failed).append(description)

    return SmokeCaseResult(
        case_id=str(case["id"]),
        query=str(case["query"]),
        passed=not failed,
        matched_expectations=matched,
        failed_expectations=failed,
        matching_result_ranks=ranks,
        result_summaries=[
            summarize_result(result, rank)
            for rank, result in enumerate(results, start=1)
        ],
    )


def aggregate_passed(results: Sequence[SmokeCaseResult]) -> bool:
    return bool(results) and all(result.passed for result in results)


__all__ = [
    "SmokeCaseResult",
    "aggregate_passed",
    "evaluate_smoke_case",
    "load_smoke_test_config",
    "summarize_result",
]
