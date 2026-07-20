"""Decision-driven acquisition of explicitly curated external evidence."""

from app.acquisition.external.contracts import (
    AcquisitionFailure,
    AcquisitionMode,
    AcquisitionPlan,
    AcquisitionPlanItem,
    AcquisitionSkip,
    ExternalAcquisitionReport,
    ExternalResourceDefinition,
    ExternalSourceDefinition,
    StagingResult,
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
    "AcquisitionFailure",
    "AcquisitionMode",
    "AcquisitionPlan",
    "AcquisitionPlanItem",
    "AcquisitionSkip",
    "CuratedURLFetcher",
    "EvidenceAcquisitionPlanner",
    "ExternalEvidenceAcquisitionService",
    "ExternalAcquisitionReport",
    "ExternalResourceDefinition",
    "ExternalSourceDefinition",
    "ExternalSourceRegistry",
    "FetchedArtifact",
    "StagingResult",
    "StagedExternalDocument",
    "ValidationResult",
]
