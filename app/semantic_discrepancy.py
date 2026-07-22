"""Deterministic explanations for catalog, schedule, and governance differences."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping, Sequence

from app.subject_ownership import SubjectOwnershipRegistry


ANALYZER_VERSION = "1.0"


class DiscrepancyCategory(str, Enum):
    CURRENT_CATALOG_ONLY = "current_catalog_only"
    CURRENT_SCHEDULE_ONLY = "current_schedule_only"
    HISTORICAL_PREFIX = "historical_prefix"
    SERVICE_SUBJECT = "service_subject"
    INTERDISCIPLINARY = "interdisciplinary"
    CENTRAL_ADMINISTRATION = "central_administration"
    GRADUATE_ONLY = "graduate_only"
    CATALOG_EXTRACTION_LIMITATION = "catalog_extraction_limitation"
    CATALOG_STRUCTURE_LIMITATION = "catalog_structure_limitation"
    SCHEDULE_NORMALIZATION_LIMITATION = "schedule_normalization_limitation"
    GOVERNANCE_GAP = "governance_gap"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DiscrepancyEvidence:
    governed: bool
    current_catalog: bool
    production_schedule: bool
    schedule_offering_count: int
    schedule_term_count: int
    schedule_distinct_instructor_count: int
    catalog_sections: tuple[str, ...]
    catalog_candidate_status: str | None
    catalog_mapping_status: str | None
    catalog_relationship_type: str | None
    catalog_extraction_confidence: float | None
    catalog_kind: str | None
    schedule_normalization_issues: tuple[str, ...]

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class DiscrepancyRecord:
    prefix: str
    category: str
    evidence: DiscrepancyEvidence
    confidence: float
    rationale: str
    suggested_next_action: str
    review_priority: str
    deterministic_fingerprint: str

    def to_dict(self):
        value = asdict(self); value["evidence"] = self.evidence.to_dict(); return value


@dataclass(frozen=True)
class DiscrepancyEvidenceFitness:
    semantic_completeness_percent: float
    catalog_completeness_percent: float
    schedule_completeness_percent: float
    governance_completeness_percent: float
    parser_completeness_percent: float
    overall_discrepancy_count: int
    confidence_distribution: Mapping[str, int]
    review_workload_remaining: Mapping[str, int]
    limitations: tuple[str, ...]

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class DiscrepancyDashboard:
    records: tuple[DiscrepancyRecord, ...]
    overall_counts: Mapping[str, int]
    count_by_category: Mapping[str, int]
    observation_counts: Mapping[str, int]
    prefix_counts: Mapping[str, int]
    confidence_histogram: Mapping[str, int]
    review_priority: tuple[str, ...]
    evidence_fitness: DiscrepancyEvidenceFitness
    deterministic_fingerprint: str

    def to_dict(self):
        return {"records": [item.to_dict() for item in self.records],
                "overall_counts": dict(self.overall_counts), "count_by_category": dict(self.count_by_category),
                "observation_counts": dict(self.observation_counts), "prefix_counts": dict(self.prefix_counts),
                "confidence_histogram": dict(self.confidence_histogram), "review_priority": list(self.review_priority),
                "evidence_fitness": self.evidence_fitness.to_dict(), "deterministic_fingerprint": self.deterministic_fingerprint}


class SemanticDiscrepancyAnalyzer:
    """Assign exactly one evidence-backed primary explanation per discrepancy."""

    def analyze(
        self,
        governed_registry: SubjectOwnershipRegistry,
        catalog_observations: Sequence[Mapping[str, Any]],
        catalog_candidates: Sequence[Mapping[str, Any]],
        schedule_inventory: Mapping[str, Mapping[str, Any]],
    ) -> DiscrepancyDashboard:
        governed = {item.subject_code for item in governed_registry.records}
        observations_by: dict[str, list[Mapping[str, Any]]] = {}
        for item in catalog_observations:
            observations_by.setdefault(str(item.get("subject_code") or "").upper(), []).append(item)
        candidates = {str(item.get("subject_code") or "").upper(): item for item in catalog_candidates}
        schedule = {str(code).upper(): value for code, value in schedule_inventory.items()}
        universe = sorted(governed | set(observations_by) | set(schedule) | set(candidates))
        records = []
        for prefix in universe:
            in_catalog = prefix in observations_by
            in_schedule = prefix in schedule
            candidate = candidates.get(prefix) or {}
            # Fully aligned governed evidence is not a discrepancy.
            if prefix in governed and in_catalog and in_schedule and candidate.get("candidate_status") not in {"ambiguous", "requires_review", "exception_candidate", "unsupported"}:
                continue
            evidence = self._evidence(prefix, prefix in governed, observations_by.get(prefix, ()), candidate, schedule.get(prefix) or {})
            category, confidence, rationale, action = _classify(evidence)
            priority = _priority(evidence, category)
            semantic = {"prefix": prefix, "category": category, "evidence": evidence.to_dict(), "confidence": confidence, "rationale": rationale, "action": action, "priority": priority, "version": ANALYZER_VERSION}
            records.append(DiscrepancyRecord(prefix, category, evidence, confidence, rationale, action, priority, _fingerprint(semantic)))
        records.sort(key=lambda item: (_priority_rank(item.review_priority), -item.evidence.schedule_offering_count, item.prefix))
        return _dashboard(tuple(records), governed, set(observations_by), set(schedule))

    @staticmethod
    def _evidence(prefix, governed, observations, candidate, schedule):
        confidences = [float(item.get("extraction_confidence", 1.0)) for item in observations]
        catalog_kind = None
        if observations:
            catalog_kind = str((observations[0].get("provenance") or {}).get("catalog_kind") or "undergraduate")
        return DiscrepancyEvidence(
            governed, bool(observations), bool(schedule), int(schedule.get("offering_count", 0)),
            int(schedule.get("term_count", 0)), int(schedule.get("distinct_instructor_count", 0)),
            tuple(sorted({str(item.get("section_title") or "") for item in observations if item.get("section_title")})),
            candidate.get("candidate_status"), candidate.get("proposed_mapping_status"),
            candidate.get("proposed_relationship_type"), min(confidences) if confidences else None,
            catalog_kind, tuple(sorted(map(str, schedule.get("normalization_issues") or ()))),
        )


def _classify(evidence: DiscrepancyEvidence):
    relationship = evidence.catalog_relationship_type
    mapping = evidence.catalog_mapping_status
    if relationship == "interdisciplinary_subject" or mapping == "interdisciplinary":
        return DiscrepancyCategory.INTERDISCIPLINARY.value, 1.0, "Catalog evidence identifies an interdisciplinary subject rather than ordinary department ownership.", "Expected exception; review interdisciplinary governance context."
    if relationship in {"service_subject", "service_subject_provision"} or mapping == "service_subject":
        return DiscrepancyCategory.SERVICE_SUBJECT.value, 1.0, "Catalog evidence identifies a service subject whose instructors may have different home units.", "Expected exception; review service-subject governance context."
    if relationship == "centrally_administered_subject":
        return DiscrepancyCategory.CENTRAL_ADMINISTRATION.value, 1.0, "Reviewed catalog context identifies central administration rather than an academic department.", "Expected exception; review administrative ownership."
    if evidence.catalog_kind == "graduate":
        return DiscrepancyCategory.GRADUATE_ONLY.value, 1.0, "The prefix is supported only by graduate-catalog evidence.", "Confirm whether graduate evidence belongs in this analytical scope."
    if evidence.catalog_extraction_confidence is not None and evidence.catalog_extraction_confidence < 0.75:
        return DiscrepancyCategory.CATALOG_EXTRACTION_LIMITATION.value, evidence.catalog_extraction_confidence, "Catalog extraction confidence is below the reviewed reliability threshold.", "Improve or manually inspect the catalog parser."
    if evidence.schedule_normalization_issues:
        return DiscrepancyCategory.SCHEDULE_NORMALIZATION_LIMITATION.value, 1.0, "Schedule provenance records normalization issues for this prefix.", "Investigate schedule normalization."
    if evidence.catalog_candidate_status in {"ambiguous", "requires_review", "unsupported"} and evidence.current_catalog:
        return DiscrepancyCategory.CATALOG_STRUCTURE_LIMITATION.value, 0.5, "The prefix was extracted, but its catalog section cannot be resolved unambiguously.", "Review catalog structure or exact section aliases."
    if evidence.production_schedule and not evidence.current_catalog and evidence.governed:
        return DiscrepancyCategory.HISTORICAL_PREFIX.value, 1.0, "The governed prefix appears in schedules but is absent from the selected current catalog.", "Treat as historical/current institutional evidence; do not delete governance automatically."
    if evidence.current_catalog and not evidence.governed:
        return DiscrepancyCategory.GOVERNANCE_GAP.value, 1.0, "Current catalog course descriptions support the prefix, but no governed ownership record exists.", "Review governance; never promote automatically."
    if evidence.current_catalog and not evidence.production_schedule:
        return DiscrepancyCategory.CURRENT_CATALOG_ONLY.value, 1.0, "The prefix appears in the current catalog but has no schedule observation in the supplied schedule inventory.", "Review whether the course family was not offered during the schedule window."
    if evidence.production_schedule and not evidence.current_catalog:
        return DiscrepancyCategory.CURRENT_SCHEDULE_ONLY.value, 0.75, "The prefix appears in schedules but lacks current-catalog and governed support.", "Investigate historical catalogs, governance, and schedule normalization."
    return DiscrepancyCategory.UNKNOWN.value, 0.0, "Available evidence does not support a more specific explanation.", "Collect evidence and review manually."


def _priority(evidence, category):
    if category in {"unknown", "catalog_structure_limitation", "schedule_normalization_limitation"} or evidence.schedule_offering_count >= 50:
        return "high"
    if evidence.schedule_offering_count >= 10 or category in {"governance_gap", "current_schedule_only", "catalog_extraction_limitation"}:
        return "medium"
    return "low"


def _priority_rank(value): return {"high": 0, "medium": 1, "low": 2}[value]
def _percent(numerator, denominator): return round(100.0 * numerator / denominator, 6) if denominator else 100.0
def _fingerprint(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _dashboard(records, governed, catalog, schedule):
    categories = Counter(item.category for item in records); confidence = Counter("high" if item.confidence >= .9 else "medium" if item.confidence >= .6 else "low" for item in records); priorities = Counter(item.review_priority for item in records)
    union = governed | catalog | schedule
    explained = sum(item.category != DiscrepancyCategory.UNKNOWN.value for item in records)
    fitness = DiscrepancyEvidenceFitness(
        _percent(explained, len(records)), _percent(len(catalog), len(union)), _percent(len(schedule), len(union)),
        _percent(len(governed), len(union)), _percent(sum(item.category != DiscrepancyCategory.CATALOG_EXTRACTION_LIMITATION.value for item in records), len(records)),
        len(records), dict(sorted(confidence.items())), dict(sorted(priorities.items())),
        ("Completeness measures evidence alignment, not institutional importance.", "A deterministic explanation does not itself establish governed ownership."),
    )
    semantic = {"records": [item.deterministic_fingerprint for item in records], "categories": dict(sorted(categories.items())), "confidence": dict(sorted(confidence.items())), "priorities": dict(sorted(priorities.items())), "fitness": fitness.to_dict(), "version": ANALYZER_VERSION}
    return DiscrepancyDashboard(records, {"discrepancies": len(records), "explained": explained, "unknown": len(records) - explained}, dict(sorted(categories.items())), {"catalog_course_prefixes": len(catalog), "schedule_prefixes": len(schedule), "governed_prefixes": len(governed)}, {"union": len(union), "catalog_only": len(catalog - schedule), "schedule_only": len(schedule - catalog)}, dict(sorted(confidence.items())), tuple(item.prefix for item in records), fitness, _fingerprint(semantic))


__all__ = ["DiscrepancyCategory", "DiscrepancyDashboard", "DiscrepancyEvidence", "DiscrepancyEvidenceFitness", "DiscrepancyRecord", "SemanticDiscrepancyAnalyzer"]
