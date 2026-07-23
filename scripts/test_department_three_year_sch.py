from __future__ import annotations

import json

import pytest

from scripts.build_department_three_year_sch import (
    _write_csv,
    build_three_year_report,
)


def _timeline():
    return {
        "departments": [{
            "department_name": "Test Department",
            "academic_years": [
                {"academic_year": "2021-22", "sch": 999},
                {"academic_year": "2022-23", "sch": 100},
                {"academic_year": "2023-24", "sch": 200},
                {"academic_year": "2024-25", "sch": 300},
                {"academic_year": "2025-26", "sch": 888},
            ],
        }],
    }


def test_only_requested_years_enter_arithmetic_mean():
    row = build_three_year_report(_timeline())["rows"][0]
    assert row == {
        "Department": "Test Department",
        "AY22-23": 100.0,
        "AY23-24": 200.0,
        "AY24-25": 300.0,
        "3-Year Avg": 200.0,
    }


def test_missing_requested_year_fails_explicitly():
    timeline = _timeline()
    timeline["departments"][0]["academic_years"].pop(2)
    with pytest.raises(ValueError, match="2023-24"):
        build_three_year_report(timeline)


def test_repeated_csv_and_json_are_byte_identical(tmp_path):
    first = build_three_year_report(_timeline())
    second = build_three_year_report(_timeline())
    assert first == second
    for number, payload in ((1, first), (2, second)):
        root = tmp_path / str(number)
        root.mkdir()
        _write_csv(root / "report.csv", payload["rows"])
        (root / "report.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )
    assert {
        path.name: path.read_bytes() for path in (tmp_path / "1").iterdir()
    } == {
        path.name: path.read_bytes() for path in (tmp_path / "2").iterdir()
    }
