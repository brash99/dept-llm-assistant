#!/usr/bin/env python3
"""Build a deterministic, appointment-neutral faculty identity audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.faculty_identity import FacultyIdentityService  # noqa: E402
from app.metric_readiness_audit import load_normalized_objects  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--normalized-root", type=Path, default=Path("storage/normalized")
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _markdown(payload: dict) -> str:
    summary = payload["summary"]
    schema = payload["observation_schema_audit"]
    lines = [
        "# Faculty Identity Audit",
        "",
        "> Identity is not appointment, employment status, faculty home, or teaching assignment.",
        "",
        f"- Deterministic fingerprint: `{payload['deterministic_fingerprint']}`",
        f"- Candidate source objects: {summary['candidate_object_count']}",
        f"- Identity-bearing observations: {summary['identity_bearing_observation_count']}",
        f"- Faculty identities: {summary['identity_count']}",
        f"- Multi-observation identities: {summary['multi_observation_identity_count']}",
        f"- Single-observation identities: {summary['single_observation_identity_count']}",
        f"- Ambiguous identities: {summary['ambiguous_identity_count']}",
        f"- Duplicate identity IDs: {summary['duplicate_identity_id_count']}",
        "",
        "## Source-system coverage",
        "",
        "| Source | Observations |",
        "|---|---:|",
    ]
    for source, count in summary["source_system_coverage"].items():
        lines.append(f"| {source} | {count} |")
    lines += [
        "",
        "## Largest identity clusters",
        "",
        "| Identity | Display name | Observations | Sources | Ambiguous |",
        "|---|---|---:|---|---|",
    ]
    for item in summary["largest_identity_clusters"]:
        lines.append(
            f"| `{item['identity_id']}` | {item['display_name']} | "
            f"{item['observation_count']} | {', '.join(item['source_systems'])} | "
            f"{item['ambiguous']} |"
        )
    lines += [
        "",
        "## Observation schema",
        "",
        f"- Candidate types: {', '.join(sorted(schema['candidate_object_counts_by_type']))}",
        f"- Missing or placeholder names excluded: "
        f"{schema['excluded_missing_or_placeholder_name_count']}",
        "",
        "The audit makes no appointment, employment, rank, tenure, FTE, academic-unit, "
        "or workload assertion.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    args = parse_args(argv)
    objects, integrity = load_normalized_objects(args.normalized_root)
    if integrity["invalid_json_count"]:
        print(json.dumps({
            "error": "invalid_normalized_json",
            "invalid_json_count": integrity["invalid_json_count"],
        }, sort_keys=True))
        return 2
    result = FacultyIdentityService().audit(objects)
    payload = result.summary_dict()
    payload["integrity"] = integrity
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "faculty_identity_audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "faculty_identity_audit.md").write_text(
        _markdown(payload), encoding="utf-8"
    )
    with (args.output_dir / "faculty_identities.jsonl").open("w", encoding="utf-8") as handle:
        for identity in result.identities:
            handle.write(json.dumps(identity.to_dict(), sort_keys=True) + "\n")
    compact = {
        "fingerprint": result.deterministic_fingerprint,
        **result.summary,
        "invalid_json": integrity["invalid_json_count"],
        "reports": str(args.output_dir),
    }
    print(json.dumps(payload if args.json else compact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
