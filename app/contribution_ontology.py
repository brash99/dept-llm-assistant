"""Core semantic contracts for institutional contribution.

Contribution is part of ISO's institutional ontology.  These contracts model
institutional function; they do not evaluate importance, recommend action, or
format reports.  Deterministic builders may create these objects from governed
evidence in later modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json
import re
from typing import Any, Generic, Mapping, TypeVar

from app.semantic_identity import InstitutionalEntity


_FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _nonempty(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _json_mapping(value: Mapping[str, Any], field_name: str) -> dict[str, Any]:
    result = dict(value)
    try:
        _canonical_json(result)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must contain JSON-serializable values") from exc
    return result


@dataclass(frozen=True)
class ContributionPeriod:
    """One labeled or bounded period within contribution temporal scope."""

    start: str | None = None
    end: str | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        if not any((self.start, self.end, self.label)):
            raise ValueError("Contribution period must contain a bound or label")
        if self.start and self.end and self.start > self.end:
            raise ValueError("Contribution period start must not follow end")

    def to_dict(self) -> dict[str, str]:
        return {
            key: value
            for key, value in (
                ("start", self.start),
                ("end", self.end),
                ("label", self.label),
            )
            if value is not None
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContributionPeriod":
        return cls(
            start=value.get("start"),
            end=value.get("end"),
            label=value.get("label"),
        )


@dataclass(frozen=True)
class ContributionTemporalScope:
    """The four distinct temporal dimensions of a contribution fact.

    ``reporting_period`` is the interval summarized by attached measures.
    ``effective_period`` is when the institutional relationship is in force.
    ``observation_period`` is when supporting evidence was observed.
    ``publication_time`` is when this semantic object was published.
    """

    reporting_period: ContributionPeriod | None = None
    effective_period: ContributionPeriod | None = None
    observation_period: ContributionPeriod | None = None
    publication_time: str | None = None

    def __post_init__(self) -> None:
        if not any(
            (
                self.reporting_period,
                self.effective_period,
                self.observation_period,
                self.publication_time,
            )
        ):
            raise ValueError("Contribution temporal scope must not be empty")
        for name in ("reporting_period", "effective_period", "observation_period"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, ContributionPeriod):
                raise TypeError(f"{name} must be a ContributionPeriod")
        if self.publication_time:
            try:
                datetime.fromisoformat(self.publication_time.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("publication_time must be ISO-8601") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in (
                (
                    "reporting_period",
                    self.reporting_period.to_dict()
                    if self.reporting_period else None,
                ),
                (
                    "effective_period",
                    self.effective_period.to_dict()
                    if self.effective_period else None,
                ),
                (
                    "observation_period",
                    self.observation_period.to_dict()
                    if self.observation_period else None,
                ),
                ("publication_time", self.publication_time),
            )
            if value is not None
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContributionTemporalScope":
        def period(name: str) -> ContributionPeriod | None:
            item = value.get(name)
            return ContributionPeriod.from_dict(item) if item else None

        return cls(
            reporting_period=period("reporting_period"),
            effective_period=period("effective_period"),
            observation_period=period("observation_period"),
            publication_time=value.get("publication_time"),
        )


class ContributionPredicate(str, Enum):
    """Initial governed vocabulary of institutional contribution relations."""

    ADMINISTERS_PROGRAM = "administers_program"
    SUPPORTS_PROGRAM = "supports_program"
    PROVIDES_SERVICE_TEACHING_FOR = "provides_service_teaching_for"
    DELIVERS_INSTRUCTION_FOR = "delivers_instruction_for"
    CONTRIBUTES_TO_LLC_REQUIREMENT = "contributes_to_llc_requirement"


@dataclass(frozen=True)
class ContributionEvidenceBinding:
    """Epistemic grounding for an ontological contribution assertion."""

    binding_id: str
    source_references: tuple[str, ...]
    provenance: Mapping[str, Any]
    builder: str
    builder_version: str
    source_fingerprints: Mapping[str, str]
    derivation_basis: str

    def __post_init__(self) -> None:
        _nonempty(self.binding_id, "binding_id")
        if not self.source_references:
            raise ValueError("Evidence binding requires source references")
        if any(not str(value).strip() for value in self.source_references):
            raise ValueError("Evidence source references must not be empty")
        _nonempty(self.builder, "builder")
        _nonempty(self.builder_version, "builder_version")
        _nonempty(self.derivation_basis, "derivation_basis")
        provenance = _json_mapping(self.provenance, "provenance")
        fingerprints = dict(self.source_fingerprints)
        for source, digest in fingerprints.items():
            _nonempty(source, "source fingerprint key")
            if not _FINGERPRINT_PATTERN.fullmatch(str(digest)):
                raise ValueError(f"Invalid source fingerprint for {source}")
        object.__setattr__(self, "source_references", tuple(self.source_references))
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "source_fingerprints", fingerprints)

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "source_references": list(self.source_references),
            "provenance": dict(self.provenance),
            "builder": self.builder,
            "builder_version": self.builder_version,
            "source_fingerprints": dict(sorted(self.source_fingerprints.items())),
            "derivation_basis": self.derivation_basis,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContributionEvidenceBinding":
        return cls(
            binding_id=str(value["binding_id"]),
            source_references=tuple(map(str, value.get("source_references") or ())),
            provenance=dict(value.get("provenance") or {}),
            builder=str(value["builder"]),
            builder_version=str(value["builder_version"]),
            source_fingerprints=dict(value.get("source_fingerprints") or {}),
            derivation_basis=str(value["derivation_basis"]),
        )


@dataclass(frozen=True)
class ContributionMeasure:
    """A quantitative property attached to a contribution assertion."""

    measure_id: str
    measure_type: str
    value: int | float
    unit: str
    definition: str
    qualifiers: Mapping[str, Any] = field(default_factory=dict)
    evidence_binding_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.measure_id, "measure_id")
        _nonempty(self.measure_type, "measure_type")
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise TypeError("Contribution measure value must be numeric")
        _nonempty(self.unit, "unit")
        _nonempty(self.definition, "definition")
        object.__setattr__(
            self, "qualifiers", _json_mapping(self.qualifiers, "measure qualifiers")
        )
        object.__setattr__(
            self, "evidence_binding_ids", tuple(self.evidence_binding_ids)
        )
        object.__setattr__(self, "limitations", tuple(self.limitations))

    def to_dict(self) -> dict[str, Any]:
        return {
            "measure_id": self.measure_id,
            "measure_type": self.measure_type,
            "value": self.value,
            "unit": self.unit,
            "definition": self.definition,
            "qualifiers": dict(self.qualifiers),
            "evidence_binding_ids": list(self.evidence_binding_ids),
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContributionMeasure":
        return cls(
            measure_id=str(value["measure_id"]),
            measure_type=str(value["measure_type"]),
            value=value["value"],
            unit=str(value["unit"]),
            definition=str(value["definition"]),
            qualifiers=dict(value.get("qualifiers") or {}),
            evidence_binding_ids=tuple(
                map(str, value.get("evidence_binding_ids") or ())
            ),
            limitations=tuple(map(str, value.get("limitations") or ())),
        )


@dataclass(frozen=True)
class ContributionAssertion:
    """One atomic, governed institutional contribution relationship."""

    assertion_id: str
    subject: InstitutionalEntity
    predicate: ContributionPredicate
    object: InstitutionalEntity
    temporal_scope: ContributionTemporalScope
    evidence_bindings: tuple[ContributionEvidenceBinding, ...]
    qualifiers: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)
    measures: tuple[ContributionMeasure, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.assertion_id, "assertion_id")
        if not isinstance(self.subject, InstitutionalEntity):
            raise TypeError("Contribution assertion subject must be an InstitutionalEntity")
        if not isinstance(self.object, InstitutionalEntity):
            raise TypeError("Contribution assertion object must be an InstitutionalEntity")
        if not isinstance(self.predicate, ContributionPredicate):
            raise TypeError("Contribution assertion predicate must be governed")
        if not isinstance(self.temporal_scope, ContributionTemporalScope):
            raise TypeError("temporal_scope must be a ContributionTemporalScope")
        if not self.evidence_bindings:
            raise ValueError("Contribution assertion requires evidence")
        bindings = tuple(self.evidence_bindings)
        measures = tuple(self.measures)
        if not all(isinstance(item, ContributionEvidenceBinding) for item in bindings):
            raise TypeError("evidence_bindings contain an invalid value")
        if not all(isinstance(item, ContributionMeasure) for item in measures):
            raise TypeError("measures contain an invalid value")
        binding_ids = [item.binding_id for item in bindings]
        measure_ids = [item.measure_id for item in measures]
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("Duplicate contribution evidence binding ID")
        if len(measure_ids) != len(set(measure_ids)):
            raise ValueError("Duplicate contribution measure ID")
        known_bindings = set(binding_ids)
        for measure in measures:
            unknown = set(measure.evidence_binding_ids) - known_bindings
            if unknown:
                raise ValueError(
                    f"Measure {measure.measure_id} references unknown evidence: "
                    f"{sorted(unknown)}"
                )
        object.__setattr__(self, "evidence_bindings", bindings)
        object.__setattr__(self, "measures", measures)
        object.__setattr__(
            self, "qualifiers", _json_mapping(self.qualifiers, "assertion qualifiers")
        )
        object.__setattr__(
            self, "provenance", _json_mapping(self.provenance, "assertion provenance")
        )

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "subject": self.subject.to_dict(),
            "predicate": self.predicate.value,
            "object": self.object.to_dict(),
            "qualifiers": dict(self.qualifiers),
            "temporal_scope": self.temporal_scope.to_dict(),
            "evidence_bindings": [
                item.to_dict()
                for item in sorted(
                    self.evidence_bindings, key=lambda item: item.binding_id
                )
            ],
            "provenance": dict(self.provenance),
            "measures": [
                item.to_dict()
                for item in sorted(self.measures, key=lambda item: item.measure_id)
            ],
        }

    @property
    def deterministic_fingerprint(self) -> str:
        return _fingerprint(self.semantic_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.semantic_dict(),
            "deterministic_fingerprint": self.deterministic_fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContributionAssertion":
        result = cls(
            assertion_id=str(value["assertion_id"]),
            subject=InstitutionalEntity.from_dict(value["subject"]),
            predicate=ContributionPredicate(str(value["predicate"])),
            object=InstitutionalEntity.from_dict(value["object"]),
            qualifiers=dict(value.get("qualifiers") or {}),
            temporal_scope=ContributionTemporalScope.from_dict(
                value["temporal_scope"]
            ),
            evidence_bindings=tuple(
                ContributionEvidenceBinding.from_dict(item)
                for item in value.get("evidence_bindings") or ()
            ),
            provenance=dict(value.get("provenance") or {}),
            measures=tuple(
                ContributionMeasure.from_dict(item)
                for item in value.get("measures") or ()
            ),
        )
        supplied = value.get("deterministic_fingerprint")
        if supplied and supplied != result.deterministic_fingerprint:
            raise ValueError("Contribution assertion fingerprint does not match content")
        return result


EntityT = TypeVar("EntityT", bound=InstitutionalEntity)


@dataclass(frozen=True)
class ContributionKnowledgeObject(Generic[EntityT]):
    """ISO's model of one governed entity's function over a temporal scope.

    This generic semantic object is composed primarily of atomic contribution
    assertions.  Entity-specific contribution objects will specialize this
    contract in later work; this class contains no reporting or reasoning logic.
    """

    contribution_object_id: str
    entity: EntityT
    temporal_scope: ContributionTemporalScope
    assertions: tuple[ContributionAssertion, ...]
    ontology_version: str = "1"
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _nonempty(self.contribution_object_id, "contribution_object_id")
        _nonempty(self.ontology_version, "ontology_version")
        if not isinstance(self.entity, InstitutionalEntity):
            raise TypeError("entity must be an InstitutionalEntity")
        if not isinstance(self.temporal_scope, ContributionTemporalScope):
            raise TypeError("temporal_scope must be a ContributionTemporalScope")
        assertions = tuple(self.assertions)
        if not all(isinstance(item, ContributionAssertion) for item in assertions):
            raise TypeError("assertions contain an invalid value")
        assertion_ids = [item.assertion_id for item in assertions]
        if len(assertion_ids) != len(set(assertion_ids)):
            raise ValueError("Duplicate contribution assertion ID")
        wrong_subjects = [
            item.assertion_id
            for item in assertions
            if item.subject.entity_id != self.entity.entity_id
        ]
        if wrong_subjects:
            raise ValueError(
                "Contribution assertions must share the object's governed subject: "
                f"{wrong_subjects}"
            )
        object.__setattr__(self, "assertions", assertions)
        object.__setattr__(
            self, "provenance", _json_mapping(self.provenance, "object provenance")
        )

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "contribution_object_id": self.contribution_object_id,
            "ontology_version": self.ontology_version,
            "entity": self.entity.to_dict(),
            "temporal_scope": self.temporal_scope.to_dict(),
            "assertions": [
                item.to_dict()
                for item in sorted(self.assertions, key=lambda item: item.assertion_id)
            ],
            "provenance": dict(self.provenance),
        }

    @property
    def deterministic_fingerprint(self) -> str:
        return _fingerprint(self.semantic_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.semantic_dict(),
            "deterministic_fingerprint": self.deterministic_fingerprint,
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True
        )

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "ContributionKnowledgeObject[InstitutionalEntity]":
        result = cls(
            contribution_object_id=str(value["contribution_object_id"]),
            ontology_version=str(value.get("ontology_version", "1")),
            entity=InstitutionalEntity.from_dict(value["entity"]),
            temporal_scope=ContributionTemporalScope.from_dict(
                value["temporal_scope"]
            ),
            assertions=tuple(
                ContributionAssertion.from_dict(item)
                for item in value.get("assertions") or ()
            ),
            provenance=dict(value.get("provenance") or {}),
        )
        supplied = value.get("deterministic_fingerprint")
        if supplied and supplied != result.deterministic_fingerprint:
            raise ValueError(
                "Contribution Knowledge Object fingerprint does not match content"
            )
        return result

    @classmethod
    def from_json(
        cls, value: str
    ) -> "ContributionKnowledgeObject[InstitutionalEntity]":
        return cls.from_dict(json.loads(value))


__all__ = [
    "ContributionAssertion",
    "ContributionEvidenceBinding",
    "ContributionKnowledgeObject",
    "ContributionMeasure",
    "ContributionPeriod",
    "ContributionPredicate",
    "ContributionTemporalScope",
]
