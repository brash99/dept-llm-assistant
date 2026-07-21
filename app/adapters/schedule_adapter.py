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


ADAPTER_NAME = "schedule_csv_adapter"
ADAPTER_VERSION = "0.1"
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
    raw_record: Dict[str, Any],
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
            # Preserve uniqueness when the source lacks its normal section ID.
            "raw_record": raw_record,
        }
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
    subject: Optional[str] = None
    course_number: Optional[str] = None
    course_code: str = ""
    course_title: Optional[str] = None
    section: str = ""
    crn: Optional[str] = None
    instructor_name: Optional[str] = None
    instructor_raw: Optional[str] = None
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
    provenance: Dict[str, Any] = field(default_factory=dict)
    raw_record: Dict[str, Any] = field(default_factory=dict)

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


@dataclass
class ScheduleAdaptationResult:
    observations: list[CourseOfferingObservation] = field(default_factory=list)
    rows_processed: int = 0
    rows_skipped: int = 0
    duplicate_observations: int = 0
    missing_required_fields: Counter[str] = field(default_factory=Counter)
    parsing_warnings: Counter[str] = field(default_factory=Counter)
    source_headers: list[str] = field(default_factory=list)


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
        academic_term, term_warning = _term_from_filename(self.source_path)
        source_hash = _source_sha256(self.source_path)
        seen_ids = set()

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
                raw_record = _raw_record(row)
                row_warnings: Counter[str] = Counter()

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
                observation_id = _observation_id(
                    academic_term=academic_term,
                    crn=crn_raw,
                    course_code=course_code_raw,
                    section=section_raw,
                    raw_record=raw_record,
                )
                if observation_id in seen_ids:
                    result.duplicate_observations += 1
                    result.rows_skipped += 1
                    continue
                seen_ids.add(observation_id)

                subject, course_number = _split_course_code(course_code_raw)
                if course_number is None:
                    row_warnings["course_code_could_not_split_preserved_raw"] += 1

                credits_raw = self._value(row, columns, "credits")
                credits = _parse_scalar_number(
                    credits_raw,
                    field_name="credits",
                    warnings=row_warnings,
                )

                time_raw = self._value(row, columns, "meeting_time")
                start_time, end_time = _parse_meeting_time(time_raw, row_warnings)
                days_raw = self._value(row, columns, "meeting_days")
                meeting_pattern = " ".join(
                    value for value in (days_raw, time_raw) if value
                ) or None

                location_raw = self._value(row, columns, "location")
                building, room = _parse_location(location_raw, row_warnings)

                numeric_values = {
                    name: _parse_integer(
                        self._value(row, columns, name),
                        field_name=name,
                        warnings=row_warnings,
                    )
                    for name in INTEGER_FIELDS
                }

                instructor_raw = self._value(row, columns, "instructor")
                acquisition_date_raw = self._value(
                    row, columns, "acquisition_date"
                )
                if term_warning:
                    row_warnings[term_warning] += 1

                result.parsing_warnings.update(row_warnings)
                normalized_at = timestamp.isoformat()
                source_filename = self.source_path.name
                provenance = {
                    "source_filename": source_filename,
                    "source_path": str(self.source_path),
                    "source_row": source_row,
                    "ingested_at": normalized_at,
                    "source_sha256": source_hash,
                    "adapter": ADAPTER_NAME,
                    "adapter_version": ADAPTER_VERSION,
                    "source_headers": headers,
                }

                course_title = self._value(row, columns, "course_title")
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
                        "parsing_warnings": dict(row_warnings),
                    },
                    source={
                        "kind": "institutional_schedule_csv",
                        "path": str(self.source_path),
                        "filename": source_filename,
                        "row": source_row,
                        "content_hash": source_hash,
                    },
                    created_at=None,
                    normalized_at=normalized_at,
                    observation_id=observation_id,
                    source_file=source_filename,
                    source_row=source_row,
                    acquisition_date=acquisition_date_raw or None,
                    academic_term=academic_term,
                    subject=subject,
                    course_number=course_number,
                    course_code=course_code_raw,
                    course_title=course_title or None,
                    section=section_raw,
                    crn=crn_raw or None,
                    instructor_name=instructor_raw or None,
                    instructor_raw=instructor_raw or None,
                    instructional_method=(
                        self._value(row, columns, "instructional_method") or None
                    ),
                    meeting_pattern=meeting_pattern,
                    meeting_days=days_raw or None,
                    meeting_time_raw=time_raw or None,
                    start_time=start_time,
                    end_time=end_time,
                    meeting_date_range_raw=(
                        self._value(row, columns, "meeting_date_range") or None
                    ),
                    start_date=self._value(row, columns, "start_date") or None,
                    end_date=self._value(row, columns, "end_date") or None,
                    location_raw=location_raw or None,
                    building=building,
                    room=room,
                    credits=credits,
                    credits_raw=credits_raw or None,
                    enrollment=numeric_values["enrollment"],
                    capacity=numeric_values["capacity"],
                    waitlist=numeric_values["waitlist"],
                    seats_available=numeric_values["seats_available"],
                    status=self._value(row, columns, "status") or None,
                    campus=self._value(row, columns, "campus") or None,
                    notes=self._value(row, columns, "notes") or None,
                    llc_area_raw=self._value(row, columns, "llc_area") or None,
                    reserved=numeric_values["reserved"],
                    reserved_available=numeric_values["reserved_available"],
                    unreserved=numeric_values["unreserved"],
                    unreserved_available=numeric_values["unreserved_available"],
                    low_cost_textbook_raw=(
                        self._value(row, columns, "low_cost_textbook") or None
                    ),
                    modality=self._value(row, columns, "modality") or None,
                    provenance=provenance,
                    raw_record=raw_record,
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
