import csv
from datetime import datetime, timezone
import json
from pathlib import Path

from app.adapters.schedule_adapter import (
    CourseOfferingObservation,
    ScheduleCSVAdapter,
    write_observations,
)
from app.knowledge import load_knowledge_object


FIXED_TIMESTAMP = datetime(2026, 7, 20, 12, 30, tzinfo=timezone.utc)


def _write_schedule(path: Path, rows: list[dict[str, str]]) -> None:
    headers = [
        "Instructor",
        "Section",
        "Course",
        "CRN",
        "Title",
        "Hours",
        "Days",
        "Time",
        "Location",
        "Enrolled",
        "Capacity",
        "Area of LLC",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "Instructor": "Doe, Jane  ",
        "Section": "01",
        "Course": "PHY 201",
        "CRN": "12345",
        "Title": "University Physics",
        "Hours": "4",
        "Days": "MWF",
        "Time": "0800-0850",
        "Location": "FORBES 2070C",
        "Enrolled": "22",
        "Capacity": "24",
        "Area of LLC": "Investigating the Natural World",
    }
    row.update(overrides)
    return row


def test_adapter_maps_named_columns_and_preserves_source_facts(tmp_path: Path) -> None:
    source = tmp_path / "2026_fall.csv"
    _write_schedule(source, [_row()])

    result = ScheduleCSVAdapter(source).adapt(timestamp=FIXED_TIMESTAMP)

    assert result.rows_processed == 1
    assert result.rows_skipped == 0
    assert result.duplicate_observations == 0
    observation = result.observations[0]
    assert observation.academic_term == "2026_fall"
    assert observation.subject == "PHY"
    assert observation.course_number == "201"
    assert observation.start_time == "08:00"
    assert observation.end_time == "08:50"
    assert observation.enrollment == 22
    assert observation.capacity == 24
    assert observation.instructor_raw == "Doe, Jane  "
    assert observation.raw_record == _row()
    assert observation.provenance["source_row"] == 2
    assert observation.provenance["ingested_at"] == FIXED_TIMESTAMP.isoformat()


def test_adapter_reports_duplicates_and_missing_required_values(tmp_path: Path) -> None:
    source = tmp_path / "2026_fall.csv"
    _write_schedule(
        source,
        [
            _row(),
            _row(),
            _row(CRN="54321", Course=""),
        ],
    )

    result = ScheduleCSVAdapter(source).adapt(timestamp=FIXED_TIMESTAMP)

    assert result.rows_processed == 3
    assert len(result.observations) == 1
    assert result.duplicate_observations == 1
    assert result.rows_skipped == 2
    assert result.missing_required_fields == {"course_code": 1}


def test_complex_values_remain_raw_when_not_safely_parseable(tmp_path: Path) -> None:
    source = tmp_path / "2026_fall.csv"
    _write_schedule(
        source,
        [_row(Hours="1-4", Time="TBA", Location="FORBES 100; LUTC 200")],
    )

    result = ScheduleCSVAdapter(source).adapt(timestamp=FIXED_TIMESTAMP)
    observation = result.observations[0]

    assert observation.credits is None
    assert observation.credits_raw == "1-4"
    assert observation.meeting_time_raw == "TBA"
    assert observation.start_time is None
    assert observation.location_raw == "FORBES 100; LUTC 200"
    assert observation.building is None
    assert result.parsing_warnings == {
        "credits_non_scalar_preserved_raw": 1,
        "meeting_time_complex_or_unrecognized_preserved_raw": 1,
        "location_multiple_or_complex_preserved_raw": 1,
    }


def test_written_observation_round_trips_through_shared_loader(tmp_path: Path) -> None:
    source = tmp_path / "2026_fall.csv"
    _write_schedule(source, [_row()])
    observation = ScheduleCSVAdapter(source).adapt(
        timestamp=FIXED_TIMESTAMP
    ).observations[0]
    output = tmp_path / "normalized"

    assert write_observations([observation], output) == 1
    saved_path = next(output.glob("course_offering_*.json"))
    loaded = load_knowledge_object(saved_path)

    assert isinstance(loaded, CourseOfferingObservation)
    assert loaded.to_dict() == observation.to_dict()
    assert json.loads(saved_path.read_text(encoding="utf-8"))["raw_record"] == _row()
