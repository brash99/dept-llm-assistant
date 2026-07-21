from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from app.adapters.schedule_adapter import ScheduleCSVAdapter


NOW = datetime(2026, 7, 21, tzinfo=timezone.utc)
HEADERS = [
    "CRN", "Course", "Section", "Title", "Hours", "Area of LLC", "Type",
    "Days", "Time", "Location", "Instructor", "Seats Still Available",
    "Status", "Low Cost Textbook", "Capacity", "Enrolled", "Instructor Type", "Term",
]


def row(**values):
    result = {
        "CRN": "1001", "Course": "TEST 101", "Section": "01", "Title": "Original Title",
        "Hours": "3", "Area of LLC": "", "Type": "Lecture", "Days": "MWF",
        "Time": "0900-0950", "Location": "HALL 100", "Instructor": "Ada Example",
        "Seats Still Available": "5", "Status": "Active", "Low Cost Textbook": "",
        "Capacity": "25", "Enrolled": "20", "Instructor Type": "Full Time",
        "Term": "Fall Semester 2024",
    }
    result.update(values)
    return result


def write(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def adapt(tmp_path: Path, rows):
    path = tmp_path / "schedule.csv"
    write(path, rows)
    return ScheduleCSVAdapter(path).adapt(timestamp=NOW)


def by_crn(result, crn):
    return next(item for item in result.observations if item.crn == crn)


def test_authoritative_source_hash_is_unchanged():
    path = Path("data/acquisition/schedules/Faculty Schedule of Classes 2021 to 2026 by semester.csv")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "9ab803cc1715dd39a8ba8ba6890921ca04a1a8e0a20160dfcf785cc3de4aebc8"


def test_grouping_identity_ignores_descriptive_differences_and_preserves_rows(tmp_path):
    result = adapt(tmp_path, [row(), row(Title="Later Title", Hours="4", Days="R", Time="1400-1650", Location="LAB 2", **{"Instructor Type": "Adjunct"})])
    assert len(result.observations) == 1
    observation = result.observations[0]
    assert observation.source_rows == (2, 3)
    assert len(observation.raw_records) == 2
    assert len(observation.repair["source_row_hashes"]) == 2
    assert observation.instructor_type["conflicting"] is True


def test_same_instructor_same_term_consensus_resolves_but_keeps_conflict(tmp_path):
    result = adapt(tmp_path, [
        row(), row(**{"Instructor Type": "Adjunct"}),
        row(CRN="1002", Section="02", **{"Instructor Type": "Full Time"}),
        row(CRN="1003", Section="03", **{"Instructor Type": "Full Time"}),
    ])
    value = by_crn(result, "1001").instructor_type
    assert value["normalized_value"] == "full_time"
    assert value["conflicting"] is True
    assert value["resolution"]["method"] == "same_instructor_same_term_consensus"
    assert value["resolution"]["confidence"] == 1.0
    assert value["resolution"]["supporting_section_count"] == 2


def test_competing_same_term_status_evidence_does_not_resolve(tmp_path):
    result = adapt(tmp_path, [
        row(), row(**{"Instructor Type": "Adjunct"}),
        row(CRN="1002", Section="02", **{"Instructor Type": "Full Time"}),
        row(CRN="1003", Section="03", **{"Instructor Type": "Adjunct"}),
    ])
    value = by_crn(result, "1001").instructor_type
    assert value["normalized_value"] == "unknown"
    assert value["resolution"]["method"] == "unresolved_source_conflict"


def test_nearest_prior_consistent_term_resolves_with_reduced_confidence(tmp_path):
    result = adapt(tmp_path, [
        row(), row(**{"Instructor Type": "Adjunct"}),
        row(CRN="9001", Section="09", Term="Spring Semester 2024", **{"Instructor Type": "Adjunct"}),
    ])
    value = by_crn(result, "1001").instructor_type
    assert value["normalized_value"] == "adjunct"
    assert value["resolution"]["method"] == "same_instructor_nearest_prior_term"
    assert 0.65 <= value["resolution"]["confidence"] < 1.0


def test_contradictory_nearer_prior_blocks_older_and_later_is_not_used(tmp_path):
    result = adapt(tmp_path, [
        row(), row(**{"Instructor Type": "Adjunct"}),
        row(CRN="9001", Section="09", Term="Spring Semester 2024"),
        row(CRN="9001", Section="09", Term="Spring Semester 2024", **{"Instructor Type": "Adjunct"}),
        row(CRN="8001", Section="08", Term="Fall Semester 2023"),
        row(CRN="7001", Section="07", Term="Spring Semester 2025"),
    ])
    value = by_crn(result, "1001").instructor_type
    assert value["normalized_value"] == "unknown"
    assert value["resolution"]["method"] == "unresolved_source_conflict"


def test_unknown_blank_and_global_majority_do_not_vote(tmp_path):
    rows = [row(), row(**{"Instructor Type": "Adjunct"})]
    rows += [row(CRN=str(2000 + i), Section=str(i), Instructor="Someone Else", **{"Instructor Type": "Full Time"}) for i in range(10)]
    rows += [row(CRN="3001", Section="30", **{"Instructor Type": ""}), row(CRN="3002", Section="31", **{"Instructor Type": "Visitor"})]
    value = by_crn(adapt(tmp_path, rows), "1001").instructor_type
    assert value["normalized_value"] == "unknown"


def test_title_same_term_consensus_and_ambiguous_title(tmp_path):
    resolved = adapt(tmp_path, [
        row(), row(Title="Future Title"), row(CRN="1002", Section="02"), row(CRN="1003", Section="03"),
    ])
    assertion = by_crn(resolved, "1001").course_title_assertion
    assert assertion["normalized_value"] == "Original Title"
    assert assertion["resolution"]["method"] == "same_course_same_term_consensus"

    ambiguous = adapt(tmp_path, [
        row(), row(Title="Future Title"), row(CRN="1002", Section="02"), row(CRN="1003", Section="03", Title="Other Title"),
    ])
    assert by_crn(ambiguous, "1001").course_title is None
    assert by_crn(ambiguous, "1001").course_title_assertion["resolution"]["method"] == "unresolved_course_title_conflict"


def test_prior_title_is_preferred_over_later_title(tmp_path):
    result = adapt(tmp_path, [
        row(), row(Title="Future Title"),
        row(CRN="9001", Section="09", Term="Spring Semester 2024", Title="Original Title"),
        row(CRN="7001", Section="07", Term="Spring Semester 2025", Title="Future Title"),
    ])
    assertion = by_crn(result, "1001").course_title_assertion
    assert assertion["normalized_value"] == "Original Title"
    assert assertion["resolution"]["method"] == "same_course_nearest_prior_term"


def test_credit_consensus_and_variable_credit_remain_non_scalar(tmp_path):
    consensus = adapt(tmp_path, [row(), row(Hours="4"), row(CRN="1002", Section="02", Hours="3")])
    assert by_crn(consensus, "1001").credits == 3
    variable = adapt(tmp_path, [
        row(), row(Hours="4"), row(CRN="1002", Section="02", Hours="1"), row(CRN="1003", Section="03", Hours="3"),
    ])
    observation = by_crn(variable, "1001")
    assert observation.credits is None
    assert observation.credits_assertion["resolution"]["method"] == "legitimate_variable_credit"


def test_meeting_components_are_deduplicated_and_scalars_are_not_selected(tmp_path):
    result = adapt(tmp_path, [
        row(), row(), row(Days="R", Time="1400-1650", Location="LAB 2"),
    ])
    observation = result.observations[0]
    assert len(observation.meeting_patterns) == 2
    assert observation.meeting_patterns[0]["source_rows"] == [2, 3]
    assert observation.meeting_days is None
    assert observation.meeting_time_raw is None
    assert observation.location_raw is None


def test_repair_ids_and_fingerprints_are_deterministic(tmp_path):
    rows = [row(), row(**{"Instructor Type": "Adjunct"})]
    first = adapt(tmp_path, rows)
    second = adapt(tmp_path, rows)
    assert first.observations[0].id == second.observations[0].id
    assert first.observations[0].repair["decision_fingerprint"] == second.observations[0].repair["decision_fingerprint"]
