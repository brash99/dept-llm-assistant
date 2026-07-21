from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.adapters.schedule_adapter import (
    ScheduleCSVAdapter,
    normalize_academic_term,
)
from app.classification.classifiers import DeterministicSemanticClassifier


TIMESTAMP = datetime(2026, 7, 21, 16, 0, tzinfo=timezone.utc)
HEADERS = [
    "CRN", "Course", "Section", "Title", "Hours", "Area of LLC", "Type",
    "Days", "Time", "Location", "Instructor", "Seats Still Available",
    "Status", "Low Cost Textbook", "Capacity", "Enrolled",
    "Instructor Type", "Term",
]


def _row(**overrides):
    value = {
        "CRN": "12345", "Course": "PHY 201", "Section": "01",
        "Title": "University Physics", "Hours": "4", "Area of LLC": "",
        "Type": "Lecture", "Days": "MWF", "Time": "0800-0850",
        "Location": "Forbes Hall 2070C", "Instructor": "Example, Ada",
        "Seats Still Available": "-2", "Status": "Active",
        "Low Cost Textbook": "", "Capacity": "0", "Enrolled": "3",
        "Instructor Type": "Full Time", "Term": "Fall Semester 2026",
    }
    value.update(overrides)
    return value


def _write(path: Path, rows, *, bom=True):
    with path.open("w", encoding="utf-8-sig" if bom else "utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def test_exact_authoritative_header_and_bom_are_supported(tmp_path):
    path = tmp_path / "authoritative.csv"
    _write(path, [_row()])
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    result = ScheduleCSVAdapter(path).adapt(timestamp=TIMESTAMP)
    assert result.source_headers == HEADERS
    assert len(result.observations) == 1


@pytest.mark.parametrize(
    ("published", "normalized"),
    (("Full Time", "full_time"), ("Adjunct", "adjunct"), ("", "unknown"), ("Visitor", "unknown")),
)
def test_instructor_type_is_a_preserved_section_fact(tmp_path, published, normalized):
    path = tmp_path / "authoritative.csv"
    _write(path, [_row(**{"Instructor Type": published})])
    observation = ScheduleCSVAdapter(path).adapt(timestamp=TIMESTAMP).observations[0]
    assert observation.instructor_type["normalized_value"] == normalized
    assert observation.instructor_type["published_values"] == ([published] if published else [])
    proposal = DeterministicSemanticClassifier().classify(observation).to_dict()
    encoded = str(proposal).casefold()
    assert "employment" not in encoded
    assert "faculty_member" not in encoded
    assert normalized not in encoded


def test_valid_source_edge_conditions_are_not_rejected(tmp_path):
    path = tmp_path / "authoritative.csv"
    _write(path, [_row(Days="", Time="-", Hours="0")])
    result = ScheduleCSVAdapter(path).adapt(timestamp=TIMESTAMP)
    observation = result.observations[0]
    assert observation.seats_available == -2
    assert observation.capacity == 0
    assert observation.enrollment == 3
    assert observation.meeting_days is None
    assert observation.meeting_time_raw == "-"
    assert observation.credits == 0
    assert result.rows_skipped == 0


@pytest.mark.parametrize(
    ("published", "normalized"),
    (
        ("Fall Semester 2026", "2026_fall"),
        ("Spring Semester 2027", "2027_spring"),
        ("May Term 2026", "2026_may"),
        ("Summer Term I 2025", "2025_summer_1"),
        ("Summer Term 1 2024", "2024_summer_1"),
        ("Summer Term II 2026", "2026_summer_2"),
    ),
)
def test_term_variants_normalize_without_losing_published_label(published, normalized):
    assert normalize_academic_term(published) == (normalized, None)


def test_repeated_crns_across_terms_have_distinct_deterministic_ids(tmp_path):
    path = tmp_path / "authoritative.csv"
    rows = [_row(), _row(Term="Spring Semester 2027")]
    _write(path, rows)
    first = ScheduleCSVAdapter(path).adapt(timestamp=TIMESTAMP)
    second = ScheduleCSVAdapter(path).adapt(timestamp=TIMESTAMP)
    assert len(first.observations) == 2
    assert first.observations[0].id != first.observations[1].id
    assert [item.to_dict() for item in first.observations] == [item.to_dict() for item in second.observations]
    assert first.observations[0].academic_term_published == "Fall Semester 2026"


def test_conflicting_duplicate_section_assertions_are_preserved_without_guessing(tmp_path):
    path = tmp_path / "authoritative.csv"
    _write(path, [_row(), _row(**{"Instructor Type": "Adjunct"})])
    result = ScheduleCSVAdapter(path).adapt(timestamp=TIMESTAMP)
    assert len(result.observations) == 1
    assert result.duplicate_observations == 1
    observation = result.observations[0]
    assert observation.instructor_type["normalized_value"] == "unknown"
    assert observation.instructor_type["published_values"] == ["Full Time", "Adjunct"]
    assert observation.published_field_variants["instructor_type"] == ("Full Time", "Adjunct")
    assert observation.source_rows == (2, 3)
