"""Deterministic CSV adapter for the authoritative faculty roster contract."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.authoritative_faculty_roster import (
    ALGORITHM, ALGORITHM_VERSION, AuthoritativeFacultyRosterObservation,
    FacultyRosterIngestionResult, FacultyRosterRowResult, FacultyRosterSchema,
    fingerprint,
)
from app.faculty_identity import FacultyIdentity, FacultyIdentityService, normalize_person_name
from app.institutional_units import AcademicUnitRegistry


ACCEPTED = {"accepted", "accepted_with_limitations"}
DATE_FIELDS = {"effective_date", "snapshot_date", "effective_end_date", "hire_date", "retirement_date"}
FTE_FIELDS = {"appointment_fte", "instructional_fte", "administrative_fte"}


class _IdentityLinker:
    def __init__(self, identity_objects: Iterable[Mapping[str, Any]]) -> None:
        self.service = FacultyIdentityService()
        audit = self.service.audit(tuple(identity_objects))
        self.identities = audit.identities
        self.by_identifier: dict[str, set[str]] = defaultdict(set)
        self.by_email: dict[str, set[str]] = defaultdict(set)
        self.by_name: dict[str, set[str]] = defaultdict(set)
        for identity in self.identities:
            if identity.ambiguous:
                continue
            for name in identity.normalized_names:
                self.by_name[name].add(identity.identity_id)
            for source in identity.source_observations:
                for identifier in source.identifiers:
                    kind, _, value = identifier.partition(":")
                    target = self.by_email if kind == "email" else self.by_identifier
                    target[value].add(identity.identity_id)

    def link(self, person_id: str, email: str | None, name: str) -> tuple[str | None, str | None, tuple[str, ...]]:
        parsed = normalize_person_name(name)
        ordered: list[tuple[str, set[str]]] = [
            ("institutional_identifier", set(self.by_identifier.get(person_id.casefold(), ()))),
            ("email", set(self.by_email.get((email or "").casefold(), ()))),
            ("exact_normalized_name", set(self.by_name.get(parsed.normalized_name if parsed else "", ()))),
        ]
        alias = self.service.alias_registry.for_name(parsed) if parsed else None
        alias_ids = {f"faculty_identity:{alias.identity_key}"} if alias else set()
        if alias_ids and not alias_ids.intersection({item.identity_id for item in self.identities}):
            alias_ids = set()
        ordered.append(("governed_alias", alias_ids))
        candidates = self.service.review_candidates(name, self.identities)
        middle = {item["faculty_identity_id"] for item in candidates if "middle_name_variation" in item["candidate_methods"]}
        initials = {item["faculty_identity_id"] for item in candidates if "given_initial" in item["candidate_methods"]}
        ordered.extend((("middle_name_variation", middle), ("unique_initial", initials)))
        selected: str | None = None
        method: str | None = None
        conflicts: set[str] = set()
        for candidate_method, values in ordered:
            if len(values) > 1:
                conflicts.update(values)
                continue
            if not values:
                continue
            candidate = next(iter(values))
            if selected is None:
                selected, method = candidate, candidate_method
            elif candidate != selected:
                conflicts.update((selected, candidate))
        if conflicts:
            return None, None, tuple(sorted(conflicts))
        return selected, method, ()


class FacultyRosterCSVAdapter:
    def __init__(
        self,
        input_path: Path,
        schema: FacultyRosterSchema,
        *,
        source_authority: str | None = None,
        effective_date: str | None = None,
        identity_objects: Iterable[Mapping[str, Any]] = (),
        unit_registry: AcademicUnitRegistry | None = None,
    ) -> None:
        self.input_path = Path(input_path)
        self.schema = schema
        self.source_authority = source_authority
        self.default_effective_date = effective_date
        self.identity_linker = _IdentityLinker(identity_objects)
        self.unit_registry = unit_registry or AcademicUnitRegistry.load()

    def adapt(self) -> FacultyRosterIngestionResult:
        source_bytes = self.input_path.read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        with self.input_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError("Faculty roster CSV has no header")
            column_map, unmapped = self._column_map(reader.fieldnames)
            raw_rows = list(reader)
        seen_ids: set[str] = set()
        seen_positions: set[tuple[str, str, str]] = set()
        results: list[FacultyRosterRowResult] = []
        for row_number, raw in enumerate(raw_rows, start=2):
            values = {
                field: str(raw.get(source, "") or "").strip()
                for field, source in column_map.items()
            }
            if self.source_authority:
                values["source_authority"] = self.source_authority
            if self.default_effective_date and not values.get("effective_date") and not values.get("snapshot_date"):
                values["effective_date"] = self.default_effective_date
            reasons: list[str] = []
            classification = "accepted"
            missing = [field for field in self.schema.required_fields if not values.get(field)]
            if not any(values.get(field) for field in self.schema.temporal_alternatives):
                missing.append("effective_date_or_snapshot_date")
            if missing:
                classification = "rejected"
                reasons.extend(f"missing_required_field:{field}" for field in sorted(missing))
            invalid_dates = [field for field in DATE_FIELDS if values.get(field) and not _valid_date(values[field])]
            if invalid_dates:
                classification = "rejected"
                reasons.extend(f"invalid_date:{field}" for field in sorted(invalid_dates))
            invalid_fte = [field for field in FTE_FIELDS if values.get(field) and not self._valid_fte(values[field])]
            if invalid_fte and classification != "rejected":
                classification = "quarantined"
                reasons.extend(f"invalid_fte:{field}" for field in sorted(invalid_fte))
            record_id = values.get("source_record_id") or None
            if record_id and record_id in seen_ids:
                classification = "rejected"
                reasons.append("duplicate_source_record_id")
            if record_id:
                seen_ids.add(record_id)
            position_key = (
                values.get("position_number", ""),
                values.get("effective_date") or values.get("snapshot_date", ""),
                values.get("primary_secondary", ""),
            )
            if position_key[0] and position_key in seen_positions and classification != "rejected":
                classification = "quarantined"
                reasons.append("duplicate_position_effective_record")
            if position_key[0]:
                seen_positions.add(position_key)
            identity_id = link_method = None
            conflicts: tuple[str, ...] = ()
            if classification != "rejected":
                identity_id, link_method, conflicts = self.identity_linker.link(
                    values.get("institutional_person_identifier", ""),
                    values.get("email") or None,
                    values.get("published_person_name", ""),
                )
                if conflicts:
                    classification = "quarantined"
                    reasons.append("identity_conflict:" + ",".join(conflicts))
            unit = self.unit_registry.resolve_published_label(values.get("appointment_academic_unit")).unit
            limitations = []
            if not identity_id:
                limitations.append("identity_unlinked")
            if not unit:
                limitations.append("academic_unit_unresolved")
            missing_recommended = [field for field in self.schema.recommended_fields if not values.get(field)]
            if missing_recommended:
                limitations.append("denominator_fields_incomplete")
            if classification == "accepted" and limitations:
                classification = "accepted_with_limitations"
            reasons.extend(limitations)
            observation = None
            if classification in ACCEPTED:
                observation = self._observation(values, identity_id, link_method, unit.unit_id if unit else None, source_hash, row_number, limitations)
            results.append(FacultyRosterRowResult(
                row_number=row_number,
                classification=classification,
                reasons=tuple(sorted(set(reasons))),
                source_record_id=record_id,
                observation=observation,
                published_values=dict(sorted(values.items())),
            ))
        summary = self._summary(results, unmapped)
        semantic = {
            "algorithm": ALGORITHM, "algorithm_version": ALGORITHM_VERSION,
            "schema_fingerprint": self.schema.deterministic_fingerprint,
            "source_fingerprint": source_hash,
            "rows": [row.to_dict() for row in results], "summary": summary,
        }
        return FacultyRosterIngestionResult(
            tuple(results), summary, self.schema.deterministic_fingerprint,
            source_hash, fingerprint(semantic),
        )

    def _column_map(self, fieldnames: list[str]) -> tuple[dict[str, str], tuple[str, ...]]:
        normalized = {name.strip().casefold(): name for name in fieldnames}
        mapping: dict[str, str] = {}
        used: set[str] = set()
        for field, aliases in self.schema.column_aliases.items():
            matches = [normalized[value.strip().casefold()] for value in aliases if value.strip().casefold() in normalized]
            if len(matches) > 1:
                raise ValueError(f"Multiple source columns map to {field}: {matches}")
            if matches:
                mapping[field] = matches[0]
                used.add(matches[0])
        return mapping, tuple(sorted(set(fieldnames) - used))

    def _valid_fte(self, value: str) -> bool:
        try:
            parsed = Decimal(value)
        except InvalidOperation:
            return False
        return Decimal(str(self.schema.fte_minimum)) <= parsed <= Decimal(str(self.schema.fte_maximum))

    def _observation(self, values, identity_id, link_method, unit_id, source_hash, row_number, limitations):
        fitness = ["explicit_employment_status"]
        fitness.append("authoritative_effective_dated_appointment" if values.get("effective_date") else "authoritative_snapshot_roster")
        if values.get("home_department"):
            fitness.append("explicit_faculty_home")
        for field, category in (
            ("appointment_fte", "explicit_appointment_fte"),
            ("instructional_fte", "explicit_instructional_fte"),
            ("tenure_status", "explicit_tenure_status"),
        ):
            if values.get(field):
                fitness.append(category)
        if identity_id:
            fitness.append("identifier_link" if link_method in {"institutional_identifier", "email"} else "name_link")
        if "denominator_fields_incomplete" in limitations:
            fitness.append("denominator_fields_incomplete")
        factual = {field: values.get(field) or None for field in self.schema.canonical_fields}
        provenance = {
            "source_file": _repository_relative(self.input_path),
            "source_file_sha256": source_hash,
            "source_row_number": row_number,
            "schema_id": self.schema.schema_id,
            "schema_fingerprint": self.schema.deterministic_fingerprint,
            "algorithm": ALGORITHM,
            "algorithm_version": ALGORITHM_VERSION,
        }
        semantic = {
            **factual, "faculty_identity_id": identity_id,
            "identity_link_method": link_method, "academic_unit_id": unit_id,
            "evidence_fitness": sorted(set(fitness)),
            "evidence_limitations": sorted(set(limitations)), "provenance": provenance,
        }
        digest = fingerprint(semantic)
        return AuthoritativeFacultyRosterObservation(
            observation_id=f"authoritative_faculty_roster_observation:{digest}",
            object_type="authoritative_faculty_roster_observation",
            faculty_identity_id=identity_id, identity_link_method=link_method,
            academic_unit_id=unit_id,
            evidence_fitness=tuple(semantic["evidence_fitness"]),
            evidence_limitations=tuple(semantic["evidence_limitations"]),
            provenance=provenance, deterministic_fingerprint=digest,
            **factual,
        )

    def _summary(self, results, unmapped):
        counts = Counter(row.classification for row in results)
        accepted = [row.observation for row in results if row.observation]
        linked = sum(item.faculty_identity_id is not None for item in accepted)
        return {
            "source_row_count": len(results),
            "accepted_row_count": counts["accepted"],
            "accepted_with_limitations_row_count": counts["accepted_with_limitations"],
            "accepted_observation_count": len(accepted),
            "quarantined_row_count": counts["quarantined"],
            "rejected_row_count": counts["rejected"],
            "identity_linked_count": linked,
            "identity_unlinked_count": len(accepted) - linked,
            "identity_link_coverage_percent": _percent(linked, len(accepted)),
            "unit_resolved_count": sum(item.academic_unit_id is not None for item in accepted),
            "appointment_fte_coverage_count": sum(item.appointment_fte is not None for item in accepted),
            "instructional_fte_coverage_count": sum(item.instructional_fte is not None for item in accepted),
            "tenure_coverage_count": sum(item.tenure_status is not None for item in accepted),
            "appointment_category_coverage_count": sum(bool(item.appointment_category) for item in accepted),
            "effective_date_coverage_count": sum(bool(item.effective_date or item.snapshot_date) for item in accepted),
            "duplicate_source_record_id_count": sum("duplicate_source_record_id" in row.reasons for row in results),
            "duplicate_position_count": sum("duplicate_position_effective_record" in row.reasons for row in results),
            "identity_conflict_count": sum(any(reason.startswith("identity_conflict:") for reason in row.reasons) for row in results),
            "unmapped_source_columns": list(unmapped),
        }


def _valid_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _percent(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 6) if denominator else 0.0


def _repository_relative(path: Path) -> str:
    resolved = path.resolve()
    root = Path(__file__).resolve().parents[2]
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return path.name


__all__ = ["FacultyRosterCSVAdapter"]
