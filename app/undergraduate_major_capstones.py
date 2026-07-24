"""Governed undergraduate major-to-capstone relationships."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from app.undergraduate_majors import UndergraduateMajorRegistry


DEFAULT_MAJOR_CAPSTONE_REGISTRY = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "undergraduate_major_capstones.yaml"
)
VALID_REQUIREMENT_TYPES = {
    "single_required_capstone",
    "required_capstone_sequence",
    "multiple_required_capstones",
    "alternative_capstone_choices",
    "thesis_or_seminar_options",
    "multiple_pathways",
    "no_identifiable_capstone",
    "unresolved",
}
VALID_CONFIDENCE = {"high", "medium", "low"}


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CapstoneEvidence:
    catalog_year: str
    catalog_pages: tuple[int, ...]
    evidence_confidence: str
    assertion: str


@dataclass(frozen=True)
class CapstonePathway:
    pathway_id: str
    label: str
    requirement_type: str
    course_ids: tuple[str, ...]
    non_course_requirement: str | None
    evidence: CapstoneEvidence


@dataclass(frozen=True)
class MajorCapstoneRequirement:
    major_id: str
    display_name: str
    requirement_type: str
    pathways: tuple[CapstonePathway, ...]
    notes: tuple[str, ...]
    deterministic_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["pathways"] = [
            {
                **asdict(pathway),
                "course_ids": list(pathway.course_ids),
                "evidence": {
                    **asdict(pathway.evidence),
                    "catalog_pages": list(pathway.evidence.catalog_pages),
                },
            }
            for pathway in self.pathways
        ]
        value["notes"] = list(self.notes)
        return value


class UndergraduateMajorCapstoneRegistry:
    def __init__(
        self,
        requirements: Iterable[MajorCapstoneRequirement],
        *,
        schema_version: str,
        registry_id: str,
        catalog_year: str,
        source_path: Path | None = None,
    ):
        self.requirements = tuple(requirements)
        self.schema_version = schema_version
        self.registry_id = registry_id
        self.catalog_year = catalog_year
        self.source_path = source_path
        self.validate()

    @classmethod
    def load(
        cls, path: Path = DEFAULT_MAJOR_CAPSTONE_REGISTRY
    ) -> "UndergraduateMajorCapstoneRegistry":
        source = Path(path)
        payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        requirements = tuple(
            _requirement_from_dict(item)
            for item in payload.get("major_capstones") or ()
        )
        return cls(
            requirements,
            schema_version=str(payload.get("schema_version", "1")),
            registry_id=str(payload.get("registry_id") or ""),
            catalog_year=str(payload.get("catalog_year") or ""),
            source_path=source,
        )

    def validate(self) -> None:
        if not self.registry_id or not self.catalog_year:
            raise ValueError("Capstone registry identity and catalog year are required")
        ids = [item.major_id for item in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate major in capstone registry")
        current = {
            item.major_id
            for item in UndergraduateMajorRegistry.load().majors
            if item.status == "current"
        }
        missing = current - set(ids)
        extra = set(ids) - current
        if missing or extra:
            raise ValueError(
                f"Capstone registry/current-major mismatch: "
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        for item in self.requirements:
            if item.requirement_type not in VALID_REQUIREMENT_TYPES:
                raise ValueError(f"Invalid requirement type for {item.major_id}")
            if item.requirement_type == "no_identifiable_capstone" and any(
                pathway.course_ids for pathway in item.pathways
            ):
                raise ValueError(
                    f"No-capstone record contains courses: {item.major_id}"
                )
            if not item.pathways:
                raise ValueError(f"Missing evidence pathway for {item.major_id}")
            pathway_ids = [pathway.pathway_id for pathway in item.pathways]
            if len(pathway_ids) != len(set(pathway_ids)):
                raise ValueError(f"Duplicate pathway for {item.major_id}")
            for pathway in item.pathways:
                if pathway.requirement_type not in VALID_REQUIREMENT_TYPES:
                    raise ValueError(
                        f"Invalid pathway type for {item.major_id}"
                    )
                if pathway.evidence.catalog_year != self.catalog_year:
                    raise ValueError(
                        f"Catalog year mismatch for {item.major_id}"
                    )
                if not pathway.evidence.catalog_pages:
                    raise ValueError(f"Missing pages for {item.major_id}")
                if pathway.evidence.evidence_confidence not in VALID_CONFIDENCE:
                    raise ValueError(
                        f"Invalid evidence confidence for {item.major_id}"
                    )

    def get(self, major_id: str) -> MajorCapstoneRequirement | None:
        return next(
            (item for item in self.requirements if item.major_id == major_id),
            None,
        )

    @property
    def deterministic_fingerprint(self) -> str:
        return _fingerprint({
            "schema_version": self.schema_version,
            "registry_id": self.registry_id,
            "catalog_year": self.catalog_year,
            "requirements": [
                item.to_dict()
                for item in sorted(
                    self.requirements, key=lambda value: value.major_id
                )
            ],
        })


def _requirement_from_dict(value: dict[str, Any]) -> MajorCapstoneRequirement:
    pathways = tuple(
        CapstonePathway(
            pathway_id=str(item.get("pathway_id") or ""),
            label=str(item.get("label") or ""),
            requirement_type=str(item.get("requirement_type") or ""),
            course_ids=tuple(item.get("course_ids") or ()),
            non_course_requirement=item.get("non_course_requirement"),
            evidence=CapstoneEvidence(
                catalog_year=str(item["evidence"].get("catalog_year") or ""),
                catalog_pages=tuple(item["evidence"].get("catalog_pages") or ()),
                evidence_confidence=str(
                    item["evidence"].get("evidence_confidence") or ""
                ),
                assertion=str(item["evidence"].get("assertion") or ""),
            ),
        )
        for item in value.get("pathways") or ()
    )
    semantic = {
        "major_id": value.get("major_id"),
        "display_name": value.get("display_name"),
        "requirement_type": value.get("requirement_type"),
        "pathways": value.get("pathways"),
        "notes": value.get("notes"),
    }
    return MajorCapstoneRequirement(
        major_id=str(value.get("major_id") or ""),
        display_name=str(value.get("display_name") or ""),
        requirement_type=str(value.get("requirement_type") or ""),
        pathways=pathways,
        notes=tuple(value.get("notes") or ()),
        deterministic_fingerprint=_fingerprint(semantic),
    )


__all__ = [
    "DEFAULT_MAJOR_CAPSTONE_REGISTRY",
    "CapstoneEvidence",
    "CapstonePathway",
    "MajorCapstoneRequirement",
    "UndergraduateMajorCapstoneRegistry",
]
