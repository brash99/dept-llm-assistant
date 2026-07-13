import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from app.acquisition.source_document import SourceDocument


class AcquisitionStatus(str, Enum):
    """
    Relationship between an acquired SourceDocument and the existing manifest.
    """

    NEW = "new"
    UNCHANGED = "unchanged"
    CHANGED = "changed"
    DUPLICATE_CONTENT = "duplicate_content"


@dataclass(frozen=True)
class ManifestDecision:
    """
    Result of comparing one SourceDocument with prior acquisition records.
    """

    status: AcquisitionStatus
    document: SourceDocument
    previous_document: Optional[SourceDocument] = None
    duplicate_documents: Tuple[SourceDocument, ...] = ()

    @property
    def should_append(self) -> bool:
        """
        Append only records that add new acquisition history.

        An unchanged file does not create another manifest entry.
        """
        return self.status is not AcquisitionStatus.UNCHANGED


class AcquisitionManifest:
    """
    Append-only JSONL manifest for SourceDocument acquisition records.

    The manifest preserves acquisition history while providing efficient
    lookup by storage-relative path and by content hash.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def read_all(self) -> List[SourceDocument]:
        if not self.path.exists():
            return []

        documents: List[SourceDocument] = []

        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()

                if not stripped:
                    continue

                try:
                    payload = json.loads(stripped)
                    documents.append(SourceDocument.from_dict(payload))
                except Exception as error:
                    raise ValueError(
                        f"Invalid acquisition manifest record at "
                        f"{self.path}:{line_number}"
                    ) from error

        return documents

    def classify(
        self,
        document: SourceDocument,
    ) -> ManifestDecision:
        existing_documents = self.read_all()

        latest_by_path = self._latest_by_path(existing_documents)
        documents_by_hash = self._documents_by_hash(existing_documents)

        previous_document = latest_by_path.get(document.relative_path)

        if (
            previous_document is not None
            and previous_document.content_hash == document.content_hash
        ):
            return ManifestDecision(
                status=AcquisitionStatus.UNCHANGED,
                document=document,
                previous_document=previous_document,
            )

        if previous_document is not None:
            return ManifestDecision(
                status=AcquisitionStatus.CHANGED,
                document=document,
                previous_document=previous_document,
            )

        duplicate_documents = tuple(
            existing
            for existing in documents_by_hash.get(
                document.content_hash,
                [],
            )
            if existing.relative_path != document.relative_path
        )

        if duplicate_documents:
            return ManifestDecision(
                status=AcquisitionStatus.DUPLICATE_CONTENT,
                document=document,
                duplicate_documents=duplicate_documents,
            )

        return ManifestDecision(
            status=AcquisitionStatus.NEW,
            document=document,
        )

    def record(
        self,
        document: SourceDocument,
    ) -> ManifestDecision:
        """
        Classify a document and append it when it adds acquisition history.
        """
        decision = self.classify(document)

        if decision.should_append:
            self.append(document)

        return decision

    def append(self, document: SourceDocument) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        serialized = json.dumps(
            document.to_dict(),
            sort_keys=True,
        )

        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.write("\n")

    def latest_documents(self) -> List[SourceDocument]:
        """
        Return the most recently recorded version of each relative path.
        """
        latest = self._latest_by_path(self.read_all())

        return sorted(
            latest.values(),
            key=lambda document: document.relative_path,
        )

    @staticmethod
    def _latest_by_path(
        documents: Iterable[SourceDocument],
    ) -> Dict[str, SourceDocument]:
        latest: Dict[str, SourceDocument] = {}

        for document in documents:
            latest[document.relative_path] = document

        return latest

    @staticmethod
    def _documents_by_hash(
        documents: Iterable[SourceDocument],
    ) -> Dict[str, List[SourceDocument]]:
        by_hash: Dict[str, List[SourceDocument]] = {}

        for document in documents:
            by_hash.setdefault(
                document.content_hash,
                [],
            ).append(document)

        return by_hash
