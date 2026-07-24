from __future__ import annotations

import json

from app.reasoning import ScheduleAnalysisService
from scripts import analyze_schedule


OBSERVATIONS = (
    {
        "id": "one", "object_type": "course_offering_observation",
        "academic_term": "2024_spring", "subject": "CPSC",
        "instructor_raw": "A Person",
        "instructor_type": {"normalized_value": "adjunct", "conflicting": False},
    },
    {
        "id": "two", "object_type": "course_offering_observation",
        "academic_term": "2024_fall", "subject": "CPSC",
        "instructor_raw": "B Person",
        "instructor_type": {"normalized_value": "full_time", "conflicting": False},
    },
)


class FixtureService(ScheduleAnalysisService):
    def load_observations(self):
        return OBSERVATIONS


def test_cli_json_subject_aggregation(monkeypatch, capsys):
    monkeypatch.setattr(analyze_schedule, "ScheduleAnalysisService", FixtureService)
    monkeypatch.setattr("sys.argv", [
        "analyze_schedule", "Count offerings by subject and term",
        "--schedule-root", "unused", "--metric", "course_offerings",
        "--group-by", "subject", "academic_term", "--json",
    ])
    assert analyze_schedule.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["metric"] == "course_offerings"
    assert len(payload["grouped_results"]) == 2
    assert payload["grouping"] == ["subject", "academic_term"]


def test_cli_csv_trend_and_term_filter(monkeypatch, capsys):
    monkeypatch.setattr(analyze_schedule, "ScheduleAnalysisService", FixtureService)
    monkeypatch.setattr("sys.argv", [
        "analyze_schedule", "Show adjunct offering share trends by subject",
        "--schedule-root", "unused", "--metric", "adjunct_offering_share",
        "--group-by", "subject", "academic_term", "--trend", "--csv",
        "--term-from", "2024_spring", "--term-to", "2024_fall",
    ])
    assert analyze_schedule.main() == 0
    output = capsys.readouterr().out
    assert "first_term,last_term" in output
    assert "2024_spring,2024_fall" in output
