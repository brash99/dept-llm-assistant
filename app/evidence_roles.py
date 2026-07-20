"""Deterministic evidence-role derivation and empirical allocation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional, Sequence, Tuple


class EvidenceRole(str, Enum):
    EXTERNAL_TRENDS = "external_landscape_trends"
    WORKFORCE_DEMAND = "workforce_labor_demand"
    REGULATORY = "regulatory_accreditation"
    INSTITUTIONAL_CAPACITY = "institutional_capacity"
    INSTITUTIONAL_OUTCOMES = "institutional_enrollment_outcomes"
    INSTITUTIONAL_PLANNING = "institutional_planning"
    INSTITUTIONAL_CONTEXT = "institutional_context"
    COMPARATOR = "comparator_peer"
    FINANCIAL = "financial_resources"
    REGIONAL_DEMAND = "regional_demand"
    CONTEXTUAL = "contextual_evidence"
    UNKNOWN = "unknown"


EXPECTED_ROLES_BY_DECISION_TYPE = {
    "academic_program": (
        EvidenceRole.EXTERNAL_TRENDS.value,
        EvidenceRole.WORKFORCE_DEMAND.value,
        EvidenceRole.REGULATORY.value,
        EvidenceRole.INSTITUTIONAL_CAPACITY.value,
        EvidenceRole.INSTITUTIONAL_OUTCOMES.value,
        EvidenceRole.INSTITUTIONAL_PLANNING.value,
        EvidenceRole.COMPARATOR.value,
        EvidenceRole.FINANCIAL.value,
        EvidenceRole.REGIONAL_DEMAND.value,
    ),
    "enrollment_planning": (
        EvidenceRole.EXTERNAL_TRENDS.value,
        EvidenceRole.INSTITUTIONAL_OUTCOMES.value,
        EvidenceRole.WORKFORCE_DEMAND.value,
        EvidenceRole.REGIONAL_DEMAND.value,
        EvidenceRole.COMPARATOR.value,
        EvidenceRole.INSTITUTIONAL_CAPACITY.value,
    ),
}


@dataclass(frozen=True)
class EvidenceRoleAssessment:
    role: str
    source: str
    confidence: float


@dataclass(frozen=True)
class RoleAllocationResult:
    selected: Tuple[object, ...]
    role_excluded: Tuple[object, ...]
    quota_excluded: Tuple[object, ...]
    insufficient_relevance: Tuple[object, ...]
    roles_represented: Tuple[str, ...]
    role_counts: dict
    expected_roles: Tuple[str, ...]
    missing_roles: Tuple[str, ...]
    concentrated_roles: Tuple[str, ...]
    changed_baseline_order: bool

    @property
    def excluded(self) -> Tuple[object, ...]:
        return self.role_excluded + self.quota_excluded + self.insufficient_relevance


def _normalized_metadata_text(result) -> str:
    citation = result.citation or {}
    metadata = result.metadata or {}
    provenance = metadata.get("external_provenance") or {}
    values = [
        metadata.get("evidence_role") or provenance.get("evidence_role"),
        metadata.get("document_type") or provenance.get("document_type"),
        metadata.get("authority_class"),
        metadata.get("geographic_scope") or provenance.get("geographic_scope"),
        citation.get("title"),
        citation.get("relative_path"),
    ]
    values.extend(metadata.get("evidence_domains") or provenance.get("evidence_domains") or ())
    return re.sub(r"[^a-z0-9]+", " ", " ".join(str(value or "") for value in values).casefold())


def derive_evidence_role(result) -> EvidenceRoleAssessment:
    """Derive a broad decision function from provenance already on a result."""
    metadata = result.metadata or {}
    provenance = metadata.get("external_provenance") or {}
    explicit = bool(
        metadata.get("evidence_role")
        or provenance.get("evidence_role")
        or metadata.get("document_type")
        or provenance.get("document_type")
        or metadata.get("evidence_domains")
        or provenance.get("evidence_domains")
    )
    source = "explicit_metadata" if explicit else "inferred_metadata"
    confidence = 0.95 if explicit else 0.75
    text = _normalized_metadata_text(result)
    document_type = str(
        metadata.get("document_type")
        or provenance.get("document_type")
        or ""
    ).casefold()

    if any(marker in document_type for marker in ("enrollment_survey", "historical_trend")):
        return EvidenceRoleAssessment(EvidenceRole.EXTERNAL_TRENDS.value, source, confidence)
    if any(marker in document_type for marker in ("occupational", "workforce", "career_profile")):
        return EvidenceRoleAssessment(EvidenceRole.WORKFORCE_DEMAND.value, source, confidence)

    rules = (
        (EvidenceRole.COMPARATOR, ("comparator", "peer institution", "academic common market")),
        (EvidenceRole.REGIONAL_DEMAND, ("regional demand", "regional workforce", "state workforce")),
        (EvidenceRole.FINANCIAL, ("budget", "financial", "cost", "revenue", "funding")),
        (EvidenceRole.REGULATORY, ("accreditation", "accreditor", "regulatory", "formal external standard", "program authority")),
        (EvidenceRole.INSTITUTIONAL_OUTCOMES, ("institutional enrollment", "retention", "graduation", "student outcomes")),
        (EvidenceRole.EXTERNAL_TRENDS, ("enrollment survey", "enrollment demand", "degree survey", "historical trend", "trend assessment")),
        (EvidenceRole.WORKFORCE_DEMAND, ("workforce", "labor market", "occupational", "employment outlook", "career profile")),
        (EvidenceRole.INSTITUTIONAL_CAPACITY, ("institutional capacity", "faculty capacity", "laboratory capacity", "facilities capacity")),
        (EvidenceRole.INSTITUTIONAL_PLANNING, ("planning document", "program proposal", "curriculum justification", "strategic planning")),
        (EvidenceRole.INSTITUTIONAL_CONTEXT, ("institutional self study", "departmental report", "institutional operating record")),
    )
    for role, markers in rules:
        if any(marker in text for marker in markers):
            return EvidenceRoleAssessment(role.value, source, confidence)

    if "selfstudy" in text or "self study" in text:
        return EvidenceRoleAssessment(EvidenceRole.INSTITUTIONAL_CONTEXT.value, source, confidence)
    if re.search(r"\bcriterion\s+\d+\b.*\b(?:final|draft)\b", text):
        return EvidenceRoleAssessment(EvidenceRole.INSTITUTIONAL_CONTEXT.value, source, confidence)
    if "curricjustification" in text:
        return EvidenceRoleAssessment(EvidenceRole.INSTITUTIONAL_PLANNING.value, source, confidence)

    if explicit:
        return EvidenceRoleAssessment(EvidenceRole.CONTEXTUAL.value, source, 0.70)
    return EvidenceRoleAssessment(EvidenceRole.UNKNOWN.value, "fallback", 0.25)


def expected_roles_for(decision_type: Optional[str]) -> Tuple[str, ...]:
    value = getattr(decision_type, "value", decision_type)
    return EXPECTED_ROLES_BY_DECISION_TYPE.get(str(value or ""), ())


def allocate_empirical_by_role(
    candidates: Sequence[object],
    *,
    limit: int,
    decision_type: Optional[str],
    max_per_role: Optional[int],
    relevance_margin: float,
    minimum_role_confidence: float = 0.70,
) -> RoleAllocationResult:
    """Apply a soft role cap without reaching far below the reranker cutoff."""
    candidates = list(candidates)
    baseline = candidates[:limit]
    expected = expected_roles_for(decision_type)
    if not candidates or limit == 0:
        return RoleAllocationResult((), (), (), (), (), {}, expected, expected, (), False)

    for result in candidates:
        assessment = derive_evidence_role(result)
        result.metadata["derived_evidence_role"] = assessment.role
        result.metadata["evidence_role_source"] = assessment.source
        result.metadata["evidence_role_confidence"] = assessment.confidence

    usable_roles = any(
        result.metadata["evidence_role_confidence"] >= minimum_role_confidence
        and result.metadata["derived_evidence_role"] != EvidenceRole.UNKNOWN.value
        for result in candidates
    )
    if max_per_role is None or not usable_roles:
        selected = baseline
        role_excluded = []
        quota_excluded = candidates[limit:]
        insufficient_relevance = []
    else:
        cutoff = baseline[-1].score if baseline else candidates[0].score
        relevance_floor = cutoff - max(0.0, relevance_margin)
        counts = Counter()
        selected = []
        role_excluded = []
        quota_excluded = []
        insufficient_relevance = []
        for result in candidates:
            role = result.metadata["derived_evidence_role"]
            confidence = result.metadata["evidence_role_confidence"]
            if len(selected) >= limit:
                result.metadata["evidence_exclusion_reason"] = (
                    "Excluded after the empirical evidence quota was filled."
                )
                quota_excluded.append(result)
                continue
            if result.score < relevance_floor:
                result.metadata["evidence_exclusion_reason"] = (
                    "Available for role coverage but below the reranker-relative "
                    f"relevance floor ({relevance_floor:.4f})."
                )
                insufficient_relevance.append(result)
                continue
            if confidence >= minimum_role_confidence and counts[role] >= max_per_role:
                result.metadata["evidence_exclusion_reason"] = (
                    "Excluded by evidence-role concentration control "
                    f"({max_per_role} per role)."
                )
                role_excluded.append(result)
                continue
            result.metadata["evidence_role_added_new_coverage"] = counts[role] == 0
            result.metadata["evidence_role_fallback_selection"] = confidence < minimum_role_confidence
            counts[role] += 1
            selected.append(result)

    counts = Counter(result.metadata["derived_evidence_role"] for result in selected)
    represented = tuple(dict.fromkeys(result.metadata["derived_evidence_role"] for result in selected))
    missing = tuple(role for role in expected if role not in counts)
    concentrated = tuple(role for role, count in counts.items() if max_per_role and count >= max_per_role)
    changed = [item.chunk_id for item in selected] != [item.chunk_id for item in baseline]
    return RoleAllocationResult(
        selected=tuple(selected),
        role_excluded=tuple(role_excluded),
        quota_excluded=tuple(quota_excluded),
        insufficient_relevance=tuple(insufficient_relevance),
        roles_represented=represented,
        role_counts=dict(counts),
        expected_roles=expected,
        missing_roles=missing,
        concentrated_roles=concentrated,
        changed_baseline_order=changed,
    )
