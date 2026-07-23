#!/usr/bin/env python3
"""Interactively record reviewed analytical-workforce overrides."""

from __future__ import annotations

import argparse
from datetime import date
import os
from pathlib import Path
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytical_workforce import (  # noqa: E402
    AnalyticalWorkforceBuilder, AnalyticalWorkforcePolicy, load_overrides,
)
from app.faculty_appointments import FacultyAppointmentObservationService  # noqa: E402
from app.institutional_units import AcademicUnitRegistry  # noqa: E402
from app.metric_readiness_audit import load_normalized_objects  # noqa: E402


DEFAULT_OVERRIDES = Path("config/analytical_workforce_overrides.yaml")
SOURCE = "institutional_review:analytical_workforce_manual"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-root", type=Path, default=Path("storage/normalized"))
    parser.add_argument("--policy", type=Path, default=Path("config/analytical_workforce_policy.yaml"))
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--reviewer", default="Edward Brash")
    args = parser.parse_args(argv)

    objects, integrity = load_normalized_objects(args.normalized_root)
    if integrity["invalid_json_count"]:
        raise ValueError("Normalized corpus contains invalid JSON")
    policy = AnalyticalWorkforcePolicy.load(args.policy)
    decisions, _ = AnalyticalWorkforceBuilder(
        policy, load_overrides(args.overrides)
    ).build(objects)
    appointments = FacultyAppointmentObservationService().audit(objects)
    context = _appointment_context(appointments)
    registry = AcademicUnitRegistry.load()

    workforce = [item for item in decisions if item.workforce_disposition == "review_required"]
    departments = [item for item in decisions if item.department_assignment_disposition == "review_required"]
    print(f"Workforce membership reviews remaining: {len(workforce)}")
    print(f"Department assignment reviews remaining: {len(departments)}")

    for decision in workforce:
        _show_person(decision, context)
        print("Decision?\n\n    [i] Include in analytical workforce\n    [e] Exclude from analytical workforce\n    [s] Skip\n    [q] Quit\n")
        choice = input("Choice: ").strip().casefold()
        if choice == "q":
            return 0
        if choice not in {"i", "e"}:
            continue
        disposition = "include" if choice == "i" else "exclude"
        _save_choice(
            args.overrides, decision.faculty_identity_id,
            decision=disposition, unit_id=None,
            reason=f"Institutional review: {disposition} in analytical workforce.",
            reviewer=args.reviewer,
        )
        print("Saved.\n")

    # Rebuild so exclusions and any existing reviewed units are reflected.
    decisions, _ = AnalyticalWorkforceBuilder(
        policy, load_overrides(args.overrides)
    ).build(objects)
    departments = [item for item in decisions if item.department_assignment_disposition == "review_required"]
    for decision in departments:
        _show_person(decision, context)
        choices = _unit_choices(decision, registry)
        print("Select analytical department:\n")
        for index, unit in enumerate(choices, 1):
            print(f"    {index}. {unit.published_name}")
        print("\n    s = Skip\n    q = Quit\n")
        choice = input("Choice: ").strip().casefold()
        if choice == "q":
            return 0
        if not choice.isdigit() or not 1 <= int(choice) <= len(choices):
            continue
        unit = choices[int(choice) - 1]
        _save_choice(
            args.overrides, decision.faculty_identity_id,
            decision=decision.workforce_disposition,
            unit_id=unit.unit_id,
            reason=f"Institutional review: assign analytical unit {unit.unit_id}.",
            reviewer=args.reviewer,
        )
        print("Saved.\n")
    return 0


def _show_person(decision, context):
    value = context.get(decision.faculty_identity_id, {})
    positions = sorted({*value.get("positions", ()), *value.get("administrative", ())})
    print("\n" + "-" * 60)
    print(f"\nName:\n    {decision.display_name}")
    print("\nCurrent Positions:")
    for item in positions or ("Not published",):
        print(f"    {item}")
    print("\nPublished Departments:")
    for item in decision.published_academic_units or ("Not safely resolved",):
        print(f"    {item}")
    reason = (decision.workforce_primary_reason_code
              if decision.workforce_disposition == "review_required"
              else decision.department_assignment_primary_reason_code)
    print(f"\nReason:\n    {reason}\n")


def _appointment_context(audit):
    values = {}
    for item in audit.faculty_appointments:
        if not item.faculty_identity_id:
            continue
        target = values.setdefault(item.faculty_identity_id, {"positions": set(), "administrative": set()})
        target["positions"].update(item.published_titles)
    for item in audit.administrative_appointments:
        if item.faculty_identity_id:
            values.setdefault(item.faculty_identity_id, {"positions": set(), "administrative": set()})["administrative"].add(item.published_administrative_title)
    return values


def _unit_choices(decision, registry):
    ids = set(decision.analytical_academic_unit_candidates)
    for label in decision.published_academic_units:
        resolution = registry.resolve_published_label(label)
        if resolution.unit_id:
            ids.add(resolution.unit_id)
        ids.update(resolution.competing_unit_ids)
    units = [registry.get(unit_id) for unit_id in ids]
    choices = tuple(sorted(
        (unit for unit in units if unit.valid_faculty_home_unit and unit.active_current_unit and not unit.deprecated),
        key=lambda unit: (unit.published_name.casefold(), unit.unit_id),
    ))
    if choices:
        return choices
    # A genuinely unresolved published label still needs a manual governed choice.
    return tuple(sorted(
        (unit for unit in registry.units if unit.valid_faculty_home_unit and unit.active_current_unit and not unit.deprecated),
        key=lambda unit: (unit.published_name.casefold(), unit.unit_id),
    ))


def _save_choice(path, identity_id, decision, unit_id, reason, reviewer, review_date=None):
    path = Path(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    records = {item["faculty_identity_id"]: dict(item) for item in payload.get("overrides") or ()}
    prior = records.get(identity_id, {})
    records[identity_id] = {
        "faculty_identity_id": identity_id,
        "decision": decision or prior.get("decision"),
        "analytical_academic_unit_id": (
            None if decision == "exclude"
            else unit_id or prior.get("analytical_academic_unit_id")
        ),
        "reason": reason,
        "source": SOURCE,
        "source_type": "institutional_expert",
        "reviewer": reviewer,
        "review_date": review_date or date.today().isoformat(),
        "notes": "Recorded by scripts/review_analytical_workforce.py",
    }
    payload["overrides"] = [records[key] for key in sorted(records)]
    _atomic_yaml(path, payload)
    load_overrides(path)


def _atomic_yaml(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
        temporary = Path(handle.name)
    os.replace(temporary, path)


if __name__ == "__main__":
    raise SystemExit(main())
