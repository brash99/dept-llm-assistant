#!/usr/bin/env python3
"""Validate governed faculty-identity precedence from production audit files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


GOVERNED_IDENTITIES = {
    "faculty_identity:patricia_siewe_seuchie": {
        "Patricia Seuchie", "Patricia Siewe Seuchie",
        "Patricia Angele Siewe Seuchie",
    },
    "faculty_identity:james_p_kelly": {"James P. Kelly", "J. P. Kelly"},
    "faculty_identity:shinhye_kim": {"Shinhye Kim", "S. Kim"},
    "faculty_identity:cynthia_vacca_davis": {
        "Cynthia Vacca Davis", "Cynthia Davis",
    },
    "faculty_identity:ann_mazzocca_bellecci": {
        "Ann Mazzocca Bellecci", "Ann Bellecci",
    },
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path):
    return tuple(
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def validate(root: Path) -> dict:
    identity_one = _load(root / "identity_1/faculty_identity_audit.json")
    identity_two = _load(root / "identity_2/faculty_identity_audit.json")
    appointment_one = _load(root / "appointments_1/faculty_appointment_audit.json")
    appointment_two = _load(root / "appointments_2/faculty_appointment_audit.json")
    metric = _load(root / "metric_readiness/metric_readiness_audit.json")
    roster = _load(root / "roster_readiness/faculty_roster_readiness.json")

    if identity_one["deterministic_fingerprint"] != identity_two["deterministic_fingerprint"]:
        raise ValueError("identity audit fingerprints differ")
    if appointment_one["deterministic_fingerprint"] != appointment_two["deterministic_fingerprint"]:
        raise ValueError("appointment audit fingerprints differ")
    for relative in (
        "faculty_identity_audit.json", "faculty_identities.jsonl",
    ):
        if (root / "identity_1" / relative).read_bytes() != (root / "identity_2" / relative).read_bytes():
            raise ValueError(f"repeated identity output differs: {relative}")
    for relative in (
        "faculty_appointment_audit.json",
        "faculty_appointment_observations.jsonl",
        "administrative_appointment_observations.jsonl",
        "employment_status_observations.jsonl",
        "identity_review_queue.jsonl",
    ):
        if (root / "appointments_1" / relative).read_bytes() != (root / "appointments_2" / relative).read_bytes():
            raise ValueError(f"repeated appointment output differs: {relative}")

    identity_summary = identity_one["summary"]
    appointment_summary = appointment_one["summary"]
    expected = {
        "ambiguous_identity_count": (identity_summary, 0),
        "duplicate_identity_id_count": (identity_summary, 0),
        "identity_link_coverage_percent": (appointment_summary, 100.0),
        "identity_unlinked_observation_count": (appointment_summary, 0),
        "ambiguous_or_unlinked_record_count": (appointment_summary, 0),
    }
    for field, (values, wanted) in expected.items():
        if values.get(field) != wanted:
            raise ValueError(f"{field} expected {wanted!r}; found {values.get(field)!r}")

    identities = {
        value["identity_id"]: value
        for value in _jsonl(root / "identity_1/faculty_identities.jsonl")
    }
    registry_path = Path(__file__).resolve().parents[2] / "config/faculty_identity_aliases.yaml"
    registry_payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    registry = {
        str(value["identity_key"]): value
        for value in registry_payload.get("identities") or ()
    }
    governed = {}
    for identity_id, required_names in GOVERNED_IDENTITIES.items():
        identity_key = identity_id.removeprefix("faculty_identity:")
        governed_record = registry.get(identity_key)
        if not governed_record:
            raise ValueError(f"missing governed registry record: {identity_key}")
        configured_names = set(governed_record.get("observed_names") or ())
        missing_configured = required_names - configured_names
        if missing_configured:
            raise ValueError(
                f"{identity_key} missing governed aliases: {sorted(missing_configured)}"
            )
        identity = identities.get(identity_id)
        if not identity:
            raise ValueError(f"missing governed identity: {identity_id}")
        if identity["ambiguous"]:
            raise ValueError(f"governed identity remains ambiguous: {identity_id}")
        observed_governed_names = required_names.intersection(identity["observed_names"])
        if not observed_governed_names:
            raise ValueError(f"{identity_id} has no governed name in production evidence")
        if identity["display_name"] != governed_record["canonical_display_name"]:
            raise ValueError(f"{identity_id} canonical display name differs from governance")
        governed[identity_id] = {
            "observation_count": len(identity["source_observations"]),
            "observed_governed_names": sorted(observed_governed_names),
            "configured_governed_names": sorted(configured_names),
        }

    unresolved = metric["audit"]["institutional_units"]["unresolved_published_unit_labels"]
    if unresolved:
        raise ValueError("institutional unresolved labels remain")
    if roster["authoritative_roster_present"] is not False:
        raise ValueError("authoritative_roster_present must remain false")
    if roster["production_denominator_ready"] is not False:
        raise ValueError("production_denominator_ready must remain false")

    return {
        "status": "passed",
        "identity_fingerprint": identity_one["deterministic_fingerprint"],
        "appointment_fingerprint": appointment_one["deterministic_fingerprint"],
        "ambiguous_identity_count": identity_summary["ambiguous_identity_count"],
        "duplicate_identity_id_count": identity_summary["duplicate_identity_id_count"],
        "appointment_identity_link_coverage_percent": appointment_summary["identity_link_coverage_percent"],
        "appointment_identity_unlinked_observation_count": appointment_summary["identity_unlinked_observation_count"],
        "appointment_ambiguous_or_unlinked_record_count": appointment_summary["ambiguous_or_unlinked_record_count"],
        "institutional_unresolved_label_count": len(unresolved),
        "authoritative_roster_present": roster["authoritative_roster_present"],
        "production_denominator_ready": roster["production_denominator_ready"],
        "governed_identity_observation_counts": governed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    summary = validate(args.run_root)
    (args.run_root / "production_validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = ["# Faculty Identity Governance Precedence Validation", ""] + [
        f"- {key}: {value}" for key, value in summary.items()
        if key != "governed_identity_observation_counts"
    ]
    (args.run_root / "production_validation_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
