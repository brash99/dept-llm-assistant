"""Decision-driven acquisition of explicitly curated external evidence."""

from app.acquisition.external.contracts import (
    AcquisitionPlan,
    AcquisitionPlanItem,
    ExternalResourceDefinition,
    ExternalSourceDefinition,
    StagedExternalDocument,
    ValidationResult,
)
from app.acquisition.external.planner import EvidenceAcquisitionPlanner
from app.acquisition.external.registry import ExternalSourceRegistry
from app.acquisition.external.service import (
    CuratedURLFetcher,
    ExternalEvidenceAcquisitionService,
    FetchedArtifact,
)

__all__ = [
    "AcquisitionPlan",
    "AcquisitionPlanItem",
    "CuratedURLFetcher",
    "EvidenceAcquisitionPlanner",
    "ExternalEvidenceAcquisitionService",
    "ExternalResourceDefinition",
    "ExternalSourceDefinition",
    "ExternalSourceRegistry",
    "FetchedArtifact",
    "StagedExternalDocument",
    "ValidationResult",
]
