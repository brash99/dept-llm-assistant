from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import hashlib
import json


@dataclass
class KnowledgeObject:
    """
    Base semantic unit in the AI pipeline.

    A KnowledgeObject is anything that can be normalized into text plus metadata:
    documents, database records, course records, budget records, policies, etc.
    """

    id: str
    object_type: str
    title: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    normalized_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)


@dataclass
class Document(KnowledgeObject):
    """
    A KnowledgeObject derived from a filesystem document.
    """

    source_path: str = ""
    relative_path: str = ""
    file_type: str = ""
    parser: str = ""
    size_bytes: int = 0
    modified_at: Optional[str] = None
    content_hash: Optional[str] = None


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    sha = hashlib.sha256()

    with Path(path).open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha.update(chunk)

    return sha.hexdigest()


def make_document_id(relative_path: str, content_hash: Optional[str] = None) -> str:
    """
    Stable-ish document id.

    If content_hash is available, use path + hash.
    If not, use path only.
    """

    base = relative_path

    if content_hash:
        base = f"{relative_path}:{content_hash}"

    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def document_from_text(
    source_path: Path,
    root_path: Path,
    text: str,
    parser: str,
    title: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Document:
    """
    Convenience constructor for parsers.

    A parser can extract text, then call this function to create a normalized
    Document object.
    """

    source_path = Path(source_path).resolve()
    root_path = Path(root_path).resolve()
    relative_path = str(source_path.relative_to(root_path))

    stat = source_path.stat()
    file_hash = hash_file(source_path)

    if title is None:
        title = source_path.stem

    if metadata is None:
        metadata = {}

    doc_id = make_document_id(relative_path, file_hash)

    return Document(
        id=doc_id,
        object_type="document",
        title=title,
        text=text,
        metadata=metadata,
        source={
            "kind": "filesystem",
            "path": str(source_path),
            "relative_path": relative_path,
        },
        created_at=None,
        normalized_at=now_iso(),
        source_path=str(source_path),
        relative_path=relative_path,
        file_type=source_path.suffix.lower(),
        parser=parser,
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        content_hash=file_hash,
    )


def save_knowledge_object(obj: KnowledgeObject, output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(obj.to_dict(), f, indent=2)


def load_knowledge_object(input_path: Path) -> KnowledgeObject:
    input_path = Path(input_path)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    object_type = data.get("object_type")

    if object_type == "document":
        return Document(**data)

    if object_type == "constitutional_knowledge":
        from app.constitution.objects import (
            ConstitutionalKnowledgeObject,
        )

        return ConstitutionalKnowledgeObject.from_dict(
            data
        )

    return KnowledgeObject(**data)
