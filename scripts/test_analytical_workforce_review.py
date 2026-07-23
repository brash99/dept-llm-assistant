from __future__ import annotations

import yaml

from app.analytical_workforce import load_overrides
from app.institutional_units import AcademicUnitRegistry
from scripts.review_analytical_workforce import _save_choice, _unit_choices


class Decision:
    analytical_academic_unit_candidates = (
        "academic_unit:department_accounting_finance",
        "academic_unit:department_management_marketing",
    )
    published_academic_units = ("Luter School of Business",)


def _registry(path):
    path.write_text(
        "registry_id: test\nversion: '1.0'\ndescription: test\noverrides: []\n",
        encoding="utf-8",
    )


def test_review_choices_save_immediately_and_preserve_both_dimensions(tmp_path):
    path = tmp_path / "overrides.yaml"
    _registry(path)
    _save_choice(path, "faculty:test", "include", None, "include", "Edward Brash", "2026-07-22")
    assert load_overrides(path)[0].decision == "include"
    _save_choice(
        path, "faculty:test", "include",
        "academic_unit:department_accounting_finance",
        "assign unit", "Edward Brash", "2026-07-22",
    )
    record = load_overrides(path)[0]
    assert record.decision == "include"
    assert record.analytical_academic_unit_id == "academic_unit:department_accounting_finance"
    assert yaml.safe_load(path.read_text())["overrides"][0]["reviewer"] == "Edward Brash"


def test_exclusion_clears_department_assignment(tmp_path):
    path = tmp_path / "overrides.yaml"
    _registry(path)
    _save_choice(path, "faculty:test", "include", "academic_unit:department_history", "first", "Edward Brash", "2026-07-22")
    _save_choice(path, "faculty:test", "exclude", None, "second", "Edward Brash", "2026-07-22")
    record = load_overrides(path)[0]
    assert record.decision == "exclude"
    assert record.analytical_academic_unit_id is None


def test_department_choices_are_deterministic_governed_units():
    choices = _unit_choices(Decision(), AcademicUnitRegistry.load())
    assert [item.unit_id for item in choices] == [
        "academic_unit:department_accounting_finance",
        "academic_unit:department_management_marketing",
    ]
