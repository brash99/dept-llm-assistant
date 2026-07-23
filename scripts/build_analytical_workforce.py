#!/usr/bin/env python3
"""Build a governed analytical workforce population from normalized evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytical_workforce import (  # noqa: E402
    AnalyticalWorkforceBuilder, AnalyticalWorkforcePolicy, load_overrides,
)
from app.metric_readiness_audit import load_normalized_objects  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-root", type=Path, default=Path("storage/normalized"))
    parser.add_argument("--policy", type=Path, default=Path("config/analytical_workforce_policy.yaml"))
    parser.add_argument("--overrides", type=Path, default=Path("config/analytical_workforce_overrides.yaml"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    objects, integrity = load_normalized_objects(args.normalized_root)
    if integrity["invalid_json_count"]:
        raise ValueError("Normalized corpus contains invalid JSON")
    policy = AnalyticalWorkforcePolicy.load(args.policy)
    decisions, population = AnalyticalWorkforceBuilder(
        policy, load_overrides(args.overrides)
    ).build(objects)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = population.to_dict()
    payload["target_reference_population"] = policy.target_reference_population
    payload["distance_from_275"] = {
        "minimum": population.minimum_plausible_population - policy.target_reference_population,
        "maximum": population.maximum_plausible_population - policy.target_reference_population,
    }
    _write_json(args.output_dir / "analytical_workforce_population.json", payload)
    _write_json(args.output_dir / "analytical_workforce_unit_summary.json", population.counts_by_academic_unit)
    evidence = {
        "integrity": integrity, "evidence_coverage": population.evidence_coverage,
        "policy_sensitivity": population.policy_sensitivity,
        "source_capabilities": {
            "faculty_directory": {
                "current_presence": "explicit",
                "published_title": "explicit",
                "published_academic_unit": "explicit",
                "full_time_instructional_status": "supporting_but_not_conclusive",
            },
            "appointment_observations": {
                "faculty_and_administrative_titles": "explicit",
                "authoritative_current_employment": "absent",
            },
            "employment_status_observations": {
                "published_status_phrases": "explicit",
                "status_when_not_published": "unsafe_to_infer",
            },
            "schedule": {
                "teaching_activity": "explicit",
                "faculty_appointment_or_full_time_status": "unsafe_to_infer",
            },
            "catalog_and_department_rosters": {
                "historical_edition_presence": "explicit",
                "current_status": "unsafe_to_infer",
            },
        },
        "limitations": [
            "analytical population is not an authoritative HR roster",
            "full-time status is a governed proxy, not an authoritative assertion",
            "teaching absence is not an exclusion rule",
            "appointment FTE is not inferred",
        ],
    }
    _write_json(args.output_dir / "analytical_workforce_evidence_audit.json", evidence)
    _write_jsonl(args.output_dir / "analytical_workforce_decisions.jsonl", decisions)
    _write_jsonl(args.output_dir / "analytical_workforce_included.jsonl", [item for item in decisions if item.decision == "include"])
    _write_jsonl(args.output_dir / "analytical_workforce_excluded.jsonl", [item for item in decisions if item.decision == "exclude"])
    _write_jsonl(args.output_dir / "analytical_workforce_review_queue.jsonl", [item for item in decisions if item.decision == "review_required"])
    (args.output_dir / "analytical_workforce_population.md").write_text(
        _markdown(payload), encoding="utf-8"
    )
    print(json.dumps({
        "fingerprint": population.deterministic_fingerprint,
        "starting_population": population.starting_directory_identity_count,
        "included": population.included_count,
        "excluded": population.excluded_count,
        "review_required": population.review_required_count,
        "minimum_plausible_population": population.minimum_plausible_population,
        "maximum_plausible_population": population.maximum_plausible_population,
        "distance_from_275": payload["distance_from_275"],
        "unit_resolution_percent": population.evidence_coverage["analytical_unit_resolution_percent"],
        "output_dir": str(args.output_dir),
    }, indent=2, sort_keys=True))
    return 0


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path, values):
    with path.open("w", encoding="utf-8") as handle:
        for value in values:
            handle.write(json.dumps(value.to_dict(), sort_keys=True) + "\n")


def _markdown(value):
    lines = [
        "# Analytical Workforce Population", "",
        "> Governed analytical proxy; not an authoritative HR roster.", "",
        f"- As of directory snapshot: {value['as_of_date']}",
        f"- Starting directory identities: {value['starting_directory_identity_count']}",
        f"- Included: {value['included_count']}",
        f"- Excluded: {value['excluded_count']}",
        f"- Review required: {value['review_required_count']}",
        f"- Minimum plausible population: {value['minimum_plausible_population']}",
        f"- Maximum plausible population: {value['maximum_plausible_population']}",
        f"- Distance from 275: {value['distance_from_275']}",
        f"- Unit resolution: {value['evidence_coverage']['analytical_unit_resolution_percent']}%", "",
        "## Primary reasons", "", "| Reason | Count |", "|---|---:|",
    ]
    lines.extend(f"| {reason} | {count} |" for reason, count in value["counts_by_reason"].items())
    lines += ["", "## Policy sensitivity", "", "| Choice | Affected identities |", "|---|---:|"]
    lines.extend(f"| {name} | {count} |" for name, count in value["policy_sensitivity"].items())
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
