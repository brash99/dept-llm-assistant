import hashlib
import mimetypes
from pathlib import Path
from typing import Optional

from app.acquisition.authority import SourceAuthority
from app.acquisition.method import AcquisitionMethod
from app.acquisition.source_document import SourceDocument


class FilesystemAcquisitionService:
    """
    Create SourceDocument records for files already present on disk.

    Version 0.1:
    - validates the source file,
    - computes a SHA-256 content hash,
    - derives a stable document id,
    - detects the media type,
    - returns a SourceDocument.

    It does not copy, move, parse, chunk, or embed the file.
    """

    def __init__(self, storage_root: Path) -> None:
        self.storage_root = Path(storage_root).resolve()

        if not self.storage_root.exists():
            raise FileNotFoundError(
                f"Acquisition storage root does not exist: "
                f"{self.storage_root}"
            )

        if not self.storage_root.is_dir():
            raise NotADirectoryError(
                f"Acquisition storage root is not a directory: "
                f"{self.storage_root}"
            )

    def acquire(
        self,
        *,
        source_file: Path,
        title: str,
        source_organization: str,
        authority: SourceAuthority,
        acquisition_method: AcquisitionMethod,
        source_url: Optional[str] = None,
        publication_date=None,
        media_type: Optional[str] = None,
    ) -> SourceDocument:
        source_file = Path(source_file).resolve()

        self._validate_source_file(source_file)

        relative_path = source_file.relative_to(
            self.storage_root
        ).as_posix()

        content_hash = self.compute_sha256(source_file)

        detected_media_type = (
            media_type
            or mimetypes.guess_type(source_file.name)[0]
            or "application/octet-stream"
        )

        return SourceDocument.acquired_now(
            id=f"sha256:{content_hash}",
            title=title,
            source_organization=source_organization,
            authority=authority,
            acquisition_method=acquisition_method,
            relative_path=relative_path,
            content_hash=content_hash,
            source_url=source_url,
            publication_date=publication_date,
            media_type=detected_media_type,
        )

    def _validate_source_file(self, source_file: Path) -> None:
        if not source_file.exists():
            raise FileNotFoundError(
                f"Source file does not exist: {source_file}"
            )

        if not source_file.is_file():
            raise ValueError(
                f"Source path is not a regular file: {source_file}"
            )

        try:
            source_file.relative_to(self.storage_root)
        except ValueError as error:
            raise ValueError(
                "Source file must be located beneath the acquisition "
                f"storage root: {self.storage_root}"
            ) from error

    @staticmethod
    def compute_sha256(
        source_file: Path,
        block_size: int = 1024 * 1024,
    ) -> str:
        """
        Compute a file hash without loading the entire file into memory.
        """
        digest = hashlib.sha256()

        with Path(source_file).open("rb") as handle:
            while True:
                block = handle.read(block_size)

                if not block:
                    break

                digest.update(block)

        return digest.hexdigest()
