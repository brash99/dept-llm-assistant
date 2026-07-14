from app.acquisition.acquisition_report import (
    AcquisitionFailure,
    AcquisitionReport,
)
from app.acquisition.authority import SourceAuthority
from app.acquisition.directory_runner import (
    DirectoryAcquisitionRunner,
)
from app.acquisition.filesystem import (
    FilesystemAcquisitionService,
)
from app.acquisition.manifest import (
    AcquisitionManifest,
    AcquisitionStatus,
    ManifestDecision,
)
from app.acquisition.method import AcquisitionMethod
from app.acquisition.source_document import SourceDocument

__all__ = [
    "AcquisitionFailure",
    "AcquisitionManifest",
    "AcquisitionMethod",
    "AcquisitionReport",
    "AcquisitionStatus",
    "DirectoryAcquisitionRunner",
    "FilesystemAcquisitionService",
    "ManifestDecision",
    "SourceAuthority",
    "ObserverAuthorization",
    "SourceDocument",
    "WebAcquisitionService",
    "WebAcquisitionRunner",
    "WebCrawlFailure",
    "WebCrawlReport",
    "WebObserver",
    "WebObserverCatalog",
]

from app.acquisition.web import WebAcquisitionService

from app.acquisition.web_crawler import (
    WebAcquisitionRunner,
    WebCrawlFailure,
    WebCrawlReport,
)

from app.acquisition.observers import (
    ObserverAuthorization,
    WebObserver,
    WebObserverCatalog,
)
