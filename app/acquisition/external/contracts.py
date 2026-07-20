from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

from app.acquisition.authority import SourceAuthority
from app.acquisition.source_document import SourceDocument


@dataclass(frozen=True)
class ExternalResourceDefinition:
    id: str
    title: str
    canonical_url: str
    document_type: str
    evidence_domains: Tuple[str, ...]
    effective_period: Optional[str] = None
    version: Optional[str] = None
    geographic_scope: str = "United States"


@dataclass(frozen=True)
class ExternalSourceDefinition:
    key: str
    name: str
    issuing_authority: str
    authority_class: SourceAuthority
    evidence_role: str
    supported_decision_types: Tuple[str, ...]
    supported_evidence_domains: Tuple[str, ...]
    refresh_policy: str
    max_age_days: int
    expected_extraction_method: str
    resources: Tuple[ExternalResourceDefinition, ...]


@dataclass(frozen=True)
class AcquisitionPlanItem:
    evidence_domain: str
    source_key: str
    resource_id: str
    title: str
    canonical_url: str
    issuing_authority: str
    authority_class: str
    evidence_role: str


@dataclass(frozen=True)
class AcquisitionPlan:
    decision_type: str
    decision_label: str
    missing_domains: Tuple[str, ...]
    items: Tuple[AcquisitionPlanItem, ...]
    unmapped_domains: Tuple[str, ...] = ()

    @property
    def estimated_documents(self) -> int:
        return len({item.resource_id for item in self.items})

    @property
    def candidate_authorities(self) -> Tuple[str, ...]:
        return tuple(dict.fromkeys(item.issuing_authority for item in self.items))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_type": self.decision_type,
            "decision_label": self.decision_label,
            "missing_domains": list(self.missing_domains),
            "items": [asdict(item) for item in self.items],
            "unmapped_domains": list(self.unmapped_domains),
            "estimated_documents": self.estimated_documents,
            "candidate_authorities": list(self.candidate_authorities),
        }


@dataclass(frozen=True)
class StagedExternalDocument:
    source_document: SourceDocument
    source_key: str
    resource_id: str
    issuing_authority: str
    authority_class: str
    evidence_role: str
    decision_types: Tuple[str, ...]
    evidence_domains: Tuple[str, ...]
    effective_period: Optional[str]
    version: Optional[str]
    canonical_url: str
    document_type: str
    geographic_scope: str
    refresh_policy: str
    max_age_days: int
    expected_extraction_method: str

    def provenance(self) -> Dict[str, Any]:
        return {
            "issuing_authority": self.issuing_authority,
            "authority_class": self.authority_class,
            "evidence_role": self.evidence_role,
            "decision_types": list(self.decision_types),
            "evidence_domains": list(self.evidence_domains),
            "retrieval_timestamp": self.source_document.acquired_at.isoformat(),
            "effective_period": self.effective_period,
            "version": self.version,
            "canonical_url": self.canonical_url,
            "document_type": self.document_type,
            "geographic_scope": self.geographic_scope,
            "refresh_policy": self.refresh_policy,
            "expected_extraction_method": self.expected_extraction_method,
            "content_hash": self.source_document.content_hash,
        }


@dataclass(frozen=True)
class ValidationResult:
    resource_id: str
    valid: bool
    errors: Tuple[str, ...]
    extracted_characters: int
    duplicate: bool = False
    fresh: bool = True

