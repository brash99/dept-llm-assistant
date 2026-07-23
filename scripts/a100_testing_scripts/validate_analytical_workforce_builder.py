#!/usr/bin/env python3
"""Validate production analytical-workforce artifacts and invariants."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl(path):
    return tuple(json.loads(line) for line in path.read_text().splitlines() if line.strip())


def validate(root):
    first = load(root / "workforce_1/analytical_workforce_population.json")
    second = load(root / "workforce_2/analytical_workforce_population.json")
    if first["deterministic_fingerprint"] != second["deterministic_fingerprint"]:
        raise ValueError("workforce fingerprints differ")
    for path in (root / "workforce_1").iterdir():
        other = root / "workforce_2" / path.name
        if not other.exists() or path.read_bytes() != other.read_bytes():
            raise ValueError(f"workforce output differs: {path.name}")
    decisions = jsonl(root / "workforce_1/analytical_workforce_decisions.jsonl")
    ids = [item["decision_id"] for item in decisions]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate decision IDs")
    if len(decisions) != first["starting_directory_identity_count"]:
        raise ValueError("missing starting identity decisions")
    if first["included_count"] + first["excluded_count"] + first["review_required_count"] != first["starting_directory_identity_count"]:
        raise ValueError("population arithmetic does not reconcile")
    if first["minimum_plausible_population"] != first["included_count"]:
        raise ValueError("minimum population invariant failed")
    if first["maximum_plausible_population"] != first["included_count"] + first["review_required_count"]:
        raise ValueError("maximum population invariant failed")

    identity = load(root / "identity/faculty_identity_audit.json")
    identity_manifest = jsonl(root / "identity/faculty_identities.jsonl")
    directory_dates = sorted({
        source.get("temporal_label")
        for item in identity_manifest for source in item["source_observations"]
        if source.get("source_system") == "faculty_directory"
        and source.get("temporal_label")
    })
    if not directory_dates:
        raise ValueError("production identity audit has no directory snapshot")
    latest_directory_date = directory_dates[-1]
    expected_starting_identities = {
        item["identity_id"] for item in identity_manifest
        if any(
            source.get("source_system") == "faculty_directory"
            and source.get("temporal_label") == latest_directory_date
            for source in item["source_observations"]
        )
    }
    decided_identities = {item["faculty_identity_id"] for item in decisions}
    if decided_identities != expected_starting_identities:
        raise ValueError("workforce decisions do not match latest directory identities")
    appointment = load(root / "appointments/faculty_appointment_audit.json")
    metric = load(root / "metric_readiness/metric_readiness_audit.json")
    roster = load(root / "roster_readiness/faculty_roster_readiness.json")
    if identity["summary"]["ambiguous_identity_count"] != 0:
        raise ValueError("ambiguous faculty identities remain")
    if identity["summary"]["duplicate_identity_id_count"] != 0:
        raise ValueError("duplicate faculty identity IDs remain")
    if appointment["summary"]["identity_link_coverage_percent"] != 100.0:
        raise ValueError("appointment identity coverage is not 100%")
    if appointment["summary"]["identity_unlinked_observation_count"] != 0:
        raise ValueError("unlinked appointment observations remain")
    if appointment["summary"]["ambiguous_or_unlinked_record_count"] != 0:
        raise ValueError("ambiguous appointment observations remain")
    labels = metric["audit"]["institutional_units"]["unresolved_published_unit_labels"]
    blocking = [item for item in labels if item.get("classification") != "ambiguous"]
    if blocking:
        raise ValueError("genuinely unresolved institutional labels remain")
    if roster["authoritative_roster_present"] is not False or roster["production_denominator_ready"] is not False:
        raise ValueError("authoritative-roster readiness assertions changed")
    summary = {
        "status": "passed",
        "fingerprint": first["deterministic_fingerprint"],
        "starting_population": first["starting_directory_identity_count"],
        "included": first["included_count"], "excluded": first["excluded_count"],
        "review_required": first["review_required_count"],
        "minimum_plausible_population": first["minimum_plausible_population"],
        "maximum_plausible_population": first["maximum_plausible_population"],
        "distance_from_275": first["distance_from_275"],
        "unit_resolution_percent": first["evidence_coverage"]["analytical_unit_resolution_percent"],
        "top_exclusion_reasons": Counter(item["primary_reason_code"] for item in decisions if item["decision"] == "exclude").most_common(10),
        "top_review_reasons": Counter(item["primary_reason_code"] for item in decisions if item["decision"] == "review_required").most_common(10),
        "known_ambiguous_historical_unit_label_count": len(labels),
        "authoritative_roster_present": False,
        "production_denominator_ready": False,
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    summary = validate(args.run_root)
    (args.run_root / "production_validation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (args.run_root / "production_validation_summary.md").write_text("# Analytical Workforce Builder Validation\n\n" + "\n".join(f"- {key}: {value}" for key, value in summary.items()) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
