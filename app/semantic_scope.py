"""Semantic-scope contracts and retrieval-profile resolution.

Semantic scope describes how a Knowledge Object participates in an
institutional perspective. It is not a storage location or vector-index name.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import yaml

from app.semantic_identity import OrganizationalRelationship


SCOPE_ID = re.compile(r"^[a-z][a-z0-9_]*(?::[a-z0-9][a-z0-9_]*)?$")


@dataclass(frozen=True, order=True)
class SemanticScope:
    id: str
    kind: str
    label: str
    status: str = "active"
    aliases: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not SCOPE_ID.fullmatch(self.id):
            raise ValueError(f"Invalid semantic scope id: {self.id!r}")
        expected_kind = self.id.split(":", 1)[0]
        if self.kind != expected_kind:
            raise ValueError(
                f"Scope {self.id!r} kind must be {expected_kind!r}, not {self.kind!r}"
            )
        if not self.label.strip():
            raise ValueError("Semantic scope label must not be empty")
        object.__setattr__(self, "aliases", tuple(self.aliases))


class MembershipProvenance(str, Enum):
    ASSERTED = "asserted"
    REVIEWED = "reviewed"
    PROPOSED = "proposed"
    DERIVED = "derived"


@dataclass(frozen=True)
class SemanticMembership:
    """A retrieval projection with explicit provenance state."""

    scope: str
    provenance: MembershipProvenance
    asserted_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    note: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.scope.strip():
            raise ValueError("Semantic membership scope must not be empty")
        if not isinstance(self.provenance, MembershipProvenance):
            object.__setattr__(self, "provenance", MembershipProvenance(self.provenance))

    def to_dict(self) -> Dict[str, Any]:
        return {
            key: value
            for key, value in {
                "scope": self.scope,
                "provenance": self.provenance.value,
                "asserted_by": self.asserted_by,
                "reviewed_by": self.reviewed_by,
                "note": self.note,
            }.items()
            if value is not None
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SemanticMembership":
        return cls(
            scope=str(value["scope"]),
            provenance=MembershipProvenance(str(value["provenance"])),
            asserted_by=value.get("asserted_by"),
            reviewed_by=value.get("reviewed_by"),
            note=value.get("note"),
        )


@dataclass(frozen=True)
class RetrievalProfile:
    name: str
    scope_kind: str
    requires_selector: bool = False


@dataclass(frozen=True)
class ResolvedRetrievalProfile:
    profile: RetrievalProfile
    eligible_memberships: Tuple[str, ...]
    selected_scope: SemanticScope


RETRIEVAL_PROFILES: Dict[str, RetrievalProfile] = {
    "institution": RetrievalProfile(
        name="institution", scope_kind="institution", requires_selector=False
    ),
    "department": RetrievalProfile(
        name="department", scope_kind="department", requires_selector=True
    ),
}


class ScopeRegistry:
    def __init__(self, scopes: Iterable[SemanticScope]) -> None:
        self._scopes = {scope.id: scope for scope in scopes}
        if not self._scopes:
            raise ValueError("Scope registry must contain at least one scope")
        aliases: Dict[str, str] = {}
        for scope in self._scopes.values():
            for alias in (scope.id, *scope.aliases):
                key = _normalize_selector(alias)
                prior = aliases.get(key)
                if prior is not None and prior != scope.id:
                    raise ValueError(
                        f"Scope alias {alias!r} is ambiguous between {prior!r} and {scope.id!r}"
                    )
                aliases[key] = scope.id
        self._aliases = aliases

    @property
    def scopes(self) -> Tuple[SemanticScope, ...]:
        return tuple(sorted(self._scopes.values(), key=lambda scope: scope.id))

    def by_kind(self, kind: str, *, active_only: bool = False) -> Tuple[SemanticScope, ...]:
        return tuple(
            scope
            for scope in self.scopes
            if scope.kind == kind and (not active_only or scope.status == "active")
        )

    def resolve(self, selector: str, *, kind: Optional[str] = None) -> SemanticScope:
        normalized = _normalize_selector(selector)
        candidates = [normalized]
        if kind and ":" not in normalized:
            candidates.insert(0, f"{kind}:{normalized}")
        scope_id = next((self._aliases[key] for key in candidates if key in self._aliases), None)
        if scope_id is None:
            raise KeyError(f"Unknown semantic scope: {selector!r}")
        scope = self._scopes[scope_id]
        if kind is not None and scope.kind != kind:
            raise ValueError(
                f"Scope {selector!r} is {scope.kind!r}, not required kind {kind!r}"
            )
        return scope


def _normalize_selector(value: str) -> str:
    return re.sub(r"[^a-z0-9:]+", "_", str(value).strip().casefold()).strip("_")


def load_scope_registry(path: Path | str = "config/semantic_scopes.yaml") -> ScopeRegistry:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    entries = data.get("scopes") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise ValueError("Semantic scope registry must contain a scopes list")
    scopes = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Semantic scope entry {index} must be an object")
        scopes.append(
            SemanticScope(
                id=str(entry["id"]),
                kind=str(entry["kind"]),
                label=str(entry["label"]),
                status=str(entry.get("status", "active")),
                aliases=tuple(map(str, entry.get("aliases") or ())),
            )
        )
    return ScopeRegistry(scopes)


def resolve_retrieval_profile(
    profile: str | RetrievalProfile,
    *,
    department: Optional[str] = None,
    registry: Optional[ScopeRegistry] = None,
) -> ResolvedRetrievalProfile:
    contract = RETRIEVAL_PROFILES.get(profile) if isinstance(profile, str) else profile
    if contract is None:
        raise ValueError(f"Unknown retrieval profile: {profile!r}")
    registry = registry or load_scope_registry()
    if contract.requires_selector:
        if not department:
            raise ValueError(f"Retrieval profile {contract.name!r} requires department")
        scope = registry.resolve(department, kind=contract.scope_kind)
    else:
        scope = registry.resolve(contract.scope_kind, kind=contract.scope_kind)
    return ResolvedRetrievalProfile(
        profile=contract,
        eligible_memberships=(scope.id,),
        selected_scope=scope,
    )


def semantic_membership_ids(value: Any) -> Tuple[str, ...]:
    """Normalize serialized membership strings or future mapping contracts."""
    if value is None:
        return ()
    if isinstance(value, str):
        value = (value,)
    memberships = []
    for item in value:
        if isinstance(item, str):
            membership = item
        elif isinstance(item, Mapping):
            membership = item.get("scope") or item.get("id")
        elif isinstance(item, SemanticMembership):
            membership = item.scope
        else:
            membership = None
        if membership and membership not in memberships:
            memberships.append(str(membership))
    return tuple(memberships)


def record_matches_semantic_memberships(
    record: Mapping[str, Any], eligible_memberships: Sequence[str]
) -> bool:
    metadata = record.get("metadata") or {}
    actual = set(semantic_membership_ids(metadata.get("semantic_memberships")))
    return bool(actual.intersection(eligible_memberships))


__all__ = [
    "OrganizationalRelationship",
    "MembershipProvenance",
    "RETRIEVAL_PROFILES",
    "ResolvedRetrievalProfile",
    "RetrievalProfile",
    "ScopeRegistry",
    "SemanticScope",
    "SemanticMembership",
    "load_scope_registry",
    "record_matches_semantic_memberships",
    "resolve_retrieval_profile",
    "semantic_membership_ids",
]
