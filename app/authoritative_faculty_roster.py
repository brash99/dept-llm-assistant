"""Explicit, effective-dated facts from an authoritative faculty roster.

This contract never derives active employment, tenure, faculty home, missing
FTE, or denominator eligibility. Knowledge objects store facts; services derive
meaning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "config" / "faculty_roster_schema.yaml"
OBJECT_TYPE = "authoritative_faculty_roster_observation"
ALGORITHM = "iso_authoritative_faculty_roster_contract"
ALGORITHM_VERSION = "1.0"
ROW_CLASSIFICATIONS = {"accepted", "accepted_with_limitations", "quarantined", "rejected"}


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FacultyRosterSchema:
    schema_id: str
    schema_version: str
    required_fields: tuple[str, ...]
    temporal_alternatives: tuple[str, ...]
    recommended_fields: tuple[str, ...]
    optional_fields: tuple[str, ...]
    column_aliases: Mapping[str, tuple[str, ...]]
    fte_minimum: float = 0.0
    fte_maximum: float = 1.0

    @classmethod
    def load(cls, path: Path = DEFAULT_SCHEMA) -> "FacultyRosterSchema":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        aliases = {
            str(field): tuple(str(value) for value in values)
            for field, values in (payload.get("column_aliases") or {}).items()
        }
        schema = cls(
            schema_id=str(payload.get("schema_id") or ""),
            schema_version=str(payload.get("schema_version") or ""),
            required_fields=tuple(payload.get("required_fields") or ()),
            temporal_alternatives=tuple(payload.get("required_temporal_alternatives") or ()),
            recommended_fields=tuple(payload.get("recommended_fields") or ()),
            optional_fields=tuple(payload.get("optional_fields") or ()),
            column_aliases=aliases,
            fte_minimum=float(payload.get("fte_minimum", 0.0)),
            fte_maximum=float(payload.get("fte_maximum", 1.0)),
        )
        if not schema.schema_id or not schema.required_fields or not schema.temporal_alternatives:
            raise ValueError("Faculty roster schema requires identity, required, and temporal fields")
        all_fields = set(schema.required_fields + schema.temporal_alternatives + schema.recommended_fields + schema.optional_fields)
        if set(aliases) != all_fields:
            missing = sorted(all_fields - set(aliases))
            extra = sorted(set(aliases) - all_fields)
            raise ValueError(f"Roster column aliases do not match fields; missing={missing}, extra={extra}")
        observed_aliases: dict[str, str] = {}
        for field, values in aliases.items():
            if not values:
                raise ValueError(f"Roster field {field!r} has no source-column aliases")
            for value in values:
                key = value.strip().casefold()
                if key in observed_aliases and observed_aliases[key] != field:
                    raise ValueError(f"Duplicate source-column alias: {value}")
                observed_aliases[key] = field
        return schema

    @property
    def canonical_fields(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(
            self.required_fields + self.temporal_alternatives
            + self.recommended_fields + self.optional_fields
        ))

    @property
    def deterministic_fingerprint(self) -> str:
        return fingerprint(asdict(self))


@dataclass(frozen=True)
class AuthoritativeFacultyRosterObservation:
    observation_id: str
    object_type: str
    faculty_identity_id: str | None
    identity_link_method: str | None
    institutional_person_identifier: str
    published_person_name: str
    effective_date: str | None
    snapshot_date: str | None
    effective_end_date: str | None
    employment_status: str
    appointment_category: str
    appointment_academic_unit: str
    academic_unit_id: str | None
    source_authority: str
    source_record_id: str
    appointment_fte: str | None
    instructional_fte: str | None
    administrative_fte: str | None
    faculty_rank: str | None
    tenure_status: str | None
    primary_secondary: str | None
    position_number: str | None
    home_department: str | None
    email: str | None
    preferred_name: str | None
    legal_name: str | None
    hire_date: str | None
    retirement_date: str | None
    notes: str | None
    evidence_fitness: tuple[str, ...]
    evidence_limitations: tuple[str, ...]
    provenance: Mapping[str, Any]
    deterministic_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FacultyRosterRowResult:
    row_number: int
    classification: str
    reasons: tuple[str, ...]
    source_record_id: str | None
    observation: AuthoritativeFacultyRosterObservation | None
    published_values: Mapping[str, str]

    def __post_init__(self) -> None:
        if self.classification not in ROW_CLASSIFICATIONS:
            raise ValueError(f"Invalid roster row classification: {self.classification}")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["observation"] = self.observation.to_dict() if self.observation else None
        return value


@dataclass(frozen=True)
class FacultyRosterIngestionResult:
    rows: tuple[FacultyRosterRowResult, ...]
    summary: Mapping[str, Any]
    schema_fingerprint: str
    source_fingerprint: str
    deterministic_fingerprint: str

    @property
    def observations(self) -> tuple[AuthoritativeFacultyRosterObservation, ...]:
        return tuple(row.observation for row in self.rows if row.observation is not None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": dict(self.summary),
            "schema_fingerprint": self.schema_fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "deterministic_fingerprint": self.deterministic_fingerprint,
            "rows": [row.to_dict() for row in self.rows],
        }


def denominator_readiness(summary: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    accepted = int(summary.get("accepted_observation_count", 0))
    if not accepted:
        blocked = "blocked_by_missing_evidence"
        return {
            name: {"status": blocked, "reason": "No authoritative faculty roster is present."}
            for name in (
                "full_time_faculty", "instructional_faculty", "tenure_line_faculty",
                "faculty_fte", "active_faculty", "current_faculty_by_unit",
            )
        }
    def readiness(covered: int, required: str) -> dict[str, str]:
        if covered == accepted:
            return {"status": "supported_by_explicit_evidence", "reason": f"Every accepted observation explicitly publishes {required}."}
        if covered:
            return {"status": "partially_supported", "reason": f"Only some accepted observations explicitly publish {required}."}
        return {"status": "blocked_by_missing_evidence", "reason": f"No accepted observation explicitly publishes {required}."}
    return {
        "full_time_faculty": readiness(int(summary.get("appointment_category_coverage_count", 0)), "appointment category"),
        "instructional_faculty": readiness(int(summary.get("instructional_fte_coverage_count", 0)), "instructional FTE"),
        "tenure_line_faculty": readiness(int(summary.get("tenure_coverage_count", 0)), "tenure status"),
        "faculty_fte": readiness(int(summary.get("appointment_fte_coverage_count", 0)), "appointment FTE"),
        "active_faculty": {"status": "unsafe_to_infer", "reason": "Effective dates and explicit status require an as-of policy; no active population is calculated."},
        "current_faculty_by_unit": {"status": "unsafe_to_infer", "reason": "Unit and status facts do not themselves establish a current denominator policy."},
    }


__all__ = [
    "AuthoritativeFacultyRosterObservation", "FacultyRosterIngestionResult",
    "FacultyRosterRowResult", "FacultyRosterSchema", "denominator_readiness",
]
