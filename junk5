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
        return self.status is not AcquisitionStatus.UNCHANGED


class AcquisitionManifest:
    """
    Append-only JSONL manifest with in-memory lookup indexes.

    The manifest is read once, on first use. Subsequent classifications use
    dictionaries maintained in memory, avoiding an O(N^2) full-manifest scan
    during large directory acquisitions.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

        self._loaded = False
        self._documents: List[SourceDocument] = []
        self._latest_by_path_index: Dict[str, SourceDocument] = {}
        self._documents_by_hash_index: Dict[
            str,
            List[SourceDocument],
        ] = {}

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        self._documents = self._read_from_disk()
        self._rebuild_indexes()
        self._loaded = True

    def _read_from_disk(self) -> List[SourceDocument]:
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
                    document = SourceDocument.from_dict(payload)
                except Exception as error:
                    raise ValueError(
                        "Invalid acquisition manifest record at "
                        f"{self.path}:{line_number}"
                    ) from error

                documents.append(document)

        return documents

    def _rebuild_indexes(self) -> None:
        self._latest_by_path_index = {}
        self._documents_by_hash_index = {}

        for document in self._documents:
            self._index_document(document)

    def _index_document(
        self,
        document: SourceDocument,
    ) -> None:
        self._latest_by_path_index[
            document.relative_path
        ] = document

        self._documents_by_hash_index.setdefault(
            document.content_hash,
            [],
        ).append(document)

    def read_all(self) -> List[SourceDocument]:
        self._ensure_loaded()
        return list(self._documents)

    def classify(
        self,
        document: SourceDocument,
    ) -> ManifestDecision:
        self._ensure_loaded()

        previous_document = self._latest_by_path_index.get(
            document.relative_path
        )

        if (
            previous_document is not None
            and previous_document.content_hash
            == document.content_hash
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
            for existing in self._documents_by_hash_index.get(
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
        decision = self.classify(document)

        if decision.should_append:
            self.append(document)

        return decision

    def append(self, document: SourceDocument) -> None:
        self._ensure_loaded()

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

        self._documents.append(document)
        self._index_document(document)

    def latest_documents(self) -> List[SourceDocument]:
        self._ensure_loaded()

        return sorted(
            self._latest_by_path_index.values(),
            key=lambda document: document.relative_path,
        )

    def reload(self) -> None:
        """
        Explicitly discard cached state and reread the manifest from disk.

        This is useful only when another process may have modified the same
        manifest while this object remained alive.
        """
        self._loaded = False
        self._documents = []
        self._latest_by_path_index = {}
        self._documents_by_hash_index = {}
        self._ensure_loaded()

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
