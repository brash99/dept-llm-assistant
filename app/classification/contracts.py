"""Auditable proposal contracts for semantic classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Tuple

from app.knowledge import KnowledgeObject
from app.semantic_identity import SemanticIdentity


class ClassificationMethod(str, Enum):
    DETERMINISTIC_RULE = "deterministic_rule"
    ADAPTER = "adapter"
    REGISTRY_LOOKUP = "registry_lookup"
    LLM = "llm"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class ProposalStage(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ClassificationConfidence:
    score: float
    rationale: Optional[str] = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("Classification confidence score must be between 0 and 1")

    def to_dict(self) -> Dict[str, Any]:
        value = {"score": self.score}
        if self.rationale is not None:
            value["rationale"] = self.rationale
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ClassificationConfidence":
        return cls(score=float(value["score"]), rationale=value.get("rationale"))


@dataclass(frozen=True)
class EvidenceCitation:
    source_kind: str
    field: Optional[str] = None
    knowledge_object_id: Optional[str] = None
    chunk_id: Optional[str] = None
    text_excerpt: Optional[str] = None
    page_reference: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.source_kind.strip():
            raise ValueError("Evidence citation source_kind must not be empty")

    def to_dict(self) -> Dict[str, Any]:
        return {
            key: value
            for key, value in {
                "source_kind": self.source_kind,
                "field": self.field,
                "knowledge_object_id": self.knowledge_object_id,
                "chunk_id": self.chunk_id,
                "text_excerpt": self.text_excerpt,
                "page_reference": self.page_reference,
            }.items()
            if value is not None
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceCitation":
        return cls(
            source_kind=str(value["source_kind"]),
            field=value.get("field"),
            knowledge_object_id=value.get("knowledge_object_id"),
            chunk_id=value.get("chunk_id"),
            text_excerpt=value.get("text_excerpt"),
            page_reference=value.get("page_reference"),
        )


@dataclass(frozen=True)
class ClassificationAssertion:
    field_name: str
    value: Any
    confidence: ClassificationConfidence
    classification_method: ClassificationMethod
    supporting_evidence: Tuple[EvidenceCitation, ...]

    def __post_init__(self) -> None:
        if not self.field_name.strip():
            raise ValueError("Classification assertion field_name must not be empty")
        if not isinstance(self.classification_method, ClassificationMethod):
            object.__setattr__(
                self,
                "classification_method",
                ClassificationMethod(self.classification_method),
            )
        object.__setattr__(self, "supporting_evidence", tuple(self.supporting_evidence))
        if not self.supporting_evidence:
            raise ValueError("Classification assertion requires supporting evidence")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "value": self.value,
            "confidence": self.confidence.to_dict(),
            "classification_method": self.classification_method.value,
            "supporting_evidence": [item.to_dict() for item in self.supporting_evidence],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ClassificationAssertion":
        return cls(
            field_name=str(value["field_name"]),
            value=value.get("value"),
            confidence=ClassificationConfidence.from_dict(value["confidence"]),
            classification_method=ClassificationMethod(value["classification_method"]),
            supporting_evidence=tuple(
                EvidenceCitation.from_dict(item)
                for item in value.get("supporting_evidence") or ()
            ),
        )


@dataclass
class ClassificationProposal:
    knowledge_object_id: str
    assertions: Tuple[ClassificationAssertion, ...]
    classifier_name: str
    stage: ProposalStage = ProposalStage.PROPOSED
    rejection_reason: Optional[str] = None

    def __post_init__(self) -> None:
        self.assertions = tuple(self.assertions)
        if not self.knowledge_object_id.strip():
            raise ValueError("Classification proposal knowledge_object_id is required")
        if not self.assertions:
            raise ValueError("Classification proposal requires at least one assertion")
        if not isinstance(self.stage, ProposalStage):
            self.stage = ProposalStage(self.stage)

    @property
    def average_confidence(self) -> float:
        return sum(item.confidence.score for item in self.assertions) / len(self.assertions)

    @property
    def minimum_confidence(self) -> float:
        return min(item.confidence.score for item in self.assertions)

    @property
    def methods(self) -> Tuple[ClassificationMethod, ...]:
        return tuple(dict.fromkeys(item.classification_method for item in self.assertions))

    def requires_review(self, threshold: float = 0.8) -> bool:
        return self.minimum_confidence < threshold

    def accept(self) -> None:
        if self.stage == ProposalStage.REJECTED:
            raise ValueError("Rejected proposal cannot be accepted")
        self.stage = ProposalStage.ACCEPTED
        self.rejection_reason = None

    def reject(self, reason: str) -> None:
        if not reason.strip():
            raise ValueError("Rejected proposal requires a reason")
        if self.stage == ProposalStage.ACCEPTED:
            raise ValueError("Accepted proposal cannot be rejected")
        self.stage = ProposalStage.REJECTED
        self.rejection_reason = reason

    def proposed_identity(self) -> SemanticIdentity:
        fields: Dict[str, Any] = {}
        for assertion in self.assertions:
            if assertion.field_name in fields:
                raise ValueError(
                    f"Proposal contains duplicate identity field {assertion.field_name!r}"
                )
            fields[assertion.field_name] = assertion.value
        return SemanticIdentity.from_dict(fields)

    def apply_to_knowledge_object(self, knowledge_object: KnowledgeObject) -> None:
        if self.stage != ProposalStage.ACCEPTED:
            raise ValueError("Only an accepted proposal may be applied")
        if knowledge_object.id != self.knowledge_object_id:
            raise ValueError("Proposal does not belong to this Knowledge Object")
        knowledge_object.set_semantic_identity(self.proposed_identity())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_object_id": self.knowledge_object_id,
            "classifier_name": self.classifier_name,
            "stage": self.stage.value,
            "rejection_reason": self.rejection_reason,
            "average_confidence": self.average_confidence,
            "assertions": [item.to_dict() for item in self.assertions],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ClassificationProposal":
        return cls(
            knowledge_object_id=str(value["knowledge_object_id"]),
            classifier_name=str(value["classifier_name"]),
            stage=ProposalStage(value.get("stage", ProposalStage.PROPOSED.value)),
            rejection_reason=value.get("rejection_reason"),
            assertions=tuple(
                ClassificationAssertion.from_dict(item)
                for item in value.get("assertions") or ()
            ),
        )


@dataclass(frozen=True)
class ClassificationResult:
    proposal: ClassificationProposal
    applied: bool = False
    automatically_accepted: bool = False


__all__ = [
    "ClassificationAssertion",
    "ClassificationConfidence",
    "ClassificationMethod",
    "ClassificationProposal",
    "ClassificationResult",
    "EvidenceCitation",
    "ProposalStage",
]
