"""Deterministic analysis over factual schedule Knowledge Objects."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from app.knowledge import load_knowledge_object
from app.source_presentation import repository_relative_path


INSTRUCTOR_TYPE_FULL_TIME = "Full Time"
INSTRUCTOR_TYPE_ADJUNCT = "Adjunct"
INSTRUCTOR_TYPE_UNRESOLVED_CONFLICT = "Unresolved Conflict"
INSTRUCTOR_TYPE_MISSING_INSTRUCTOR = "Missing Instructor"
INSTRUCTOR_TYPE_UNKNOWN = "Unknown Instructor Type"

_CATEGORY_ORDER = (
    INSTRUCTOR_TYPE_FULL_TIME,
    INSTRUCTOR_TYPE_ADJUNCT,
    INSTRUCTOR_TYPE_UNRESOLVED_CONFLICT,
    INSTRUCTOR_TYPE_MISSING_INSTRUCTOR,
    INSTRUCTOR_TYPE_UNKNOWN,
)


class ScheduleAnalysisMetric(str, Enum):
    DISTINCT_INSTRUCTORS = "distinct_instructors"
    COURSE_OFFERINGS = "course_offerings"


@dataclass(frozen=True)
class ScheduleAggregationGroup:
    academic_term: str
    instructor_type: str
    value: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduleAggregationResult:
    request: str
    metric: str
    grouping: tuple[str, ...]
    totals: Mapping[str, int]
    grouped_results: tuple[ScheduleAggregationGroup, ...]
    uncertainty_summary: Mapping[str, int]
    provenance: Mapping[str, Any]
    source_object_count: int
    included_object_count: int
    excluded_object_count: int
    deterministic_result_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "metric": self.metric,
            "grouping": list(self.grouping),
            "totals": dict(self.totals),
            "grouped_results": [item.to_dict() for item in self.grouped_results],
            "uncertainty_summary": dict(self.uncertainty_summary),
            "provenance": dict(self.provenance),
            "source_object_count": self.source_object_count,
            "included_object_count": self.included_object_count,
            "excluded_object_count": self.excluded_object_count,
            "deterministic_result_fingerprint": self.deterministic_result_fingerprint,
        }


def _value(observation: Any, name: str, default: Any = None) -> Any:
    if isinstance(observation, Mapping):
        return observation.get(name, default)
    return getattr(observation, name, default)


def _canonical_instructor(value: str) -> str:
    text = " ".join(value.casefold().split())
    if "," in text:
        last, first = (" ".join(part.split()) for part in text.split(",", 1))
        if first and last:
            text = f"{first} {last}"
    return re.sub(r"\s+", " ", text).strip()


def _instructor_category(observation: Any) -> str:
    instructor = str(
        _value(observation, "instructor_raw")
        or _value(observation, "instructor_name")
        or ""
    ).strip()
    if not instructor:
        return INSTRUCTOR_TYPE_MISSING_INSTRUCTOR
    assertion = _value(observation, "instructor_type", {}) or {}
    resolution = assertion.get("resolution") or {}
    if assertion.get("conflicting") and not resolution.get("resolved"):
        return INSTRUCTOR_TYPE_UNRESOLVED_CONFLICT
    normalized = assertion.get("normalized_value")
    if normalized == "full_time":
        return INSTRUCTOR_TYPE_FULL_TIME
    if normalized == "adjunct":
        return INSTRUCTOR_TYPE_ADJUNCT
    return INSTRUCTOR_TYPE_UNKNOWN


def _metric_from_request(request: str) -> ScheduleAnalysisMetric:
    text = " ".join(request.casefold().split())
    if re.search(r"\b(?:distinct|unique) instructors?\b", text):
        return ScheduleAnalysisMetric.DISTINCT_INSTRUCTORS
    if re.search(r"\binstructors?\b", text) and not re.search(
        r"\b(?:sections?|course offerings?)\b", text
    ):
        return ScheduleAnalysisMetric.DISTINCT_INSTRUCTORS
    if re.search(r"\b(?:sections?|course offerings?)\b", text):
        return ScheduleAnalysisMetric.COURSE_OFFERINGS
    raise ValueError("The request does not identify a supported schedule metric")


class ScheduleAnalysisService:
    """Compute full-corpus schedule aggregates without vector retrieval."""

    def __init__(self, schedule_root: Path | str = "storage/normalized/schedules"):
        self.schedule_root = Path(schedule_root)

    def load_observations(self) -> tuple[Any, ...]:
        if not self.schedule_root.is_dir():
            raise FileNotFoundError(
                f"Schedule Knowledge Object root does not exist: {self.schedule_root}"
            )
        observations = []
        for path in sorted(self.schedule_root.rglob("*.json")):
            observation = load_knowledge_object(path)
            if observation.object_type != "course_offering_observation":
                raise ValueError(f"Unsupported object in schedule root: {path}")
            observations.append(observation)
        return tuple(observations)

    def analyze(
        self,
        request: str,
        *,
        metric: ScheduleAnalysisMetric | str | None = None,
    ) -> ScheduleAggregationResult:
        return self.analyze_observations(
            request,
            self.load_observations(),
            metric=metric,
            source_root=self.schedule_root,
        )

    def analyze_observations(
        self,
        request: str,
        observations: Iterable[Any],
        *,
        metric: ScheduleAnalysisMetric | str | None = None,
        source_root: Path | str | None = None,
    ) -> ScheduleAggregationResult:
        selected_metric = (
            _metric_from_request(request)
            if metric is None
            else ScheduleAnalysisMetric(metric)
        )
        values = tuple(observations)
        supported = tuple(
            item for item in values
            if _value(item, "object_type") == "course_offering_observation"
        )
        unsupported_count = len(values) - len(supported)
        grouped_sets: dict[tuple[str, str], set[str]] = defaultdict(set)
        grouped_counts: Counter[tuple[str, str]] = Counter()
        uncertainty = Counter(
            source_conflicted_observations=0,
            unresolved_conflict_observations=0,
            repaired_instructor_type_observations=0,
            missing_instructor_observations=0,
            unknown_instructor_type_observations=0,
        )
        included = 0
        excluded = unsupported_count
        object_ids = []

        for observation in supported:
            object_ids.append(str(_value(observation, "id")))
            term = str(_value(observation, "academic_term") or "").strip()
            if not term:
                excluded += 1
                continue
            category = _instructor_category(observation)
            assertion = _value(observation, "instructor_type", {}) or {}
            resolution = assertion.get("resolution") or {}
            if assertion.get("conflicting"):
                uncertainty["source_conflicted_observations"] += 1
            if category == INSTRUCTOR_TYPE_UNRESOLVED_CONFLICT:
                uncertainty["unresolved_conflict_observations"] += 1
            if assertion.get("conflicting") and resolution.get("resolved"):
                uncertainty["repaired_instructor_type_observations"] += 1
            if category == INSTRUCTOR_TYPE_MISSING_INSTRUCTOR:
                uncertainty["missing_instructor_observations"] += 1
            if category == INSTRUCTOR_TYPE_UNKNOWN:
                uncertainty["unknown_instructor_type_observations"] += 1

            if selected_metric == ScheduleAnalysisMetric.COURSE_OFFERINGS:
                grouped_counts[(term, category)] += 1
                included += 1
                continue

            instructor = str(
                _value(observation, "instructor_raw")
                or _value(observation, "instructor_name")
                or ""
            ).strip()
            if not instructor:
                excluded += 1
                continue
            grouped_sets[(term, category)].add(_canonical_instructor(instructor))
            included += 1

        if selected_metric == ScheduleAnalysisMetric.DISTINCT_INSTRUCTORS:
            grouped_counts = Counter(
                {key: len(instructors) for key, instructors in grouped_sets.items()}
            )

        category_rank = {name: index for index, name in enumerate(_CATEGORY_ORDER)}
        groups = tuple(
            ScheduleAggregationGroup(term, category, value)
            for (term, category), value in sorted(
                grouped_counts.items(),
                key=lambda item: (
                    item[0][0], category_rank.get(item[0][1], len(category_rank))
                ),
            )
        )
        totals_counter: Counter[str] = Counter()
        for group in groups:
            totals_counter[group.instructor_type] += group.value
        totals = {
            category: totals_counter.get(category, 0) for category in _CATEGORY_ORDER
        }
        source_path = repository_relative_path(
            source_root or self.schedule_root
        )
        provenance = {
            "source_root": source_path,
            "source_object_type": "course_offering_observation",
            "calculation_method": "deterministic_full_corpus_aggregation",
            "source_object_ids_fingerprint": _fingerprint(sorted(object_ids)),
        }
        payload = {
            "request": request,
            "metric": selected_metric.value,
            "grouping": ["academic_term", "normalized_instructor_type"],
            "totals": totals,
            "grouped_results": [group.to_dict() for group in groups],
            "uncertainty_summary": dict(uncertainty),
            "provenance": provenance,
            "source_object_count": len(values),
            "included_object_count": included,
            "excluded_object_count": excluded,
        }
        return ScheduleAggregationResult(
            request=request,
            metric=selected_metric.value,
            grouping=("academic_term", "normalized_instructor_type"),
            totals=totals,
            grouped_results=groups,
            uncertainty_summary=dict(uncertainty),
            provenance=provenance,
            source_object_count=len(values),
            included_object_count=included,
            excluded_object_count=excluded,
            deterministic_result_fingerprint=_fingerprint_payload(payload),
        )


def _fingerprint(values: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _fingerprint_payload(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "INSTRUCTOR_TYPE_ADJUNCT",
    "INSTRUCTOR_TYPE_FULL_TIME",
    "INSTRUCTOR_TYPE_MISSING_INSTRUCTOR",
    "INSTRUCTOR_TYPE_UNKNOWN",
    "INSTRUCTOR_TYPE_UNRESOLVED_CONFLICT",
    "ScheduleAggregationGroup",
    "ScheduleAggregationResult",
    "ScheduleAnalysisMetric",
    "ScheduleAnalysisService",
]
