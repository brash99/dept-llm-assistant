"""Governed undergraduate-major facts and effective-dated ownership assertions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

import yaml

from app.institutional_units import AcademicUnitRegistry


DEFAULT_UNDERGRADUATE_MAJOR_REGISTRY = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "undergraduate_majors.yaml"
)
VALID_STATUSES = {"current", "possible_discontinued", "historical"}
VALID_OWNERSHIP_STATUSES = {
    "resolved",
    "conflicting_authoritative_assertions",
    "resolved_with_conflicting_catalog_structure",
    "unresolved",
}


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


@dataclass(frozen=True)
class MajorEvidence:
    source_type: str
    source: str
    assertion: str
    published_name: str | None = None
    catalog_year: str | None = None
    owner_code: str | None = None
    source_locator: str | None = None


@dataclass(frozen=True)
class MajorOwnerAssertion:
    owner_code: str
    academic_unit_id: str
    source: str
    source_type: str
    assertion: str


@dataclass(frozen=True)
class UndergraduateMajor:
    major_id: str
    display_name: str
    aliases: tuple[str, ...]
    degrees: tuple[str, ...]
    status: str
    effective_start: str | None
    effective_end: str | None
    owning_academic_unit_id: str | None
    ownership_status: str
    curriculum_unit_id: str | None
    owner_assertions: tuple[MajorOwnerAssertion, ...]
    evidence: tuple[MajorEvidence, ...]
    notes: tuple[str, ...]
    deterministic_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["aliases"] = list(self.aliases)
        value["degrees"] = list(self.degrees)
        value["owner_assertions"] = [
            asdict(item) for item in self.owner_assertions
        ]
        value["evidence"] = [asdict(item) for item in self.evidence]
        value["notes"] = list(self.notes)
        return value


class UndergraduateMajorRegistry:
    def __init__(
        self,
        majors: Iterable[UndergraduateMajor],
        *,
        schema_version: str,
        registry_id: str,
        title: str,
        as_of_catalog_year: str,
        source_path: Path | None = None,
    ):
        self.majors = tuple(majors)
        self.schema_version = schema_version
        self.registry_id = registry_id
        self.title = title
        self.as_of_catalog_year = as_of_catalog_year
        self.source_path = source_path
        self.validate()

    @classmethod
    def load(
        cls, path: Path = DEFAULT_UNDERGRADUATE_MAJOR_REGISTRY
    ) -> "UndergraduateMajorRegistry":
        source = Path(path)
        payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        values = tuple(_major_from_dict(item) for item in payload.get("majors") or ())
        return cls(
            values,
            schema_version=str(payload.get("schema_version", "1")),
            registry_id=str(payload.get("registry_id") or ""),
            title=str(payload.get("title") or ""),
            as_of_catalog_year=str(payload.get("as_of_catalog_year") or ""),
            source_path=source,
        )

    def validate(self) -> None:
        if not self.registry_id or not self.as_of_catalog_year:
            raise ValueError("Major registry identity and catalog year are required")
        ids = [item.major_id for item in self.majors]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate undergraduate major ID")
        names: dict[str, str] = {}
        units = AcademicUnitRegistry.load()
        governed_units = {item.unit_id for item in units.units}
        for major in self.majors:
            if major.status not in VALID_STATUSES:
                raise ValueError(f"Invalid status for {major.major_id}")
            if major.ownership_status not in VALID_OWNERSHIP_STATUSES:
                raise ValueError(f"Invalid ownership status for {major.major_id}")
            if not major.evidence:
                raise ValueError(f"Major lacks provenance: {major.major_id}")
            for value in (major.display_name, *major.aliases):
                normalized = _key(value)
                existing = names.get(normalized)
                if existing and existing != major.major_id:
                    raise ValueError(
                        f"Duplicate major name or alias {value!r}: "
                        f"{existing}, {major.major_id}"
                    )
                names[normalized] = major.major_id
            referenced = {
                value for value in (
                    major.owning_academic_unit_id, major.curriculum_unit_id,
                    *(item.academic_unit_id for item in major.owner_assertions),
                ) if value
            }
            missing = referenced - governed_units
            if missing:
                raise ValueError(
                    f"Unknown academic unit for {major.major_id}: {sorted(missing)}"
                )
            if major.ownership_status == "resolved" and not major.owning_academic_unit_id:
                raise ValueError(f"Resolved major lacks owner: {major.major_id}")

    def get(self, major_id: str) -> UndergraduateMajor | None:
        return next((item for item in self.majors if item.major_id == major_id), None)

    def resolve_name(self, name: str) -> UndergraduateMajor | None:
        target = _key(name)
        matches = tuple(
            item for item in self.majors
            if target in {_key(item.display_name), *(_key(x) for x in item.aliases)}
        )
        return matches[0] if len(matches) == 1 else None

    @property
    def deterministic_fingerprint(self) -> str:
        return _fingerprint({
            "schema_version": self.schema_version,
            "registry_id": self.registry_id,
            "as_of_catalog_year": self.as_of_catalog_year,
            "majors": [
                item.to_dict()
                for item in sorted(self.majors, key=lambda value: value.major_id)
            ],
        })


def _major_from_dict(value: dict[str, Any]) -> UndergraduateMajor:
    evidence = tuple(MajorEvidence(**item) for item in value.get("evidence") or ())
    assertions = tuple(
        MajorOwnerAssertion(**item) for item in value.get("owner_assertions") or ()
    )
    semantic = {
        key: value.get(key) for key in (
            "major_id", "display_name", "aliases", "degrees", "status",
            "effective_start", "effective_end", "owning_academic_unit_id",
            "ownership_status", "curriculum_unit_id", "owner_assertions",
            "evidence", "notes",
        )
    }
    return UndergraduateMajor(
        major_id=str(value.get("major_id") or ""),
        display_name=str(value.get("display_name") or ""),
        aliases=tuple(value.get("aliases") or ()),
        degrees=tuple(value.get("degrees") or ()),
        status=str(value.get("status") or ""),
        effective_start=value.get("effective_start"),
        effective_end=value.get("effective_end"),
        owning_academic_unit_id=value.get("owning_academic_unit_id"),
        ownership_status=str(value.get("ownership_status") or ""),
        curriculum_unit_id=value.get("curriculum_unit_id"),
        owner_assertions=assertions,
        evidence=evidence,
        notes=tuple(value.get("notes") or ()),
        deterministic_fingerprint=_fingerprint(semantic),
    )


__all__ = [
    "DEFAULT_UNDERGRADUATE_MAJOR_REGISTRY", "MajorEvidence",
    "MajorOwnerAssertion", "UndergraduateMajor", "UndergraduateMajorRegistry",
]
