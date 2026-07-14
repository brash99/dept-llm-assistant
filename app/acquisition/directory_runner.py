from pathlib import Path
from time import perf_counter
from typing import Iterable, List, Optional, Sequence, Set

from app.acquisition.acquisition_report import (
    AcquisitionFailure,
    AcquisitionReport,
)
from app.acquisition.authority import SourceAuthority
from app.acquisition.filesystem import FilesystemAcquisitionService
from app.acquisition.manifest import (
    AcquisitionManifest,
    AcquisitionStatus,
)
from app.acquisition.method import AcquisitionMethod


class DirectoryAcquisitionRunner:
    """
    Orchestrate acquisition across a directory tree.

    The runner delegates:
    - hashing and MIME detection to FilesystemAcquisitionService,
    - history and status classification to AcquisitionManifest.

    It does not parse, chunk, embed, copy, move, or interpret files.
    """

    DEFAULT_IGNORED_NAMES: Set[str] = {
        ".DS_Store",
        "Thumbs.db",
    }

    DEFAULT_IGNORED_SUFFIXES: Set[str] = {
        ".pyc",
        ".tmp",
        ".part",
        ".swp",
    }

    def __init__(
        self,
        filesystem_service: FilesystemAcquisitionService,
        manifest: AcquisitionManifest,
    ) -> None:
        self.filesystem_service = filesystem_service
        self.manifest = manifest

    def run(
        self,
        *,
        directory: Path,
        source_organization: str,
        authority: SourceAuthority,
        acquisition_method: AcquisitionMethod,
        recursive: bool = True,
        ignored_names: Optional[Sequence[str]] = None,
        ignored_suffixes: Optional[Sequence[str]] = None,
    ) -> AcquisitionReport:
        started = perf_counter()

        directory = Path(directory).resolve()
        self._validate_directory(directory)

        effective_ignored_names = set(self.DEFAULT_IGNORED_NAMES)
        effective_ignored_suffixes = set(
            self.DEFAULT_IGNORED_SUFFIXES
        )

        if ignored_names:
            effective_ignored_names.update(ignored_names)

        if ignored_suffixes:
            effective_ignored_suffixes.update(
                suffix.casefold()
                for suffix in ignored_suffixes
            )

        files = list(
            self._iter_files(
                directory=directory,
                recursive=recursive,
                ignored_names=effective_ignored_names,
                ignored_suffixes=effective_ignored_suffixes,
            )
        )

        counts = {
            AcquisitionStatus.NEW: 0,
            AcquisitionStatus.UNCHANGED: 0,
            AcquisitionStatus.CHANGED: 0,
            AcquisitionStatus.DUPLICATE_CONTENT: 0,
        }

        failures: List[AcquisitionFailure] = []

        for source_file in files:
            try:
                document = self.filesystem_service.acquire(
                    source_file=source_file,
                    title=source_file.stem,
                    source_organization=source_organization,
                    authority=authority,
                    acquisition_method=acquisition_method,
                )

                decision = self.manifest.record(document)
                counts[decision.status] += 1

            except Exception as error:
                failures.append(
                    AcquisitionFailure(
                        relative_path=self._display_path(
                            source_file
                        ),
                        error_type=type(error).__name__,
                        message=str(error),
                    )
                )

        elapsed = perf_counter() - started

        return AcquisitionReport(
            directory=self._display_path(directory),
            files_examined=len(files),
            new_documents=counts[AcquisitionStatus.NEW],
            unchanged_documents=counts[
                AcquisitionStatus.UNCHANGED
            ],
            changed_documents=counts[
                AcquisitionStatus.CHANGED
            ],
            duplicate_documents=counts[
                AcquisitionStatus.DUPLICATE_CONTENT
            ],
            failed_documents=len(failures),
            elapsed_seconds=elapsed,
            failures=tuple(failures),
        )

    def _validate_directory(self, directory: Path) -> None:
        if not directory.exists():
            raise FileNotFoundError(
                f"Acquisition directory does not exist: "
                f"{directory}"
            )

        if not directory.is_dir():
            raise NotADirectoryError(
                f"Acquisition path is not a directory: "
                f"{directory}"
            )

        try:
            directory.relative_to(
                self.filesystem_service.storage_root
            )
        except ValueError as error:
            raise ValueError(
                "Acquisition directory must be located beneath "
                "the filesystem service storage root: "
                f"{self.filesystem_service.storage_root}"
            ) from error

    def _iter_files(
        self,
        *,
        directory: Path,
        recursive: bool,
        ignored_names: Set[str],
        ignored_suffixes: Set[str],
    ) -> Iterable[Path]:
        iterator = (
            directory.rglob("*")
            if recursive
            else directory.glob("*")
        )

        files = []

        for candidate in iterator:
            if not candidate.is_file():
                continue

            if candidate.name in ignored_names:
                continue

            if candidate.suffix.casefold() in ignored_suffixes:
                continue

            files.append(candidate)

        return sorted(
            files,
            key=lambda path: path.as_posix().casefold(),
        )

    def _display_path(self, path: Path) -> str:
        resolved = Path(path).resolve()

        try:
            return resolved.relative_to(
                self.filesystem_service.storage_root
            ).as_posix()
        except ValueError:
            return resolved.as_posix()
