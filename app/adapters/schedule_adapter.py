"""Adapt raw Schedule of Classes CSV evidence into Knowledge Objects.

The adapter performs factual extraction only. It does not resolve instructors,
infer departments or curricula, assess capacity, or derive institutional
meaning from the schedule observations.
"""

from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from app.knowledge import KnowledgeObject, save_knowledge_object
from app.schedule_repair import (
    REPAIR_ALGORITHM,
    REPAIR_VERSION,
    ScheduleRepairAnalysis,
    ScheduleRepairGroup,
    ScheduleRepairRow,
    ScheduleRepairService,
)


ADAPTER_NAME = "schedule_csv_adapter"
ADAPTER_VERSION = "0.3"
OBJECT_TYPE = "course_offering_observation"


# Aliases are matched after case and punctuation normalization. Positions are
# never used, so reordered exports remain readable.
COLUMN_ALIASES = {
    "crn": ("CRN", "Course Reference Number"),
    "course_code": ("Course", "Course Code"),
    "section": ("Section", "Section Number"),
    "course_title": ("Title", "Course Title"),
    "credits": ("Hours", "Credits", "Credit Hours"),
    "llc_area": ("Area of LLC", "LLC Area"),
    "instructional_method": ("Type", "Instructional Method", "Method"),
    "meeting_days": ("Days", "Meeting Days"),
    "meeting_time": ("Time", "Meeting Time"),
    "meeting_date_range": ("Date Range", "Meeting Dates"),
    "start_date": ("Start Date", "Meeting Start Date"),
    "end_date": ("End Date", "Meeting End Date"),
    "location": ("Location", "Meeting Location"),
    "modality": ("Modality", "Instructional Modality"),
    "instructor": ("Instructor", "Instructor Name"),
    "instructor_type": ("Instructor Type",),
    "seats_available": ("Seats Still Available", "Seats Available"),
    "status": ("STATUS", "Status"),
    "enrollment": ("Enrolled", "Enrollment"),
    "capacity": ("Capacity", "Enrollment Capacity"),
    "waitlist": ("Waitlist", "Wait List", "Waitlisted"),
    "reserved": ("Reserved",),
    "reserved_available": ("Reserved Available",),
    "unreserved": ("Unreserved",),
    "unreserved_available": ("Unreserved Available",),
    "campus": ("Campus",),
    "notes": ("Notes", "Comments"),
    "low_cost_textbook": ("Low Cost Textbook",),
    "acquisition_date": ("Acquisition Date", "Acquired At"),
    "academic_term": ("Term", "Academic Term"),
}

REQUIRED_LOGICAL_FIELDS = ("course_code", "section")
INTEGER_FIELDS = (
    "enrollment",
    "capacity",
    "waitlist",
    "seats_available",
    "reserved",
    "reserved_available",
    "unreserved",
    "unreserved_available",
)


def _normalized_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _term_from_filename(path: Path) -> Tuple[str, Optional[str]]:
    """Use the evidence filename as the factual term label."""
    term = path.stem
    if re.fullmatch(
        r"\d{4}_(?:spring|fall|summer\d*|maymester|winter)",
        term.casefold(),
    ):
        return term, None
    return term, "academic_term_unrecognized_filename_pattern"


def normalize_academic_term(published_value: str) -> Tuple[str, Optional[str]]:
    """Normalize a published term label without discarding that label."""
    value = published_value.strip()
    patterns = (
        (r"Fall Semester (\d{4})", "{year}_fall"),
        (r"Spring Semester (\d{4})", "{year}_spring"),
        (r"May Term (\d{4})", "{year}_may"),
        (r"Summer Term (?:I|1) (\d{4})", "{year}_summer_1"),
        (r"Summer Term (?:II|2) (\d{4})", "{year}_summer_2"),
        (r"Extended Summer(?: Term)? (\d{4})", "{year}_extended_summer"),
    )
    for pattern, template in patterns:
        match = re.fullmatch(pattern, value, flags=re.IGNORECASE)
        if match:
            return template.format(year=match.group(1)), None
    return value, "academic_term_unrecognized_published_label"


def normalize_instructor_type(published_values: Sequence[str]) -> Dict[str, Any]:
    """Preserve section-level source assertions and normalize conservatively."""
    values = tuple(dict.fromkeys(str(value) for value in published_values))
    nonblank = tuple(value for value in values if value.strip())
    mappings = {"full time": "full_time", "adjunct": "adjunct"}
    normalized = {
        mappings.get(value.strip().casefold(), "unknown") for value in nonblank
    }
    normalized_value = (
        next(iter(normalized))
        if len(normalized) == 1 and "unknown" not in normalized
        else "unknown"
    )
    return {
        "published_value": nonblank[0] if len(nonblank) == 1 else None,
        "published_values": list(nonblank),
        "normalized_value": normalized_value,
        "has_blank_value": any(not value.strip() for value in values) or not values,
        "conflicting": len(nonblank) > 1,
    }


def _split_course_code(raw_value: str) -> Tuple[Optional[str], Optional[str]]:
    value = raw_value.strip()
    if not value:
        return None, None
    parts = value.split(maxsplit=1)
    if len(parts) != 2:
        return parts[0], None
    return parts[0], parts[1]


def _parse_scalar_number(
    raw_value: str,
    *,
    field_name: str,
    warnings: Counter[str],
) -> Optional[float]:
    value = raw_value.strip()
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError:
        warnings[f"{field_name}_non_scalar_preserved_raw"] += 1
        return None
    return int(parsed) if parsed.is_integer() else parsed


def _parse_integer(
    raw_value: str,
    *,
    field_name: str,
    warnings: Counter[str],
) -> Optional[int]:
    value = raw_value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        warnings[f"{field_name}_not_integer_preserved_raw"] += 1
        return None


def _format_clock(value: str) -> Optional[str]:
    if not re.fullmatch(r"\d{4}", value):
        return None
    hours = int(value[:2])
    minutes = int(value[2:])
    if hours > 23 or minutes > 59:
        return None
    return f"{hours:02d}:{minutes:02d}"


def _parse_meeting_time(
    raw_value: str,
    warnings: Counter[str],
) -> Tuple[Optional[str], Optional[str]]:
    value = raw_value.strip()
    if not value:
        return None, None
    match = re.fullmatch(r"(\d{4})-(\d{4})", value)
    if match is None:
        warnings["meeting_time_complex_or_unrecognized_preserved_raw"] += 1
        return None, None
    start = _format_clock(match.group(1))
    end = _format_clock(match.group(2))
    if start is None or end is None:
        warnings["meeting_time_invalid_clock_preserved_raw"] += 1
        return None, None
    return start, end


def _parse_location(
    raw_value: str,
    warnings: Counter[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Split only the simple observed `BUILDING ROOM` representation."""
    value = raw_value.strip()
    if not value:
        return None, None
    if ";" in value:
        warnings["location_multiple_or_complex_preserved_raw"] += 1
        return None, None
    parts = value.split()
    if len(parts) != 2:
        warnings["location_not_building_room_pair_preserved_raw"] += 1
        return None, None
    return parts[0], parts[1]


def _raw_record(row: Dict[Optional[str], Any]) -> Dict[str, Any]:
    """Preserve CSV-decoded values while making exceptional keys JSON-safe."""
    record: Dict[str, Any] = {}
    for key, value in row.items():
        if key is None:
            record["__extra_columns__"] = value
        else:
            record[key] = value
    return record


def _observation_id(
    *,
    academic_term: str,
    crn: str,
    course_code: str,
    section: str,
) -> str:
    """Create a stable identity, preferring term plus institutional CRN."""
    if crn.strip():
        identity = {
            "academic_term": academic_term,
            "crn": crn,
        }
    else:
        identity = {
            "academic_term": academic_term,
            "course_code": course_code,
            "section": section,
        }
    identity["course_code"] = course_code.strip()
    identity["section"] = section.strip()
    payload = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class CourseOfferingObservation(KnowledgeObject):
    """One factual observation of a scheduled course section."""

    observation_id: str = ""
    source_file: str = ""
    source_row: int = 0
    acquisition_date: Optional[str] = None
    academic_term: str = ""
    academic_term_published: Optional[str] = None
    subject: Optional[str] = None
    course_number: Optional[str] = None
    course_code: str = ""
    course_title: Optional[str] = None
    section: str = ""
    crn: Optional[str] = None
    instructor_name: Optional[str] = None
    instructor_raw: Optional[str] = None
    instructor_type: Dict[str, Any] = field(default_factory=dict)
    course_title_assertion: Dict[str, Any] = field(default_factory=dict)
    credits_assertion: Dict[str, Any] = field(default_factory=dict)
    instructional_method: Optional[str] = None
    meeting_pattern: Optional[str] = None
    meeting_days: Optional[str] = None
    meeting_time_raw: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    meeting_date_range_raw: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location_raw: Optional[str] = None
    building: Optional[str] = None
    room: Optional[str] = None
    credits: Optional[float] = None
    credits_raw: Optional[str] = None
    enrollment: Optional[int] = None
    capacity: Optional[int] = None
    waitlist: Optional[int] = None
    seats_available: Optional[int] = None
    status: Optional[str] = None
    campus: Optional[str] = None
    notes: Optional[str] = None
    llc_area_raw: Optional[str] = None
    reserved: Optional[int] = None
    reserved_available: Optional[int] = None
    unreserved: Optional[int] = None
    unreserved_available: Optional[int] = None
    low_cost_textbook_raw: Optional[str] = None
    modality: Optional[str] = None
    meeting_patterns: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    repair: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    raw_record: Dict[str, Any] = field(default_factory=dict)
    source_rows: Tuple[int, ...] = field(default_factory=tuple)
    raw_records: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    published_field_variants: Dict[str, Tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.object_type != OBJECT_TYPE:
            raise ValueError(
                f"CourseOfferingObservation.object_type must be {OBJECT_TYPE!r}"
            )
        if not self.observation_id or self.id != self.observation_id:
            raise ValueError("id and observation_id must contain the same stable ID")
        if not self.academic_term:
            raise ValueError("academic_term is required")
        if not self.course_code:
            raise ValueError("course_code is required")
        if not self.section:
            raise ValueError("section is required")
        self.source_rows = tuple(self.source_rows or ((self.source_row,) if self.source_row else ()))
        self.raw_records = tuple(dict(value) for value in (self.raw_records or ((self.raw_record,) if self.raw_record else ())))
        self.meeting_patterns = tuple(dict(value) for value in self.meeting_patterns)
        self.published_field_variants = {
            str(name): tuple(values)
            for name, values in self.published_field_variants.items()
        }


@dataclass
class ScheduleAdaptationResult:
    observations: list[CourseOfferingObservation] = field(default_factory=list)
    rows_processed: int = 0
    rows_skipped: int = 0
    duplicate_observations: int = 0
    missing_required_fields: Counter[str] = field(default_factory=Counter)
    parsing_warnings: Counter[str] = field(default_factory=Counter)
    source_headers: list[str] = field(default_factory=list)
    repair_analysis: Optional[ScheduleRepairAnalysis] = None


class ScheduleCSVAdapter:
    """Map a named-column schedule export to factual section observations."""

    def __init__(self, source_path: Path) -> None:
        self.source_path = Path(source_path)
        if not self.source_path.is_file():
            raise FileNotFoundError(f"Schedule CSV not found: {self.source_path}")

    @staticmethod
    def resolve_columns(headers: Sequence[str]) -> Dict[str, Optional[str]]:
        normalized_to_original = {
            _normalized_header(header): header
            for header in headers
            if header and _normalized_header(header)
        }
        resolved: Dict[str, Optional[str]] = {}
        for logical_name, aliases in COLUMN_ALIASES.items():
            resolved[logical_name] = next(
                (
                    normalized_to_original[_normalized_header(alias)]
                    for alias in aliases
                    if _normalized_header(alias) in normalized_to_original
                ),
                None,
            )
        return resolved

    @staticmethod
    def _value(
        row: Dict[Optional[str], Any],
        columns: Dict[str, Optional[str]],
        logical_name: str,
    ) -> str:
        header = columns.get(logical_name)
        if header is None:
            return ""
        value = row.get(header, "")
        return "" if value is None else str(value)

    def adapt(self, *, timestamp: Optional[datetime] = None) -> ScheduleAdaptationResult:
        timestamp = timestamp or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("Schedule adaptation timestamp must be timezone-aware")

        result = ScheduleAdaptationResult()
        source_hash = _source_sha256(self.source_path)
        grouped_rows: Dict[str, list[Tuple[int, Dict[Optional[str], Any], str, str]]] = {}

        with self.source_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError("Schedule CSV has no header row")

            headers = list(reader.fieldnames)
            result.source_headers = headers
            columns = self.resolve_columns(headers)
            for logical_name in REQUIRED_LOGICAL_FIELDS:
                if columns.get(logical_name) is None:
                    result.missing_required_fields[logical_name] += 1

            if result.missing_required_fields:
                return result

            for source_row, row in enumerate(reader, start=2):
                result.rows_processed += 1
                course_code_raw = self._value(row, columns, "course_code")
                section_raw = self._value(row, columns, "section")
                missing_in_row = False
                for name, value in (
                    ("course_code", course_code_raw),
                    ("section", section_raw),
                ):
                    if not value.strip():
                        result.missing_required_fields[name] += 1
                        missing_in_row = True

                if missing_in_row:
                    result.rows_skipped += 1
                    continue

                crn_raw = self._value(row, columns, "crn")
                term_raw = self._value(row, columns, "academic_term")
                if columns.get("academic_term") is None:
                    term_raw, term_warning = _term_from_filename(self.source_path)
                elif not term_raw.strip():
                    term_raw, term_warning = _term_from_filename(self.source_path)
                    term_warning = "academic_term_blank_used_filename_fallback"
                else:
                    term_warning = None
                academic_term, normalized_term_warning = normalize_academic_term(term_raw)
                if normalized_term_warning and columns.get("academic_term") is None:
                    # Legacy filename-derived values are already stable term IDs.
                    if re.fullmatch(r"\d{4}_(?:spring|fall|summer\d*|maymester|winter)", academic_term.casefold()):
                        normalized_term_warning = None
                observation_id = _observation_id(
                    academic_term=academic_term,
                    crn=crn_raw,
                    course_code=course_code_raw,
                    section=section_raw,
                )
                if observation_id in grouped_rows:
                    result.duplicate_observations += 1
                grouped_rows.setdefault(observation_id, []).append(
                    (source_row, row, term_raw, term_warning or normalized_term_warning or "")
                )

            repair_groups = []
            for observation_id, items in grouped_rows.items():
                first = items[0]
                academic_term, _ = normalize_academic_term(first[2])
                logical_rows = tuple(
                    ScheduleRepairRow(
                        source_row=source_row,
                        values={
                            logical_name: self._value(row, columns, logical_name)
                            for logical_name in COLUMN_ALIASES
                        },
                        raw_record=_raw_record(row),
                    )
                    for source_row, row, *_ in items
                )
                repair_groups.append(
                    ScheduleRepairGroup(
                        observation_id=observation_id,
                        academic_term=academic_term,
                        course_code=self._value(first[1], columns, "course_code"),
                        instructor=self._value(first[1], columns, "instructor"),
                        rows=logical_rows,
                    )
                )
            result.repair_analysis = ScheduleRepairService(
                repair_groups,
                source_sha256=source_hash,
                allow_later_term_fallback=False,
            ).analyze()

            for observation_id, items in grouped_rows.items():
                source_rows = tuple(item[0] for item in items)
                rows = tuple(item[1] for item in items)
                raw_records = tuple(_raw_record(row) for row in rows)
                row_warnings: Counter[str] = Counter(
                    warning for *_, warning in items if warning
                )

                def distinct_values(logical_name: str, *, include_blank: bool = False) -> Tuple[str, ...]:
                    values = tuple(dict.fromkeys(
                        self._value(row, columns, logical_name) for row in rows
                    ))
                    return values if include_blank else tuple(value for value in values if value != "")

                variants: Dict[str, Tuple[str, ...]] = {}
                for logical_name in COLUMN_ALIASES:
                    values = distinct_values(logical_name, include_blank=True)
                    if len(values) > 1:
                        variants[logical_name] = values
                        row_warnings[f"{logical_name}_conflicting_source_values"] += 1

                def first_value(logical_name: str) -> str:
                    values = distinct_values(logical_name)
                    return values[0] if values else ""

                course_code_raw = first_value("course_code")
                section_raw = first_value("section")
                crn_raw = first_value("crn")
                term_published = items[0][2]
                academic_term, _ = normalize_academic_term(term_published)

                subject, course_number = _split_course_code(course_code_raw)
                if course_number is None:
                    row_warnings["course_code_could_not_split_preserved_raw"] += 1

                repair_decision = result.repair_analysis.decisions[observation_id]
                credit_assertion = repair_decision["credits"]
                credit_values = tuple(credit_assertion["published_values"])
                credits_raw = " | ".join(credit_values)
                credits = _parse_scalar_number(
                    credit_assertion["normalized_value"] or "",
                    field_name="credits",
                    warnings=row_warnings,
                )

                meeting_patterns = tuple(repair_decision["meeting_patterns"])
                if len(meeting_patterns) == 1:
                    days_raw = meeting_patterns[0]["days_published"] or ""
                    time_raw = meeting_patterns[0]["time_published"] or ""
                    location_raw = meeting_patterns[0]["location_published"] or ""
                    start_time, end_time = _parse_meeting_time(time_raw, row_warnings)
                    building, room = _parse_location(location_raw, row_warnings)
                    meeting_pattern = " ".join(value for value in (days_raw, time_raw) if value) or None
                else:
                    days_raw = time_raw = location_raw = ""
                    start_time = end_time = building = room = meeting_pattern = None
                    row_warnings["multiple_meeting_patterns_preserved"] += 1

                numeric_values = {}
                for name in INTEGER_FIELDS:
                    values = distinct_values(name)
                    numeric_values[name] = _parse_integer(
                        values[0] if len(values) == 1 else "",
                        field_name=name,
                        warnings=row_warnings,
                    )
                    if len(values) > 1:
                        row_warnings[f"{name}_conflict_not_reduced"] += 1

                instructor_values = distinct_values("instructor")
                instructor_raw = instructor_values[0] if len(instructor_values) == 1 else " | ".join(instructor_values)
                instructor_type = repair_decision["instructor_type"]
                if (
                    not instructor_type["conflicting"]
                    and
                    columns.get("instructor_type") is not None
                    and instructor_type["normalized_value"] == "unknown"
                ):
                    row_warnings["instructor_type_unknown"] += 1
                acquisition_date_raw = first_value("acquisition_date")

                result.parsing_warnings.update(row_warnings)
                normalized_at = timestamp.isoformat()
                source_filename = self.source_path.name
                provenance = {
                    "source_filename": source_filename,
                    "source_path": str(self.source_path),
                    "source_row": source_rows[0],
                    "source_rows": list(source_rows),
                    "source_row_count": len(source_rows),
                    "ingested_at": normalized_at,
                    "source_sha256": source_hash,
                    "adapter": ADAPTER_NAME,
                    "adapter_version": ADAPTER_VERSION,
                    "source_headers": headers,
                }

                title_assertion = repair_decision["course_title"]
                course_title = title_assertion["normalized_value"]
                factual_lines = [
                    f"Academic term: {academic_term}",
                    f"Course: {course_code_raw}",
                    f"Section: {section_raw}",
                ]
                if course_title:
                    factual_lines.append(f"Title: {course_title}")
                if crn_raw:
                    factual_lines.append(f"CRN: {crn_raw}")

                observation = CourseOfferingObservation(
                    id=observation_id,
                    object_type=OBJECT_TYPE,
                    title=(
                        f"Course Offering: {course_code_raw} "
                        f"Section {section_raw} ({academic_term})"
                    ),
                    text="\n".join(factual_lines),
                    metadata={
                        "semantic_layer": "course_offering_observation",
                        "adapter": ADAPTER_NAME,
                        "adapter_version": ADAPTER_VERSION,
                        "repair_algorithm": REPAIR_ALGORITHM,
                        "repair_version": REPAIR_VERSION,
                        "parsing_warnings": dict(row_warnings),
                    },
                    source={
                        "kind": "institutional_schedule_csv",
                        "path": str(self.source_path),
                        "filename": source_filename,
                        "row": source_rows[0],
                        "content_hash": source_hash,
                    },
                    created_at=None,
                    normalized_at=normalized_at,
                    observation_id=observation_id,
                    source_file=source_filename,
                    source_row=source_rows[0],
                    acquisition_date=acquisition_date_raw or None,
                    academic_term=academic_term,
                    academic_term_published=term_published,
                    subject=subject,
                    course_number=course_number,
                    course_code=course_code_raw,
                    course_title=course_title or None,
                    section=section_raw,
                    crn=crn_raw or None,
                    instructor_name=instructor_raw or None,
                    instructor_raw=instructor_raw or None,
                    instructor_type=instructor_type,
                    course_title_assertion=title_assertion,
                    credits_assertion=credit_assertion,
                    instructional_method=(
                        first_value("instructional_method") or None
                    ),
                    meeting_pattern=meeting_pattern,
                    meeting_days=days_raw or None,
                    meeting_time_raw=time_raw or None,
                    start_time=start_time,
                    end_time=end_time,
                    meeting_date_range_raw=(
                        first_value("meeting_date_range") or None
                    ),
                    start_date=first_value("start_date") or None,
                    end_date=first_value("end_date") or None,
                    location_raw=location_raw or None,
                    building=building,
                    room=room,
                    credits=credits,
                    credits_raw=credits_raw or None,
                    enrollment=numeric_values["enrollment"],
                    capacity=numeric_values["capacity"],
                    waitlist=numeric_values["waitlist"],
                    seats_available=numeric_values["seats_available"],
                    status=first_value("status") or None,
                    campus=first_value("campus") or None,
                    notes=first_value("notes") or None,
                    llc_area_raw=first_value("llc_area") or None,
                    reserved=numeric_values["reserved"],
                    reserved_available=numeric_values["reserved_available"],
                    unreserved=numeric_values["unreserved"],
                    unreserved_available=numeric_values["unreserved_available"],
                    low_cost_textbook_raw=(
                        first_value("low_cost_textbook") or None
                    ),
                    modality=first_value("modality") or None,
                    meeting_patterns=meeting_patterns,
                    repair={
                        "algorithm": REPAIR_ALGORITHM,
                        "version": REPAIR_VERSION,
                        "repair_timestamp": normalized_at,
                        "source_file_sha256": source_hash,
                        "decision_fingerprint": repair_decision["decision_fingerprint"],
                        "source_row_hashes": repair_decision["source_row_hashes"],
                    },
                    provenance=provenance,
                    raw_record=raw_records[0],
                    source_rows=source_rows,
                    raw_records=raw_records,
                    published_field_variants=variants,
                )
                result.observations.append(observation)

        return result


def write_observations(
    observations: Iterable[CourseOfferingObservation],
    output_directory: Path,
) -> int:
    """Persist one JSON Knowledge Object per observation."""
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    count = 0
    for observation in observations:
        output_path = (
            output_directory
            / f"course_offering_{observation.observation_id}.json"
        )
        save_knowledge_object(observation, output_path)
        count += 1
    return count


__all__ = [
    "CourseOfferingObservation",
    "ScheduleAdaptationResult",
    "ScheduleCSVAdapter",
    "write_observations",
]
