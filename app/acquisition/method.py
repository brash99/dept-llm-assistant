from enum import Enum


class AcquisitionMethod(str, Enum):
    """
    Mechanism by which source bytes entered ISO's acquisition layer.
    """

    WEB_CRAWL = "web_crawl"
    FILESYSTEM_IMPORT = "filesystem_import"
    GOOGLE_DRIVE_SYNC = "google_drive_sync"
    API_DOWNLOAD = "api_download"
    MANUAL_UPLOAD = "manual_upload"
    GENERATED = "generated"
