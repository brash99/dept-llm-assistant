from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional
import hashlib
import json


def _json_default(value: Any):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


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

    @property
    def semantic_identity(self):
        """Return the authoritative factual identity, when one is recorded."""
        value = self.metadata.get("semantic_identity")
        if value is None:
            return None
        from app.semantic_identity import SemanticIdentity

        identity = (
            value
            if isinstance(value, SemanticIdentity)
            else SemanticIdentity.from_dict(value)
        )
        if identity.object_type != self.object_type:
            raise ValueError(
                "Semantic identity object_type must match Knowledge Object object_type"
            )
        return identity

    def set_semantic_identity(self, identity) -> None:
        """Validate and store factual identity without changing object identity."""
        from app.semantic_identity import SemanticIdentity

        if not isinstance(identity, SemanticIdentity):
            raise TypeError("identity must be a SemanticIdentity")
        if identity.object_type != self.object_type:
            raise ValueError(
                "Semantic identity object_type must match Knowledge Object object_type"
            )
        self.metadata["semantic_identity"] = identity.to_dict()

    @property
    def semantic_memberships(self):
        """Logical perspectives in which this factual object participates."""
        return tuple(self.metadata.get("semantic_memberships") or ())

    @property
    def organizational_relationships(self):
        identity = self.semantic_identity
        if identity is not None:
            return tuple(
                relationship.to_dict()
                for relationship in identity.organizational_relationships
            )
        return tuple(self.metadata.get("organizational_relationships") or ())

    @property
    def decision_domains(self):
        identity = self.semantic_identity
        if identity is not None:
            return identity.decision_domains
        return tuple(self.metadata.get("decision_domains") or ())

    @property
    def institutional_relevance(self):
        identity = self.semantic_identity
        if identity is not None:
            return identity.institutional_relevance
        return self.metadata.get("institutional_relevance")

    @property
    def institutional_entities(self):
        identity = self.semantic_identity
        return identity.institutional_entities if identity is not None else ()

    @property
    def authority(self):
        identity = self.semantic_identity
        return identity.authority if identity is not None else None

    @property
    def temporal_scope(self):
        identity = self.semantic_identity
        return identity.temporal_scope if identity is not None else None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), default=_json_default, indent=indent)

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
        json.dump(obj.to_dict(), f, default=_json_default, indent=2)


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

    if object_type == "course_offering_observation":
        from app.adapters.schedule_adapter import CourseOfferingObservation

        return CourseOfferingObservation.from_dict(data)

    if object_type == "faculty_observation":
        from app.adapters.faculty_adapter import FacultyObservation

        return FacultyObservation.from_dict(data)

    if object_type in {
        "catalog_observation",
        "academic_unit_observation",
        "department_faculty_roster_observation",
        "catalog_faculty_observation",
    }:
        from app.adapters.catalog_adapter import catalog_observation_from_dict

        return catalog_observation_from_dict(data)

    return KnowledgeObject(**data)
