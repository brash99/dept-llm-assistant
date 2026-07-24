"""Field-level governance for semantic classification proposals."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from app.classification.classifiers import ClassificationAbstained, SemanticClassifier
from app.institutional_units import is_department_workforce_entity
from app.classification.contracts import (
    ClassificationAssertion,
    ClassificationMethod,
    ClassificationProposal,
)
from app.knowledge import KnowledgeObject
from app.semantic_identity import SemanticIdentity


IDENTITY_FIELDS = (
    "object_type",
    "institutional_entities",
    "organizational_relationships",
    "decision_domains",
    "authority",
    "temporal_scope",
    "institutional_relevance",
    "source_family",
    "document_type",
    "institutional_role",
)
POLICY_VERSION = "3"
MULTIVALUE_FIELDS = {
    "institutional_entities",
    "organizational_relationships",
    "decision_domains",
}


class ClassificationDisposition(str, Enum):
    AUTO_ACCEPT = "auto_accept"
    ACCEPT_WITH_AUDIT = "accept_with_audit"
    REVIEW = "review"
    ABSTAIN = "abstain"
    REJECT = "reject"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class PolicyReason:
    code: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "message": self.message}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PolicyReason":
        return cls(code=str(value["code"]), message=str(value["message"]))


@dataclass(frozen=True)
class ClassificationConflict:
    field_name: str
    proposed_value: Any
    competing_value: Any
    competing_source: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "proposed_value": self.proposed_value,
            "competing_value": self.competing_value,
            "competing_source": self.competing_source,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class FieldPolicy:
    field_name: str
    automatic_thresholds: Mapping[ClassificationMethod, float]
    review_thresholds: Mapping[ClassificationMethod, float]
    audit_required: bool = False
    citation_required: bool = True

    def automatic_threshold(self, method: ClassificationMethod) -> Optional[float]:
        return self.automatic_thresholds.get(method)

    def review_threshold(self, method: ClassificationMethod) -> Optional[float]:
        return self.review_thresholds.get(method)


@dataclass(frozen=True)
class AssertionDecision:
    assertion: ClassificationAssertion
    disposition: ClassificationDisposition
    reasons: Tuple[PolicyReason, ...]
    conflicts: Tuple[ClassificationConflict, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.disposition in {
            ClassificationDisposition.AUTO_ACCEPT,
            ClassificationDisposition.ACCEPT_WITH_AUDIT,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assertion": self.assertion.to_dict(),
            "disposition": self.disposition.value,
            "reasons": [reason.to_dict() for reason in self.reasons],
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AssertionDecision":
        return cls(
            assertion=ClassificationAssertion.from_dict(value["assertion"]),
            disposition=ClassificationDisposition(value["disposition"]),
            reasons=tuple(
                PolicyReason.from_dict(reason) for reason in value.get("reasons") or ()
            ),
            conflicts=tuple(
                ClassificationConflict(**conflict)
                for conflict in value.get("conflicts") or ()
            ),
        )


@dataclass(frozen=True)
class ClassificationDecision:
    knowledge_object_id: str
    classifier_name: str
    assertion_decisions: Tuple[AssertionDecision, ...]

    @property
    def accepted_assertions(self) -> Tuple[ClassificationAssertion, ...]:
        return tuple(
            item.assertion for item in self.assertion_decisions if item.accepted
        )

    @property
    def disposition(self) -> ClassificationDisposition:
        dispositions = {item.disposition for item in self.assertion_decisions}
        precedence = (
            ClassificationDisposition.CONFLICT,
            ClassificationDisposition.REJECT,
            ClassificationDisposition.REVIEW,
            ClassificationDisposition.ABSTAIN,
            ClassificationDisposition.ACCEPT_WITH_AUDIT,
            ClassificationDisposition.AUTO_ACCEPT,
        )
        return next(value for value in precedence if value in dispositions)

    @property
    def has_conflicts(self) -> bool:
        return any(item.conflicts for item in self.assertion_decisions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_object_id": self.knowledge_object_id,
            "classifier_name": self.classifier_name,
            "disposition": self.disposition.value,
            "assertion_decisions": [item.to_dict() for item in self.assertion_decisions],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ClassificationDecision":
        return cls(
            knowledge_object_id=str(value["knowledge_object_id"]),
            classifier_name=str(value["classifier_name"]),
            assertion_decisions=tuple(
                AssertionDecision.from_dict(item)
                for item in value.get("assertion_decisions") or ()
            ),
        )

    def apply_to_knowledge_object(self, knowledge_object: KnowledgeObject) -> bool:
        """Merge accepted fields only and append idempotent policy provenance."""
        if knowledge_object.id != self.knowledge_object_id:
            raise ValueError("Classification decision does not belong to this object")
        accepted = self.accepted_assertions
        if not accepted:
            raise ValueError("Classification decision contains no accepted assertions")

        current = (
            knowledge_object.semantic_identity.to_dict()
            if knowledge_object.semantic_identity is not None
            else {"object_type": knowledge_object.object_type}
        )
        for assertion in accepted:
            field_name = assertion.field_name
            value = assertion.value
            if field_name == "institutional_entities":
                current[field_name] = _merge_institutional_entities(
                    current.get(field_name) or (), value or (),
                    _superseded_entity_ids(assertion),
                )
            elif field_name in MULTIVALUE_FIELDS:
                existing_values = list(current.get(field_name) or ())
                proposed_values = list(value or ())
                current[field_name] = _stable_union(existing_values, proposed_values)
            elif field_name == "institutional_relevance":
                current[field_name] = {
                    **dict(current.get(field_name) or {}),
                    **dict(value or {}),
                }
            else:
                current[field_name] = value

        identity = SemanticIdentity.from_dict(current)
        knowledge_object.set_semantic_identity(identity)

        provenance = knowledge_object.metadata.setdefault(
            "classification_provenance", []
        )
        record = {
            "classifier_name": self.classifier_name,
            "accepted_fields": sorted(item.field_name for item in accepted),
            "assertion_methods": sorted(
                {item.classification_method.value for item in accepted}
            ),
            "accepted_assertions": [item.to_dict() for item in accepted],
            "decision_fingerprint": self.fingerprint(),
        }
        if not any(
            item.get("decision_fingerprint") == record["decision_fingerprint"]
            for item in provenance
        ):
            provenance.append(record)
        return True

    def fingerprint(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ClassificationAbstention:
    knowledge_object_id: str
    classifier_name: Optional[str]
    reasons: Tuple[PolicyReason, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_object_id": self.knowledge_object_id,
            "classifier_name": self.classifier_name,
            "reasons": [reason.to_dict() for reason in self.reasons],
        }


def _default_thresholds() -> Tuple[Dict[ClassificationMethod, float], Dict[ClassificationMethod, float]]:
    automatic = {
        ClassificationMethod.ADAPTER: 0.95,
        ClassificationMethod.DETERMINISTIC_RULE: 0.95,
        ClassificationMethod.REGISTRY_LOOKUP: 0.98,
        ClassificationMethod.MANUAL: 0.0,
    }
    review = {
        ClassificationMethod.ADAPTER: 0.70,
        ClassificationMethod.DETERMINISTIC_RULE: 0.70,
        ClassificationMethod.REGISTRY_LOOKUP: 0.80,
        ClassificationMethod.LLM: 0.70,
        ClassificationMethod.MANUAL: 0.0,
    }
    return automatic, review


def default_field_policies() -> Dict[str, FieldPolicy]:
    automatic, review = _default_thresholds()
    policies = {
        field_name: FieldPolicy(field_name, dict(automatic), dict(review))
        for field_name in IDENTITY_FIELDS
    }
    for field_name in (
        "authority",
        "organizational_relationships",
        "decision_domains",
        "institutional_relevance",
        "document_type",
        "institutional_role",
    ):
        policies[field_name] = FieldPolicy(
            field_name,
            dict(automatic),
            dict(review),
            audit_required=True,
        )
    return policies


class ClassificationPolicy:
    """Evaluate each assertion using method, evidence, confidence, and conflict."""

    def __init__(self, field_policies: Optional[Mapping[str, FieldPolicy]] = None):
        self.field_policies = dict(field_policies or default_field_policies())

    def evaluate(
        self,
        proposal: ClassificationProposal,
        *,
        knowledge_object: Optional[KnowledgeObject] = None,
        competing_proposals: Sequence[ClassificationProposal] = (),
    ) -> ClassificationDecision:
        conflicts = self.detect_conflicts(
            proposal,
            knowledge_object=knowledge_object,
            competing_proposals=competing_proposals,
        )
        by_field: Dict[str, list[ClassificationConflict]] = defaultdict(list)
        for conflict in conflicts:
            by_field[conflict.field_name].append(conflict)
        decisions = tuple(
            self._evaluate_assertion(
                assertion,
                tuple(by_field[assertion.field_name]),
                classifier_name=proposal.classifier_name,
            )
            for assertion in proposal.assertions
        )
        return ClassificationDecision(
            proposal.knowledge_object_id, proposal.classifier_name, decisions
        )

    def _evaluate_assertion(
        self,
        assertion: ClassificationAssertion,
        conflicts: Tuple[ClassificationConflict, ...],
        *,
        classifier_name: str,
    ) -> AssertionDecision:
        if conflicts:
            return AssertionDecision(
                assertion,
                ClassificationDisposition.CONFLICT,
                (PolicyReason("conflict", "Competing factual values require review."),),
                conflicts,
            )
        policy = self.field_policies.get(assertion.field_name)
        if policy is None:
            return AssertionDecision(
                assertion,
                ClassificationDisposition.REJECT,
                (PolicyReason("unknown_field", "Field is not part of SemanticIdentity."),),
            )
        if policy.citation_required and not _citations_are_adequate(
            assertion.supporting_evidence
        ):
            return AssertionDecision(
                assertion,
                ClassificationDisposition.ABSTAIN,
                (PolicyReason("insufficient_evidence", "A usable citation is required."),),
            )
        if assertion.classification_method == ClassificationMethod.UNKNOWN:
            return AssertionDecision(
                assertion,
                ClassificationDisposition.ABSTAIN,
                (PolicyReason("unknown_method", "Unknown classification methods abstain."),),
            )
        if (
            assertion.classification_method == ClassificationMethod.DETERMINISTIC_RULE
            and not _deterministic_rule_evidence_is_adequate(
                assertion.supporting_evidence
            )
        ):
            return AssertionDecision(
                assertion,
                ClassificationDisposition.REVIEW,
                (
                    PolicyReason(
                        "unregistered_or_ambiguous_rule",
                        "Automatic acceptance requires a registered, satisfied, unambiguous rule.",
                    ),
                ),
            )
        if (
            assertion.classification_method == ClassificationMethod.REGISTRY_LOOKUP
            and not _registry_evidence_is_adequate(assertion.supporting_evidence)
        ):
            return AssertionDecision(
                assertion,
                ClassificationDisposition.REVIEW,
                (
                    PolicyReason(
                        "ambiguous_registry_lookup",
                        "Automatic acceptance requires a unique canonical registry match.",
                    ),
                ),
            )
        if not _assertion_value_valid(assertion):
            return AssertionDecision(
                assertion,
                ClassificationDisposition.REJECT,
                (PolicyReason("invalid_value", "Assertion value fails identity validation."),),
            )

        automatic_threshold = policy.automatic_threshold(
            assertion.classification_method
        )
        if (
            automatic_threshold is not None
            and assertion.confidence.score >= automatic_threshold
        ):
            disposition = (
                ClassificationDisposition.ACCEPT_WITH_AUDIT
                if policy.audit_required
                or (
                    assertion.field_name == "institutional_entities"
                    and (
                        classifier_name == "constitutional_knowledge_classifier"
                        or classifier_name.endswith("_document_classifier")
                    )
                )
                else ClassificationDisposition.AUTO_ACCEPT
            )
            return AssertionDecision(
                assertion,
                disposition,
                (
                    PolicyReason(
                        "validated_acceptance",
                        "Method, confidence, evidence, and field policy permit acceptance.",
                    ),
                ),
            )

        review_threshold = policy.review_threshold(assertion.classification_method)
        if (
            review_threshold is not None
            and assertion.confidence.score >= review_threshold
        ):
            return AssertionDecision(
                assertion,
                ClassificationDisposition.REVIEW,
                (
                    PolicyReason(
                        "review_required",
                        "Assertion is plausible but not eligible for automatic acceptance.",
                    ),
                ),
            )
        return AssertionDecision(
            assertion,
            ClassificationDisposition.ABSTAIN,
            (
                PolicyReason(
                    "below_policy_threshold",
                    "Evidence or confidence is insufficient for review or acceptance.",
                ),
            ),
        )

    def detect_conflicts(
        self,
        proposal: ClassificationProposal,
        *,
        knowledge_object: Optional[KnowledgeObject] = None,
        competing_proposals: Sequence[ClassificationProposal] = (),
    ) -> Tuple[ClassificationConflict, ...]:
        conflicts = []
        current = (
            knowledge_object.semantic_identity.to_dict()
            if knowledge_object is not None and knowledge_object.semantic_identity
            else {}
        )
        for assertion in proposal.assertions:
            if (
                knowledge_object is not None
                and assertion.field_name == "object_type"
                and assertion.value != knowledge_object.object_type
            ):
                conflicts.append(
                    ClassificationConflict(
                        assertion.field_name,
                        assertion.value,
                        knowledge_object.object_type,
                        "knowledge_object.object_type",
                        "Proposal object type disagrees with its Knowledge Object.",
                    )
                )
            existing_value = current.get(assertion.field_name)
            if assertion.field_name == "institutional_entities":
                superseded = _superseded_entity_ids(assertion)
                existing_value = [
                    item for item in (existing_value or ())
                    if item.get("entity_id") not in superseded
                ]
            if assertion.field_name in current and _values_conflict(
                assertion.field_name, assertion.value, existing_value
            ):
                conflicts.append(
                    ClassificationConflict(
                        assertion.field_name,
                        assertion.value,
                        current[assertion.field_name],
                        "existing_semantic_identity",
                        "New proposal disagrees with accepted semantic identity.",
                    )
                )
            for other in proposal.assertions:
                if (
                    other is not assertion
                    and other.field_name == assertion.field_name
                    and _values_conflict(
                        assertion.field_name, assertion.value, other.value
                    )
                ):
                    conflicts.append(
                        ClassificationConflict(
                            assertion.field_name,
                            assertion.value,
                            other.value,
                            proposal.classifier_name,
                            "One classifier proposed incompatible values.",
                        )
                    )
            for competing in competing_proposals:
                for other in competing.assertions:
                    if (
                        other.field_name == assertion.field_name
                        and _values_conflict(
                            assertion.field_name, assertion.value, other.value
                        )
                    ):
                        conflicts.append(
                            ClassificationConflict(
                                assertion.field_name,
                                assertion.value,
                                other.value,
                                competing.classifier_name,
                                "Classifiers proposed incompatible values.",
                            )
                        )
        return tuple(conflicts)


@dataclass(frozen=True)
class AuditCandidate:
    decision: ClassificationDecision
    object_type: str

    @property
    def key(self) -> str:
        return f"{self.decision.knowledge_object_id}:{self.decision.classifier_name}"


@dataclass(frozen=True)
class AuditSelection:
    selected_keys: Tuple[str, ...]
    reasons: Mapping[str, Tuple[str, ...]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_keys": list(self.selected_keys),
            "reasons": {key: list(values) for key, values in self.reasons.items()},
        }


@dataclass(frozen=True)
class AuditPolicy:
    percentage: float = 0.05
    minimum_per_classifier: int = 1
    minimum_per_object_type: int = 1
    near_threshold_margin: float = 0.01
    seed: str = "iso-classification-audit-v1"

    def __post_init__(self) -> None:
        if not 0.0 <= self.percentage <= 1.0:
            raise ValueError("Audit percentage must be between 0 and 1")

    def select(self, candidates: Sequence[AuditCandidate]) -> AuditSelection:
        eligible = [candidate for candidate in candidates if candidate.decision.accepted_assertions]
        selected: Dict[str, set[str]] = defaultdict(set)
        for candidate in eligible:
            if any(
                item.disposition == ClassificationDisposition.ACCEPT_WITH_AUDIT
                for item in candidate.decision.assertion_decisions
            ):
                selected[candidate.key].add("field_policy")
            if _audit_fraction(self.seed, candidate.key) < self.percentage:
                selected[candidate.key].add("percentage_sample")
            if any(
                item.accepted
                and min(
                    abs(item.assertion.confidence.score - threshold)
                    for threshold in (0.95, 0.98)
                ) <= self.near_threshold_margin
                for item in candidate.decision.assertion_decisions
            ):
                selected[candidate.key].add("near_policy_threshold")

        self._ensure_minimum(
            eligible,
            selected,
            key=lambda item: item.decision.classifier_name,
            minimum=self.minimum_per_classifier,
            reason="minimum_per_classifier",
        )
        self._ensure_minimum(
            eligible,
            selected,
            key=lambda item: item.object_type,
            minimum=self.minimum_per_object_type,
            reason="minimum_per_object_type",
        )
        return AuditSelection(
            selected_keys=tuple(sorted(selected)),
            reasons={key: tuple(sorted(values)) for key, values in sorted(selected.items())},
        )

    def _ensure_minimum(
        self,
        candidates: Sequence[AuditCandidate],
        selected: Dict[str, set[str]],
        *,
        key,
        minimum: int,
        reason: str,
    ) -> None:
        groups: Dict[str, list[AuditCandidate]] = defaultdict(list)
        for candidate in candidates:
            groups[str(key(candidate))].append(candidate)
        for group in groups.values():
            already = sum(item.key in selected for item in group)
            ordered = sorted(
                (item for item in group if item.key not in selected),
                key=lambda item: (_audit_fraction(self.seed, item.key), item.key),
            )
            for candidate in ordered[: max(0, minimum - already)]:
                selected[candidate.key].add(reason)


@dataclass(frozen=True)
class GovernedClassificationResult:
    proposal: Optional[ClassificationProposal] = None
    decision: Optional[ClassificationDecision] = None
    abstention: Optional[ClassificationAbstention] = None
    applied: bool = False


class ClassificationGovernor:
    """Run one classifier selection, policy evaluation, and optional safe apply."""

    def __init__(
        self,
        classifiers: Sequence[SemanticClassifier],
        policy: Optional[ClassificationPolicy] = None,
    ) -> None:
        self.classifiers = tuple(classifiers)
        self.policy = policy or ClassificationPolicy()

    def classify(
        self,
        knowledge_object: KnowledgeObject,
        *,
        apply: bool = False,
        competing_proposals: Sequence[ClassificationProposal] = (),
    ) -> GovernedClassificationResult:
        classifier = next(
            (item for item in self.classifiers if item.supports(knowledge_object)), None
        )
        if classifier is None:
            return GovernedClassificationResult(
                abstention=ClassificationAbstention(
                    knowledge_object.id,
                    None,
                    (
                        PolicyReason(
                            "unsupported_object_type",
                            f"No classifier supports {knowledge_object.object_type!r}.",
                        ),
                    ),
                )
            )
        try:
            proposal = classifier.classify(knowledge_object)
        except ClassificationAbstained as exc:
            return GovernedClassificationResult(
                abstention=ClassificationAbstention(
                    knowledge_object.id,
                    classifier.name,
                    (PolicyReason(exc.code, exc.message),),
                )
            )
        decision = self.policy.evaluate(
            proposal,
            knowledge_object=knowledge_object,
            competing_proposals=competing_proposals,
        )
        applied = False
        if apply and decision.accepted_assertions:
            applied = decision.apply_to_knowledge_object(knowledge_object)
        return GovernedClassificationResult(proposal, decision, None, applied)


def _citations_are_adequate(citations) -> bool:
    return bool(citations) and all(
        citation.source_kind.strip()
        and any(
            (
                citation.field,
                citation.knowledge_object_id,
                citation.chunk_id,
                citation.text_excerpt,
                citation.page_reference,
            )
        )
        for citation in citations
    )


def _assertion_value_valid(assertion: ClassificationAssertion) -> bool:
    try:
        payload = {"object_type": "validation_object"}
        if assertion.field_name == "object_type":
            payload["object_type"] = assertion.value
        else:
            payload[assertion.field_name] = assertion.value
        SemanticIdentity.from_dict(payload)
        return True
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def _deterministic_rule_evidence_is_adequate(citations) -> bool:
    return any(
        citation.attributes.get("registered_rule") is True
        and citation.attributes.get("predicates_satisfied") is True
        and citation.attributes.get("unambiguous") is True
        for citation in citations
    )


def _registry_evidence_is_adequate(citations) -> bool:
    return any(
        citation.attributes.get("unique_match") is True
        and citation.attributes.get("canonical_entity_exists") is True
        and not citation.attributes.get("competing_match_above_threshold", False)
        for citation in citations
    )


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _values_conflict(field_name: str, left: Any, right: Any) -> bool:
    if _canonical(left) == _canonical(right):
        return False
    if field_name == "institutional_entities":
        left_departments = {
            item.get("entity_id")
            for item in left or ()
            if is_department_workforce_entity(item)
        }
        right_departments = {
            item.get("entity_id")
            for item in right or ()
            if is_department_workforce_entity(item)
        }
        return bool(left_departments and right_departments and left_departments != right_departments)
    if field_name == "organizational_relationships":
        return _exclusive_relationship_conflict(left or (), right or ())
    if field_name in MULTIVALUE_FIELDS:
        return False
    return True


def _exclusive_relationship_conflict(left: Iterable[Mapping[str, Any]], right: Iterable[Mapping[str, Any]]) -> bool:
    exclusive = {"belongs_to", "published_by", "governs"}
    left_keys = {
        (item.get("relationship_type"), item.get("source")): item.get("target")
        for item in left
        if item.get("relationship_type") in exclusive
    }
    right_keys = {
        (item.get("relationship_type"), item.get("source")): item.get("target")
        for item in right
        if item.get("relationship_type") in exclusive
    }
    return any(key in right_keys and right_keys[key] != target for key, target in left_keys.items())


def _stable_union(existing: Sequence[Any], proposed: Sequence[Any]) -> list[Any]:
    values = list(existing)
    seen = {_canonical(item) for item in values}
    for item in proposed:
        marker = _canonical(item)
        if marker not in seen:
            seen.add(marker)
            values.append(item)
    return values


def _superseded_entity_ids(assertion: ClassificationAssertion) -> set[str]:
    return {
        str(entity_id)
        for citation in assertion.supporting_evidence
        for entity_id in citation.attributes.get("supersedes_entity_ids") or ()
    }


def _merge_institutional_entities(existing, proposed, superseded) -> list[Any]:
    proposed_ids = {
        item.get("entity_id") for item in proposed if isinstance(item, Mapping)
    }
    values = [
        item for item in existing
        if not isinstance(item, Mapping)
        or (
            item.get("entity_id") not in superseded
            and item.get("entity_id") not in proposed_ids
        )
    ]
    return _stable_union(values, proposed)


def _audit_fraction(seed: str, key: str) -> float:
    digest = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


__all__ = [
    "AssertionDecision",
    "AuditCandidate",
    "AuditPolicy",
    "AuditSelection",
    "ClassificationAbstention",
    "ClassificationConflict",
    "ClassificationDecision",
    "ClassificationDisposition",
    "ClassificationGovernor",
    "ClassificationPolicy",
    "FieldPolicy",
    "GovernedClassificationResult",
    "PolicyReason",
    "POLICY_VERSION",
    "default_field_policies",
]
