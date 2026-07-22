"""Deterministic full-corpus analysis over schedule Knowledge Objects."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from app.academic_terms import academic_term_order, academic_term_sort_key
from app.knowledge import load_knowledge_object
from app.reasoning.academic_unit_mapping import (
    AcademicUnitMappingService,
    AcademicUnitMappingStatus,
)
from app.source_presentation import repository_relative_path


ANALYSIS_ALGORITHM = "deterministic_schedule_aggregation"
ANALYSIS_VERSION = "2.0"
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
_RESOLVED_CATEGORIES = {INSTRUCTOR_TYPE_FULL_TIME, INSTRUCTOR_TYPE_ADJUNCT}
_ALLOWED_GROUPINGS = {
    "academic_term", "normalized_instructor_type", "subject", "academic_unit"
}


class ScheduleAnalysisMetric(str, Enum):
    DISTINCT_INSTRUCTORS = "distinct_instructors"
    COURSE_OFFERINGS = "course_offerings"
    RESOLVED_OFFERING_SHARE = "resolved_offering_share"
    ADJUNCT_OFFERING_SHARE = "adjunct_offering_share"
    FULL_TIME_OFFERING_SHARE = "full_time_offering_share"
    UNRESOLVED_OFFERING_SHARE = "unresolved_offering_share"

    @property
    def is_share(self) -> bool:
        return self.value.endswith("_share")


@dataclass(frozen=True)
class ScheduleAggregationGroup:
    academic_term: str = ""
    instructor_type: str = ""
    value: int | float | None = 0
    subject: str | None = None
    academic_unit_id: str | None = None
    academic_unit_name: str | None = None
    numerator: int | None = None
    denominator: int | None = None
    denominator_definition: str | None = None
    source_observation_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AcademicUnitMappingSummary:
    mapped_observation_count: int
    intentionally_grouped_observation_count: int
    unmapped_observation_count: int
    ambiguous_mapping_count: int
    unsupported_mapping_count: int
    mapped_subjects: tuple[str, ...]
    unmapped_subjects: tuple[str, ...]
    ambiguous_subjects: tuple[str, ...]

    @property
    def mapped_observations(self) -> int:
        return self.mapped_observation_count + self.intentionally_grouped_observation_count

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["mapped_observations"] = self.mapped_observations
        return value


@dataclass(frozen=True)
class ScheduleEvidenceFitness:
    total_schedule_observations: int
    observations_with_usable_subject: int
    mapped_observations: int
    unmapped_observations: int
    ambiguous_mappings: int
    observations_with_instructor_identity: int
    observations_with_resolved_instructor_type: int
    unresolved_conflict_rate: float
    missing_instructor_type_rate: float
    missing_instructor_rate: float
    identity_policy_limitations: tuple[str, ...]
    term_coverage: tuple[str, ...]
    unsupported_terms: tuple[str, ...]
    suitability: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["suitability"] = dict(self.suitability)
        return value


@dataclass(frozen=True)
class ScheduleAggregationResult:
    request: str
    metric: str
    grouping: tuple[str, ...]
    totals: Mapping[str, int | float | None]
    grouped_results: tuple[ScheduleAggregationGroup, ...]
    uncertainty_summary: Mapping[str, int]
    provenance: Mapping[str, Any]
    source_object_count: int
    included_object_count: int
    excluded_object_count: int
    deterministic_result_fingerprint: str
    mapping_coverage: AcademicUnitMappingSummary | None = None
    evidence_fitness: ScheduleEvidenceFitness | None = None
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "metric": self.metric,
            "grouping": list(self.grouping),
            "totals": dict(self.totals),
            "grouped_results": [item.to_dict() for item in self.grouped_results],
            "uncertainty_summary": dict(self.uncertainty_summary),
            "mapping_coverage": self.mapping_coverage.to_dict() if self.mapping_coverage else None,
            "evidence_fitness": self.evidence_fitness.to_dict() if self.evidence_fitness else None,
            "limitations": list(self.limitations),
            "provenance": dict(self.provenance),
            "source_object_count": self.source_object_count,
            "included_object_count": self.included_object_count,
            "excluded_object_count": self.excluded_object_count,
            "deterministic_result_fingerprint": self.deterministic_result_fingerprint,
        }


@dataclass(frozen=True)
class ScheduleTrendGroup:
    subject: str | None
    academic_unit_id: str | None
    academic_unit_name: str | None
    first_term: str
    last_term: str
    first_value: int | float | None
    last_value: int | float | None
    absolute_change: int | float | None
    percentage_point_change: float | None
    observation_count: int
    missing_term_warnings: tuple[str, ...]
    comparability_limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduleTrendResult:
    request: str
    metric: str
    grouping: tuple[str, ...]
    trends: tuple[ScheduleTrendGroup, ...]
    source_aggregation: ScheduleAggregationResult
    unsupported_terms: tuple[str, ...]
    deterministic_result_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "metric": self.metric,
            "grouping": list(self.grouping),
            "trends": [trend.to_dict() for trend in self.trends],
            "unsupported_terms": list(self.unsupported_terms),
            "source_aggregation": self.source_aggregation.to_dict(),
            "deterministic_result_fingerprint": self.deterministic_result_fingerprint,
        }


def _value(observation: Any, name: str, default: Any = None) -> Any:
    return observation.get(name, default) if isinstance(observation, Mapping) else getattr(observation, name, default)


def _canonical_instructor(value: str) -> str:
    text = " ".join(value.casefold().split())
    if "," in text:
        last, first = (" ".join(part.split()) for part in text.split(",", 1))
        if first and last:
            text = f"{first} {last}"
    return re.sub(r"\s+", " ", text).strip()


def _instructor_category(observation: Any) -> str:
    instructor = str(_value(observation, "instructor_raw") or _value(observation, "instructor_name") or "").strip()
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
    if "unresolved" in text and re.search(r"\b(?:share|percentage|rate)\b", text):
        return ScheduleAnalysisMetric.UNRESOLVED_OFFERING_SHARE
    if "adjunct" in text and re.search(r"\b(?:share|percentage|dependence|rate)\b", text):
        return ScheduleAnalysisMetric.ADJUNCT_OFFERING_SHARE
    if "full time" in text and re.search(r"\b(?:share|percentage|rate)\b", text):
        return ScheduleAnalysisMetric.FULL_TIME_OFFERING_SHARE
    if "resolved" in text and re.search(r"\b(?:share|percentage|rate)\b", text):
        return ScheduleAnalysisMetric.RESOLVED_OFFERING_SHARE
    if re.search(r"\b(?:distinct|unique) instructors?\b", text):
        return ScheduleAnalysisMetric.DISTINCT_INSTRUCTORS
    if re.search(r"\binstructors?\b", text) and not re.search(r"\b(?:sections?|course offerings?)\b", text):
        return ScheduleAnalysisMetric.DISTINCT_INSTRUCTORS
    if re.search(r"\b(?:sections?|course offerings?|offerings?)\b", text):
        return ScheduleAnalysisMetric.COURSE_OFFERINGS
    raise ValueError("The request does not identify a supported schedule metric")


def _default_grouping(metric: ScheduleAnalysisMetric) -> tuple[str, ...]:
    if metric.is_share:
        return ("academic_term",)
    return ("academic_term", "normalized_instructor_type")


class ScheduleAnalysisService:
    """Compute schedule aggregates directly from the complete normalized corpus."""

    def __init__(
        self,
        schedule_root: Path | str = "storage/normalized/schedules",
        *,
        mapping_service: AcademicUnitMappingService | None = None,
    ):
        self.schedule_root = Path(schedule_root)
        self.mapping_service = mapping_service or AcademicUnitMappingService()

    def load_observations(self) -> tuple[Any, ...]:
        if not self.schedule_root.is_dir():
            raise FileNotFoundError(f"Schedule Knowledge Object root does not exist: {self.schedule_root}")
        observations = []
        for path in sorted(self.schedule_root.rglob("*.json")):
            observation = load_knowledge_object(path)
            if observation.object_type != "course_offering_observation":
                raise ValueError(f"Unsupported object in schedule root: {path}")
            observations.append(observation)
        return tuple(observations)

    def analyze(self, request: str, **kwargs: Any) -> ScheduleAggregationResult:
        return self.analyze_observations(
            request, self.load_observations(), source_root=self.schedule_root, **kwargs
        )

    def analyze_observations(
        self,
        request: str,
        observations: Iterable[Any],
        *,
        metric: ScheduleAnalysisMetric | str | None = None,
        group_by: Sequence[str] | None = None,
        subject_filter: Sequence[str] | None = None,
        academic_unit_filter: Sequence[str] | None = None,
        term_filter: Sequence[str] | None = None,
        source_root: Path | str | None = None,
    ) -> ScheduleAggregationResult:
        selected_metric = _metric_from_request(request) if metric is None else ScheduleAnalysisMetric(metric)
        grouping = tuple(group_by or _default_grouping(selected_metric))
        unknown = set(grouping) - _ALLOWED_GROUPINGS
        if unknown:
            raise ValueError(f"Unsupported schedule grouping dimensions: {sorted(unknown)}")
        if selected_metric.is_share and "normalized_instructor_type" in grouping:
            raise ValueError("Share metrics cannot group by normalized_instructor_type")

        values = tuple(observations)
        supported = tuple(item for item in values if _value(item, "object_type") == "course_offering_observation")
        unsupported_count = len(values) - len(supported)
        subject_allowed = {value.strip().upper() for value in subject_filter or ()}
        unit_allowed = {value.strip() for value in academic_unit_filter or ()}
        term_allowed = {value.strip() for value in term_filter or ()}
        mapping_counts: Counter[str] = Counter()
        mapped_subjects: set[str] = set()
        unmapped_subjects: set[str] = set()
        ambiguous_subjects: set[str] = set()
        uncertainty = Counter(
            source_conflicted_observations=0,
            unresolved_conflict_observations=0,
            repaired_instructor_type_observations=0,
            missing_instructor_observations=0,
            unknown_instructor_type_observations=0,
        )
        records: list[dict[str, Any]] = []
        object_ids: list[str] = []
        excluded = unsupported_count

        for observation in supported:
            object_ids.append(str(_value(observation, "id") or ""))
            term = str(_value(observation, "academic_term") or "").strip()
            subject = str(_value(observation, "subject") or "").strip().upper()
            category = _instructor_category(observation)
            instructor = str(_value(observation, "instructor_raw") or _value(observation, "instructor_name") or "").strip()
            assertion = _value(observation, "instructor_type", {}) or {}
            resolution = assertion.get("resolution") or {}
            mapping = self.mapping_service.map_subject(subject)
            mapping_counts[mapping.status] += 1
            if mapping.status in {AcademicUnitMappingStatus.MAPPED.value, AcademicUnitMappingStatus.INTENTIONALLY_GROUPED.value}:
                mapped_subjects.add(subject)
            elif mapping.status == AcademicUnitMappingStatus.UNMAPPED.value:
                unmapped_subjects.add(subject)
            elif mapping.status == AcademicUnitMappingStatus.AMBIGUOUS.value:
                ambiguous_subjects.add(subject)

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

            if not term or (term_allowed and term not in term_allowed):
                excluded += 1
                continue
            if subject_allowed and subject not in subject_allowed:
                excluded += 1
                continue
            if "subject" in grouping and not subject:
                excluded += 1
                continue
            mapped = mapping.status in {AcademicUnitMappingStatus.MAPPED.value, AcademicUnitMappingStatus.INTENTIONALLY_GROUPED.value}
            if "academic_unit" in grouping and not mapped:
                excluded += 1
                continue
            if unit_allowed and (not mapped or mapping.academic_unit_id not in unit_allowed and mapping.academic_unit_name not in unit_allowed):
                excluded += 1
                continue
            if selected_metric == ScheduleAnalysisMetric.DISTINCT_INSTRUCTORS and not instructor:
                excluded += 1
                continue
            records.append({
                "id": str(_value(observation, "id") or ""),
                "academic_term": term,
                "subject": subject,
                "normalized_instructor_type": category,
                "instructor": _canonical_instructor(instructor) if instructor else "",
                "academic_unit_id": mapping.academic_unit_id,
                "academic_unit_name": mapping.academic_unit_name,
                "academic_unit": (mapping.academic_unit_id, mapping.academic_unit_name),
            })

        mapping_summary = AcademicUnitMappingSummary(
            mapped_observation_count=mapping_counts[AcademicUnitMappingStatus.MAPPED.value],
            intentionally_grouped_observation_count=mapping_counts[AcademicUnitMappingStatus.INTENTIONALLY_GROUPED.value],
            unmapped_observation_count=mapping_counts[AcademicUnitMappingStatus.UNMAPPED.value],
            ambiguous_mapping_count=mapping_counts[AcademicUnitMappingStatus.AMBIGUOUS.value],
            unsupported_mapping_count=mapping_counts[AcademicUnitMappingStatus.UNSUPPORTED.value],
            mapped_subjects=tuple(sorted(mapped_subjects)),
            unmapped_subjects=tuple(sorted(unmapped_subjects)),
            ambiguous_subjects=tuple(sorted(ambiguous_subjects)),
        )
        grouped = self._aggregate(records, selected_metric, grouping)
        totals = self._totals(records, grouped, selected_metric, grouping)
        evidence_fitness = _build_evidence_fitness(supported, mapping_summary)
        limitations = (
            "Schedule observations do not establish official employment history, faculty FTE, or workload.",
            "Subject-to-unit analysis is limited to reviewed governed mappings.",
            "Descriptive adjunct shares do not support staffing recommendations by themselves.",
        )
        provenance = {
            "source_root": repository_relative_path(source_root or self.schedule_root),
            "source_object_type": "course_offering_observation",
            "algorithm": ANALYSIS_ALGORITHM,
            "algorithm_version": ANALYSIS_VERSION,
            "academic_unit_registry_version": self.mapping_service.registry.version,
            "source_object_ids_fingerprint": _fingerprint(sorted(object_ids)),
        }
        payload = {
            "request": request, "metric": selected_metric.value,
            "grouping": list(grouping), "totals": totals,
            "grouped_results": [item.to_dict() for item in grouped],
            "uncertainty_summary": dict(uncertainty),
            "mapping_coverage": mapping_summary.to_dict(),
            "evidence_fitness": evidence_fitness.to_dict(),
            "limitations": list(limitations), "provenance": provenance,
            "source_object_count": len(values), "included_object_count": len(records),
            "excluded_object_count": excluded,
        }
        return ScheduleAggregationResult(
            request=request, metric=selected_metric.value, grouping=grouping,
            totals=totals, grouped_results=grouped,
            uncertainty_summary=dict(uncertainty), provenance=provenance,
            source_object_count=len(values), included_object_count=len(records),
            excluded_object_count=excluded,
            deterministic_result_fingerprint=_fingerprint_payload(payload),
            mapping_coverage=mapping_summary, evidence_fitness=evidence_fitness,
            limitations=limitations,
        )

    def _aggregate(
        self, records: Sequence[Mapping[str, Any]], metric: ScheduleAnalysisMetric,
        grouping: tuple[str, ...],
    ) -> tuple[ScheduleAggregationGroup, ...]:
        buckets: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
        for record in records:
            buckets[tuple(record.get(field) for field in grouping)].append(record)
        groups = []
        for key, items in buckets.items():
            dimensions = dict(zip(grouping, key))
            if metric == ScheduleAnalysisMetric.DISTINCT_INSTRUCTORS:
                instructors = {item["instructor"] for item in items if item["instructor"]}
                value, numerator, denominator, definition = len(instructors), None, None, None
            elif metric == ScheduleAnalysisMetric.COURSE_OFFERINGS:
                value, numerator, denominator, definition = len(items), None, None, None
            else:
                category_counts = Counter(item["normalized_instructor_type"] for item in items)
                resolved = category_counts[INSTRUCTOR_TYPE_FULL_TIME] + category_counts[INSTRUCTOR_TYPE_ADJUNCT]
                total = len(items)
                if metric == ScheduleAnalysisMetric.ADJUNCT_OFFERING_SHARE:
                    numerator, denominator = category_counts[INSTRUCTOR_TYPE_ADJUNCT], resolved
                    definition = "Adjunct offerings divided by Full Time plus Adjunct offerings; unresolved observations excluded."
                elif metric == ScheduleAnalysisMetric.FULL_TIME_OFFERING_SHARE:
                    numerator, denominator = category_counts[INSTRUCTOR_TYPE_FULL_TIME], resolved
                    definition = "Full Time offerings divided by Full Time plus Adjunct offerings; unresolved observations excluded."
                elif metric == ScheduleAnalysisMetric.RESOLVED_OFFERING_SHARE:
                    numerator, denominator = resolved, total
                    definition = "Full Time plus Adjunct offerings divided by all included offerings."
                else:
                    numerator, denominator = total - resolved, total
                    definition = "Unresolved Conflict, Missing Instructor, and Unknown Instructor Type offerings divided by all included offerings."
                value = round(100.0 * numerator / denominator, 6) if denominator else None
            groups.append(ScheduleAggregationGroup(
                academic_term=str(dimensions.get("academic_term") or ""),
                instructor_type=str(dimensions.get("normalized_instructor_type") or ""),
                subject=dimensions.get("subject"),
                academic_unit_id=(dimensions.get("academic_unit") or (None, None))[0] if "academic_unit" in dimensions else None,
                academic_unit_name=(dimensions.get("academic_unit") or (None, None))[1] if "academic_unit" in dimensions else None,
                value=value, numerator=numerator, denominator=denominator,
                denominator_definition=definition, source_observation_count=len(items),
            ))
        return tuple(sorted(groups, key=_group_sort_key))

    def _totals(
        self, records: Sequence[Mapping[str, Any]], groups: Sequence[ScheduleAggregationGroup],
        metric: ScheduleAnalysisMetric, grouping: tuple[str, ...],
    ) -> dict[str, int | float | None]:
        if metric.is_share:
            single = self._aggregate(records, metric, ())
            return {"overall_share_percent": single[0].value if single else None}
        if "normalized_instructor_type" in grouping:
            totals = Counter()
            for group in groups:
                totals[group.instructor_type] += int(group.value or 0)
            return {category: totals.get(category, 0) for category in _CATEGORY_ORDER}
        return {"grouped_value_sum": sum(int(group.value or 0) for group in groups)}

    def analyze_trend(
        self, request: str, *, observations: Iterable[Any] | None = None,
        metric: ScheduleAnalysisMetric | str,
        group_by: Sequence[str] = ("subject",), **filters: Any,
    ) -> ScheduleTrendResult:
        selected_metric = ScheduleAnalysisMetric(metric)
        base_grouping = tuple(field for field in group_by if field != "academic_term")
        aggregation = self.analyze_observations(
            request, self.load_observations() if observations is None else observations,
            metric=selected_metric, group_by=(*base_grouping, "academic_term"), **filters,
        )
        unsupported_terms = tuple(sorted(aggregation.evidence_fitness.unsupported_terms if aggregation.evidence_fitness else ()))
        supported_terms = sorted({group.academic_term for group in aggregation.grouped_results if academic_term_order(group.academic_term).supported}, key=academic_term_sort_key)
        by_entity: dict[tuple[Any, ...], list[ScheduleAggregationGroup]] = defaultdict(list)
        for group in aggregation.grouped_results:
            if not academic_term_order(group.academic_term).supported:
                continue
            entity = tuple(getattr(group, {"academic_unit": "academic_unit_id"}.get(field, field)) for field in base_grouping)
            by_entity[entity].append(group)
        trends = []
        for entity, points in sorted(by_entity.items(), key=lambda item: tuple(str(v or "") for v in item[0])):
            points.sort(key=lambda value: academic_term_sort_key(value.academic_term))
            first, last = points[0], points[-1]
            comparable = first.value is not None and last.value is not None
            absolute = round(float(last.value) - float(first.value), 6) if comparable else None
            between = [term for term in supported_terms if academic_term_sort_key(first.academic_term) <= academic_term_sort_key(term) <= academic_term_sort_key(last.academic_term)]
            present = {point.academic_term for point in points}
            missing = tuple(f"No comparable group observation for {term}." for term in between if term not in present)
            limitations = []
            if missing:
                limitations.append("The time series has missing academic terms.")
            if not comparable:
                limitations.append("A zero denominator prevents endpoint comparison.")
            if selected_metric.is_share:
                limitations.append("Percentage-point change is descriptive and does not establish causation.")
            trends.append(ScheduleTrendGroup(
                subject=first.subject,
                academic_unit_id=first.academic_unit_id,
                academic_unit_name=first.academic_unit_name,
                first_term=first.academic_term, last_term=last.academic_term,
                first_value=first.value, last_value=last.value,
                absolute_change=absolute,
                percentage_point_change=absolute if selected_metric.is_share else None,
                observation_count=sum(point.source_observation_count for point in points),
                missing_term_warnings=missing,
                comparability_limitations=tuple(limitations),
            ))
        payload = {
            "request": request, "metric": selected_metric.value,
            "grouping": list(base_grouping), "trends": [value.to_dict() for value in trends],
            "source_fingerprint": aggregation.deterministic_result_fingerprint,
            "unsupported_terms": list(unsupported_terms),
        }
        return ScheduleTrendResult(
            request=request, metric=selected_metric.value, grouping=base_grouping,
            trends=tuple(trends), source_aggregation=aggregation,
            unsupported_terms=unsupported_terms,
            deterministic_result_fingerprint=_fingerprint_payload(payload),
        )


def _group_sort_key(group: ScheduleAggregationGroup) -> tuple[Any, ...]:
    category_rank = {name: index for index, name in enumerate(_CATEGORY_ORDER)}
    return (
        str(group.academic_unit_name or ""), str(group.subject or ""),
        academic_term_sort_key(group.academic_term) if group.academic_term else (),
        category_rank.get(group.instructor_type, len(category_rank)),
    )


def _build_evidence_fitness(
    observations: Sequence[Any], mapping: AcademicUnitMappingSummary,
) -> ScheduleEvidenceFitness:
    total = len(observations)
    categories = Counter(_instructor_category(item) for item in observations)
    usable_subject = sum(bool(str(_value(item, "subject") or "").strip()) for item in observations)
    with_identity = sum(bool(str(_value(item, "instructor_raw") or _value(item, "instructor_name") or "").strip()) for item in observations)
    resolved = 0
    missing_type = 0
    for item in observations:
        assertion = _value(item, "instructor_type", {}) or {}
        resolution = assertion.get("resolution") or {}
        normalized = assertion.get("normalized_value")
        if normalized in {"full_time", "adjunct"} and (
            not assertion.get("conflicting") or resolution.get("resolved")
        ):
            resolved += 1
        elif not assertion.get("conflicting"):
            missing_type += 1
    terms = {str(_value(item, "academic_term") or "").strip() for item in observations}
    supported_terms = tuple(sorted((term for term in terms if academic_term_order(term).supported), key=academic_term_sort_key))
    unsupported_terms = tuple(sorted(term for term in terms if term and not academic_term_order(term).supported))
    rate = lambda count: round(100.0 * count / total, 6) if total else 0.0
    mapped_count = mapping.mapped_observations
    mapping_strength = mapped_count / total if total else 0.0
    suitability = {
        "descriptive_section_analysis": "suitable" if total else "insufficient",
        "adjunct_dependence_comparison": "conditionally_suitable" if resolved else "insufficient",
        "trend_description": "conditionally_suitable" if len(supported_terms) >= 2 else "insufficient",
        "academic_unit_comparison": "conditionally_suitable" if mapping_strength >= 0.8 else "insufficient_mapping_coverage",
        "official_employment_history_inference": "insufficient",
        "workload_inference": "insufficient",
        "staffing_recommendations": "insufficient",
    }
    return ScheduleEvidenceFitness(
        total_schedule_observations=total,
        observations_with_usable_subject=usable_subject,
        mapped_observations=mapped_count,
        unmapped_observations=mapping.unmapped_observation_count + mapping.unsupported_mapping_count,
        ambiguous_mappings=mapping.ambiguous_mapping_count,
        observations_with_instructor_identity=with_identity,
        observations_with_resolved_instructor_type=resolved,
        unresolved_conflict_rate=rate(categories[INSTRUCTOR_TYPE_UNRESOLVED_CONFLICT]),
        missing_instructor_type_rate=rate(missing_type),
        missing_instructor_rate=rate(categories[INSTRUCTOR_TYPE_MISSING_INSTRUCTOR]),
        identity_policy_limitations=(
            "Instructor names are formatting-normalized within groups but are not institutionally resolved identities.",
            "Instructor Type is a section-scoped source assertion, not a timeless employment fact.",
        ),
        term_coverage=supported_terms, unsupported_terms=unsupported_terms,
        suitability=suitability,
    )


def _fingerprint(values: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("utf-8")); digest.update(b"\0")
    return digest.hexdigest()


def _fingerprint_payload(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "AcademicUnitMappingSummary", "ScheduleAggregationGroup",
    "ScheduleAggregationResult", "ScheduleAnalysisMetric",
    "ScheduleAnalysisService", "ScheduleEvidenceFitness",
    "ScheduleTrendGroup", "ScheduleTrendResult",
    "INSTRUCTOR_TYPE_ADJUNCT", "INSTRUCTOR_TYPE_FULL_TIME",
    "INSTRUCTOR_TYPE_MISSING_INSTRUCTOR", "INSTRUCTOR_TYPE_UNKNOWN",
    "INSTRUCTOR_TYPE_UNRESOLVED_CONFLICT",
]
