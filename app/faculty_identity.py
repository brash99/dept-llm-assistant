"""Deterministic, appointment-neutral faculty identity resolution.

Knowledge Objects remain source observations. This service derives only whether
observations refer to the same person; it does not derive employment, faculty
home, rank, appointment, tenure, FTE, or workload.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable, Mapping

import yaml


DEFAULT_ALIAS_REGISTRY = (
    Path(__file__).resolve().parents[1] / "config" / "faculty_identity_aliases.yaml"
)
FACULTY_OBJECT_TYPES = {
    "faculty_observation",
    "catalog_faculty_observation",
    "department_faculty_roster_observation",
    "course_offering_observation",
}
PLACEHOLDER_NAMES = {"staff", "tba", "tbd", "to be announced", "unassigned"}
IDENTIFIER_FIELDS = ("person_id", "employee_id", "email")
ALGORITHM = "iso_faculty_identity_resolution"
ALGORITHM_VERSION = "1.1"


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _ascii(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )


@dataclass(frozen=True)
class NormalizedPersonName:
    published_name: str
    normalized_name: str
    given_name: str
    middle_names: tuple[str, ...]
    family_name: str
    suffix: str | None = None

    @property
    def given_initial(self) -> str:
        return self.given_name[:1]

    @property
    def is_given_initial_only(self) -> bool:
        return len(self.given_name) == 1


def normalize_person_name(value: str) -> NormalizedPersonName | None:
    """Parse common published forms without fuzzy or probabilistic matching."""
    published = " ".join(str(value or "").split()).strip()
    if not published or "|" in published:
        return None
    cleaned = re.sub(
        r"^(?:dr|prof(?:essor)?)\.?\s+", "", _ascii(published),
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[’']", "", cleaned)
    suffix = None
    suffix_match = re.search(r"(?:,|\s)\s*(jr|sr|ii|iii|iv)\.?$", cleaned, re.I)
    if suffix_match:
        suffix = suffix_match.group(1).casefold()
        cleaned = cleaned[:suffix_match.start()].strip(" ,")
    if "," in cleaned:
        family, remainder = cleaned.split(",", 1)
        ordered = [*remainder.strip().split(), *family.strip().split()]
    else:
        ordered = cleaned.split()
    tokens = [re.sub(r"[^A-Za-z0-9-]", "", token).casefold() for token in ordered]
    tokens = [token for token in tokens if token]
    if len(tokens) < 2:
        return None
    given, family = tokens[0], tokens[-1]
    middle = tuple(tokens[1:-1])
    normalized = " ".join((given, *middle, family, *((suffix,) if suffix else ())))
    if normalized in PLACEHOLDER_NAMES or family in PLACEHOLDER_NAMES:
        return None
    return NormalizedPersonName(
        published_name=published,
        normalized_name=normalized,
        given_name=given,
        middle_names=middle,
        family_name=family,
        suffix=suffix,
    )


def _middle_names_compatible(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    if not left or not right:
        return True
    if len(left) != len(right):
        return False
    return all(
        a == b or (len(a) == 1 and b.startswith(a)) or (len(b) == 1 and a.startswith(b))
        for a, b in zip(left, right)
    )


@dataclass(frozen=True)
class FacultyIdentityAlias:
    identity_key: str
    canonical_display_name: str
    observed_names: tuple[str, ...]
    confidence: float
    evidence: Mapping[str, str]


class IdentityAliasRegistry:
    def __init__(self, aliases: Iterable[FacultyIdentityAlias], registry_id: str):
        self.registry_id = registry_id
        self.aliases = tuple(aliases)
        by_name: dict[str, FacultyIdentityAlias] = {}
        identity_keys: set[str] = set()
        for alias in self.aliases:
            if not alias.identity_key or not alias.observed_names:
                raise ValueError("Faculty identity aliases require a key and observed names")
            if not 0 <= alias.confidence <= 1:
                raise ValueError("Faculty identity alias confidence must be between zero and one")
            if not alias.evidence.get("source") or not alias.evidence.get("assertion"):
                raise ValueError("Faculty identity aliases require evidence")
            if alias.identity_key in identity_keys:
                raise ValueError(f"Duplicate governed faculty identity key: {alias.identity_key}")
            identity_keys.add(alias.identity_key)
            for name in alias.observed_names:
                normalized = normalize_person_name(name)
                if not normalized:
                    raise ValueError(f"Invalid governed faculty alias: {name!r}")
                prior = by_name.get(normalized.normalized_name)
                if prior:
                    raise ValueError(f"Duplicate governed faculty alias: {name!r}")
                by_name[normalized.normalized_name] = alias
        self._by_name = by_name

    @classmethod
    def load(cls, path: Path = DEFAULT_ALIAS_REGISTRY) -> "IdentityAliasRegistry":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        aliases = tuple(
            FacultyIdentityAlias(
                identity_key=str(item["identity_key"]),
                canonical_display_name=str(item["canonical_display_name"]),
                observed_names=tuple(map(str, item.get("observed_names") or ())),
                confidence=float(item.get("confidence", 1.0)),
                evidence={str(k): str(v) for k, v in (item.get("evidence") or {}).items()},
            )
            for item in payload.get("identities") or ()
        )
        return cls(aliases, str(payload.get("registry_id") or "faculty_identity_aliases"))

    def for_name(self, name: NormalizedPersonName) -> FacultyIdentityAlias | None:
        return self._by_name.get(name.normalized_name)

    @property
    def fingerprint(self) -> str:
        return _fingerprint({
            "registry_id": self.registry_id,
            "identities": [asdict(item) for item in self.aliases],
        })


# Compatibility name for callers written before the governance sprint.
FacultyIdentityAliasRegistry = IdentityAliasRegistry


@dataclass(frozen=True)
class FacultySourceObservation:
    observation_reference: str
    knowledge_object_id: str
    object_type: str
    source_system: str
    observed_name: str
    normalized_name: str
    identifiers: tuple[str, ...]
    temporal_label: str | None
    source_path: str | None


@dataclass(frozen=True)
class FacultyIdentity:
    identity_id: str
    display_name: str
    observed_names: tuple[str, ...]
    normalized_names: tuple[str, ...]
    source_observations: tuple[FacultySourceObservation, ...]
    matching_methods: tuple[str, ...]
    confidence: float
    ambiguous: bool
    ambiguity_reason: str | None
    provenance: Mapping[str, Any]
    deterministic_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["source_observations"] = [asdict(item) for item in self.source_observations]
        return value


@dataclass(frozen=True)
class FacultyIdentityAuditResult:
    identities: tuple[FacultyIdentity, ...]
    summary: Mapping[str, Any]
    observation_schema_audit: Mapping[str, Any]
    deterministic_fingerprint: str

    def summary_dict(self) -> dict[str, Any]:
        return {
            "summary": dict(self.summary),
            "observation_schema_audit": dict(self.observation_schema_audit),
            "deterministic_fingerprint": self.deterministic_fingerprint,
        }


class _DisjointSet:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[max(left_root, right_root)] = min(left_root, right_root)


class FacultyIdentityService:
    def __init__(self, alias_registry: IdentityAliasRegistry | None = None):
        self.alias_registry = alias_registry or IdentityAliasRegistry.load()

    def audit(self, objects: Iterable[Mapping[str, Any]]) -> FacultyIdentityAuditResult:
        all_objects = tuple(objects)
        observations, schema = _extract_faculty_observations(all_objects)
        observation_references = [item.observation_reference for item in observations]
        if len(observation_references) != len(set(observation_references)):
            raise ValueError("Duplicate faculty source-observation reference")
        names = [normalize_person_name(item.observed_name) for item in observations]
        if any(item is None for item in names):
            raise ValueError("Extracted faculty observations must have valid names")
        parsed = [item for item in names if item is not None]
        dsu = _DisjointSet(len(observations))
        methods: dict[int, set[str]] = defaultdict(set)
        ambiguous: dict[int, str] = {}

        self._union_identifiers(observations, dsu, methods)
        self._union_exact_names(parsed, dsu, methods)
        self._union_governed_aliases(parsed, dsu, methods)
        self._union_compatible_middle_names(parsed, dsu, methods, ambiguous)
        self._union_unique_initials(parsed, dsu, methods, ambiguous)

        clusters: dict[int, list[int]] = defaultdict(list)
        for index in range(len(observations)):
            clusters[dsu.find(index)].append(index)

        identities = []
        used_ids: set[str] = set()
        for indexes in sorted(clusters.values(), key=lambda values: tuple(
            observations[index].observation_reference for index in values
        )):
            identity = self._build_identity(indexes, observations, parsed, methods, ambiguous)
            if identity.identity_id in used_ids:
                raise ValueError(f"Duplicate faculty identity ID: {identity.identity_id}")
            used_ids.add(identity.identity_id)
            identities.append(identity)
        identities.sort(key=lambda item: item.identity_id)

        sizes = Counter(len(item.source_observations) for item in identities)
        sources = Counter(
            observation.source_system
            for identity in identities
            for observation in identity.source_observations
        )
        largest = sorted(
            identities,
            key=lambda item: (-len(item.source_observations), item.identity_id),
        )[:10]
        summary = {
            "candidate_object_count": schema["candidate_object_count"],
            "identity_bearing_observation_count": len(observations),
            "excluded_missing_or_placeholder_name_count": schema[
                "excluded_missing_or_placeholder_name_count"
            ],
            "identity_count": len(identities),
            "identity_cluster_count": sum(size > 1 for size in sizes.elements()),
            "single_observation_identity_count": sizes[1],
            "multi_observation_identity_count": sum(
                count for size, count in sizes.items() if size > 1
            ),
            "ambiguous_identity_count": sum(item.ambiguous for item in identities),
            "duplicate_identity_id_count": len(identities) - len(used_ids),
            "source_system_coverage": dict(sorted(sources.items())),
            "largest_identity_clusters": [
                {
                    "identity_id": item.identity_id,
                    "display_name": item.display_name,
                    "observation_count": len(item.source_observations),
                    "source_systems": sorted({
                        observation.source_system
                        for observation in item.source_observations
                    }),
                    "ambiguous": item.ambiguous,
                }
                for item in largest
            ],
        }
        semantic = {
            "algorithm": ALGORITHM,
            "algorithm_version": ALGORITHM_VERSION,
            "alias_registry_fingerprint": self.alias_registry.fingerprint,
            "identities": [item.to_dict() for item in identities],
            "summary": summary,
            "observation_schema_audit": schema,
        }
        return FacultyIdentityAuditResult(
            tuple(identities), summary, schema, _fingerprint(semantic)
        )

    def _union_identifiers(self, observations, dsu, methods) -> None:
        identifier_indexes: dict[str, list[int]] = defaultdict(list)
        for index, observation in enumerate(observations):
            for identifier in observation.identifiers:
                identifier_indexes[identifier].append(index)
        self._union_groups(identifier_indexes, "exact_identifier", dsu, methods)

    def _union_exact_names(self, names, dsu, methods) -> None:
        exact_names: dict[str, list[int]] = defaultdict(list)
        for index, name in enumerate(names):
            exact_names[name.normalized_name].append(index)
        self._union_groups(exact_names, "exact_normalized_name", dsu, methods)

    def _union_governed_aliases(self, names, dsu, methods) -> None:
        governed_aliases: dict[str, list[int]] = defaultdict(list)
        for index, name in enumerate(names):
            alias = self.alias_registry.for_name(name)
            if alias:
                governed_aliases[alias.identity_key].append(index)
        self._union_groups(governed_aliases, "explicit_governed_alias", dsu, methods)

    @staticmethod
    def _union_groups(groups, method, dsu, methods) -> None:
        for indexes in groups.values():
            for index in indexes[1:]:
                dsu.union(indexes[0], index)
            if len(indexes) > 1:
                for index in indexes:
                    methods[index].add(method)

    def _union_compatible_middle_names(self, names, dsu, methods, ambiguous) -> None:
        groups: dict[tuple[str, str, str | None], list[int]] = defaultdict(list)
        for index, name in enumerate(names):
            if not name.is_given_initial_only:
                groups[(name.given_name, name.family_name, name.suffix)].append(index)
        for indexes in groups.values():
            full_middle = {
                name.middle_names[0]
                for index in indexes
                for name in (names[index],)
                if name.middle_names and len(name.middle_names[0]) > 1
            }
            initials = {
                name.middle_names[0][0]
                for index in indexes
                for name in (names[index],)
                if name.middle_names
            }
            conflict = len(full_middle) > 1 or len(initials) > 1
            if conflict:
                for index in indexes:
                    if not names[index].middle_names:
                        ambiguous[index] = "multiple_compatible_middle_name_candidates"
                continue
            for index in indexes[1:]:
                dsu.union(indexes[0], index)
            if len(indexes) > 1:
                for index in indexes:
                    methods[index].add("bounded_middle_name_variation")

    def _union_unique_initials(self, names, dsu, methods, ambiguous) -> None:
        for index, name in enumerate(names):
            if not name.is_given_initial_only:
                continue
            # A reviewed alias has already resolved at the stronger governance
            # stage and must not be weakened by a later initial-only ambiguity.
            if self.alias_registry.for_name(name):
                continue
            candidates = {
                dsu.find(other)
                for other, candidate in enumerate(names)
                if other != index
                and not candidate.is_given_initial_only
                and candidate.family_name == name.family_name
                and candidate.given_initial == name.given_initial
            }
            if len(candidates) == 1:
                target = next(iter(candidates))
                dsu.union(index, target)
                methods[index].add("unique_given_initial")
                methods[target].add("unique_given_initial")
            elif len(candidates) > 1:
                ambiguous[index] = "multiple_given_name_candidates_for_initial"

    def review_candidates(
        self, observed_name: str, identities: Iterable[FacultyIdentity]
    ) -> tuple[dict[str, Any], ...]:
        """Return bounded deterministic candidates without performing a merge."""
        name = normalize_person_name(observed_name)
        if not name:
            return ()
        candidates: dict[str, set[str]] = defaultdict(set)
        governed = self.alias_registry.for_name(name)
        for identity in identities:
            if identity.ambiguous:
                continue
            parsed_names = tuple(filter(None, (
                normalize_person_name(value) for value in identity.observed_names
            )))
            if governed and identity.identity_id == f"faculty_identity:{governed.identity_key}":
                candidates[identity.identity_id].add("governed_alias")
            for candidate in parsed_names:
                if (
                    not name.is_given_initial_only
                    and name.given_name == candidate.given_name
                    and name.family_name == candidate.family_name
                    and name.suffix == candidate.suffix
                    and _middle_names_compatible(name.middle_names, candidate.middle_names)
                ):
                    candidates[identity.identity_id].add("middle_name_variation")
                if (
                    name.is_given_initial_only
                    and name.family_name == candidate.family_name
                    and name.given_initial == candidate.given_initial
                ):
                    candidates[identity.identity_id].add("given_initial")
        by_id = {item.identity_id: item for item in identities}
        return tuple({
            "faculty_identity_id": identity_id,
            "display_name": by_id[identity_id].display_name,
            "candidate_methods": sorted(methods),
        } for identity_id, methods in sorted(candidates.items()))

    def _build_identity(self, indexes, observations, names, methods, ambiguous):
        refs = tuple(sorted((observations[index] for index in indexes), key=lambda x: x.observation_reference))
        parsed = [names[index] for index in indexes]
        governed = {
            alias.identity_key: alias
            for name in parsed
            for alias in (self.alias_registry.for_name(name),)
            if alias
        }
        ambiguity_reasons = {
            ambiguous[index] for index in indexes if index in ambiguous
        }
        if len(governed) > 1:
            ambiguity_reasons.add("conflicting_governed_identity_aliases")
        if len(governed) == 1:
            alias = next(iter(governed.values()))
            identity_id = f"faculty_identity:{alias.identity_key}"
            display_name = alias.canonical_display_name
            confidence = alias.confidence
        else:
            display_name = max(
                (item.published_name for item in parsed),
                key=lambda value: (len(value.split()), len(value), value.casefold()),
            )
            identifiers = sorted({value for ref in refs for value in ref.identifiers})
            base = identifiers[0] if identifiers else min(item.normalized_name for item in parsed)
            identity_id = f"faculty_identity:{_fingerprint(base)[:24]}"
            confidence = 1.0 if identifiers or len(refs) == 1 else 0.9
        cluster_methods = sorted({
            method for index in indexes
            for method in methods.get(index, ())
        })
        if not cluster_methods:
            cluster_methods = ["single_observation"]
        ambiguity_reasons = sorted(ambiguity_reasons)
        provenance = {
            "algorithm": ALGORITHM,
            "algorithm_version": ALGORITHM_VERSION,
            "alias_registry_id": self.alias_registry.registry_id,
            "alias_registry_fingerprint": self.alias_registry.fingerprint,
            "source_observation_ids_fingerprint": _fingerprint([
                item.observation_reference for item in refs
            ]),
        }
        semantic = {
            "identity_id": identity_id,
            "display_name": display_name,
            "observed_names": sorted({item.published_name for item in parsed}),
            "normalized_names": sorted({item.normalized_name for item in parsed}),
            "source_observations": [asdict(item) for item in refs],
            "matching_methods": cluster_methods,
            "confidence": confidence,
            "ambiguous": bool(ambiguity_reasons),
            "ambiguity_reason": ";".join(ambiguity_reasons) or None,
            "provenance": provenance,
        }
        return FacultyIdentity(
            identity_id=identity_id,
            display_name=display_name,
            observed_names=tuple(semantic["observed_names"]),
            normalized_names=tuple(semantic["normalized_names"]),
            source_observations=refs,
            matching_methods=tuple(cluster_methods),
            confidence=confidence,
            ambiguous=bool(ambiguity_reasons),
            ambiguity_reason=semantic["ambiguity_reason"],
            provenance=provenance,
            deterministic_fingerprint=_fingerprint(semantic),
        )


def _extract_faculty_observations(objects: tuple[Mapping[str, Any], ...]):
    observations: list[FacultySourceObservation] = []
    object_counts = Counter()
    field_counts: dict[str, Counter[str]] = defaultdict(Counter)
    excluded = 0
    for obj in sorted(objects, key=lambda item: str(item.get("id") or "")):
        object_type = str(obj.get("object_type") or "")
        if object_type not in FACULTY_OBJECT_TYPES:
            continue
        object_counts[object_type] += 1
        for field in _observed_fields(object_type):
            if obj.get(field) not in (None, "", [], {}):
                field_counts[object_type][field] += 1
        if object_type == "department_faculty_roster_observation":
            for index, entry in enumerate(obj.get("entries") or ()):
                name = str(entry.get("published_name") or "").strip()
                if not normalize_person_name(name):
                    excluded += 1
                    continue
                observations.append(_source_reference(obj, name, object_type, f"entry:{index}", entry))
                field_counts[object_type]["entry_published_name"] += 1
            continue
        name_field = {
            "faculty_observation": "display_name",
            "catalog_faculty_observation": "published_name",
            "course_offering_observation": "instructor_raw",
        }[object_type]
        name = str(obj.get(name_field) or obj.get("instructor_name") or "").strip()
        if not normalize_person_name(name):
            excluded += 1
            continue
        observations.append(_source_reference(obj, name, object_type, None, obj))
    observations.sort(key=lambda item: item.observation_reference)
    schema = {
        "candidate_object_count": sum(object_counts.values()),
        "candidate_object_counts_by_type": dict(sorted(object_counts.items())),
        "identity_bearing_observation_count": len(observations),
        "excluded_missing_or_placeholder_name_count": excluded,
        "observed_field_nonempty_counts": {
            key: dict(sorted(value.items())) for key, value in sorted(field_counts.items())
        },
        "source_systems": sorted({item.source_system for item in observations}),
        "temporal_labels": sorted({
            item.temporal_label for item in observations if item.temporal_label
        }),
    }
    return observations, schema


def _observed_fields(object_type: str) -> tuple[str, ...]:
    return {
        "faculty_observation": (
            "display_name", "given_name", "middle_name", "family_name", "email",
            "profile_url", "snapshot_date", "published_department", "published_titles",
            "provenance",
        ),
        "catalog_faculty_observation": (
            "published_name", "published_title", "academic_unit", "appointment_year",
            "catalog_year", "provenance",
        ),
        "department_faculty_roster_observation": (
            "entries", "academic_unit", "catalog_year", "provenance",
        ),
        "course_offering_observation": (
            "instructor_raw", "academic_term", "subject", "course_code", "provenance",
        ),
    }[object_type]


def _source_reference(obj, name, object_type, component, values):
    object_id = str(obj.get("id") or "")
    reference = f"{object_id}#{component}" if component else object_id
    identifiers = []
    for field in IDENTIFIER_FIELDS:
        value = values.get(field) or obj.get(field)
        if value:
            identifiers.append(f"{field}:{str(value).strip().casefold()}")
    temporal = (
        obj.get("snapshot_date") or obj.get("catalog_year")
        or obj.get("academic_term") or obj.get("acquisition_date")
    )
    provenance = obj.get("provenance") or {}
    source_path = (
        obj.get("relative_source_path") or obj.get("source_file")
        or provenance.get("source_path") or provenance.get("source_file")
        or provenance.get("source")
    )
    if source_path:
        source_path = _repository_relative(str(source_path))
    source_system = {
        "faculty_observation": "faculty_directory",
        "catalog_faculty_observation": "catalog_faculty",
        "department_faculty_roster_observation": "department_roster",
        "course_offering_observation": "schedule",
    }[object_type]
    normalized = normalize_person_name(name)
    return FacultySourceObservation(
        observation_reference=reference,
        knowledge_object_id=object_id,
        object_type=object_type,
        source_system=source_system,
        observed_name=name,
        normalized_name=normalized.normalized_name,
        identifiers=tuple(sorted(set(identifiers))),
        temporal_label=str(temporal) if temporal else None,
        source_path=source_path,
    )


def _repository_relative(value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        return path.as_posix()
    root = Path(__file__).resolve().parents[1]
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


__all__ = [
    "FacultyIdentity", "FacultyIdentityAliasRegistry", "IdentityAliasRegistry",
    "FacultyIdentityAuditResult",
    "FacultyIdentityService", "FacultySourceObservation", "NormalizedPersonName",
    "normalize_person_name",
]
