from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class AcquisitionFailure:
    """
    One file that could not be represented as a SourceDocument.
    """

    relative_path: str
    error_type: str
    message: str


@dataclass(frozen=True)
class AcquisitionReport:
    """
    Immutable summary of one directory acquisition run.
    """

    directory: str
    files_examined: int
    new_documents: int
    unchanged_documents: int
    changed_documents: int
    duplicate_documents: int
    failed_documents: int
    elapsed_seconds: float
    failures: Tuple[AcquisitionFailure, ...] = ()

    @property
    def successful_documents(self) -> int:
        return self.files_examined - self.failed_documents

    def to_dict(self) -> dict:
        return {
            "directory": self.directory,
            "files_examined": self.files_examined,
            "new_documents": self.new_documents,
            "unchanged_documents": self.unchanged_documents,
            "changed_documents": self.changed_documents,
            "duplicate_documents": self.duplicate_documents,
            "failed_documents": self.failed_documents,
            "successful_documents": self.successful_documents,
            "elapsed_seconds": self.elapsed_seconds,
            "failures": [
                {
                    "relative_path": failure.relative_path,
                    "error_type": failure.error_type,
                    "message": failure.message,
                }
                for failure in self.failures
            ],
        }
