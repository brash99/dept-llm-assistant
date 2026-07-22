#!/usr/bin/env python3
"""Validate and ingest an authoritative faculty-roster CSV contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.adapters.faculty_roster_adapter import FacultyRosterCSVAdapter  # noqa: E402
from app.authoritative_faculty_roster import FacultyRosterSchema, denominator_readiness  # noqa: E402
from app.metric_readiness_audit import load_normalized_objects  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--schema", type=Path, default=Path("config/faculty_roster_schema.yaml"))
    parser.add_argument("--source-authority")
    parser.add_argument("--effective-date")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--identity-root", type=Path, default=Path("storage/normalized"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def run(args):
    identities, integrity = load_normalized_objects(args.identity_root)
    if integrity["invalid_json_count"]:
        raise ValueError("Identity root contains invalid JSON")
    schema = FacultyRosterSchema.load(args.schema)
    return FacultyRosterCSVAdapter(
        args.input, schema, source_authority=args.source_authority,
        effective_date=args.effective_date, identity_objects=identities,
    ).adapt()


def write_result(result, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    payload["denominator_readiness"] = denominator_readiness(result.summary)
    (output_dir / "faculty_roster_ingestion.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output_dir / "faculty_roster_observations.jsonl").open("w", encoding="utf-8") as handle:
        for observation in result.observations:
            handle.write(json.dumps(observation.to_dict(), sort_keys=True) + "\n")
    with (output_dir / "faculty_roster_row_manifest.jsonl").open("w", encoding="utf-8") as handle:
        for row in result.rows:
            handle.write(json.dumps(row.to_dict(), sort_keys=True) + "\n")
    (output_dir / "faculty_roster_ingestion.md").write_text(_markdown(payload), encoding="utf-8")


def _markdown(payload):
    summary = payload["summary"]
    lines = [
        "# Authoritative Faculty Roster Ingestion", "",
        f"- Fingerprint: `{payload['deterministic_fingerprint']}`",
        f"- Accepted: {summary['accepted_row_count']}",
        f"- Accepted with limitations: {summary['accepted_with_limitations_row_count']}",
        f"- Quarantined: {summary['quarantined_row_count']}",
        f"- Rejected: {summary['rejected_row_count']}",
        f"- Identity-link coverage: {summary['identity_link_coverage_percent']}%", "",
        "No active population, tenure, faculty home, missing FTE, denominator, or SCH was inferred.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    args = parse_args(argv)
    result = run(args)
    if not args.dry_run:
        write_result(result, args.output_dir)
    print(json.dumps({
        "dry_run": args.dry_run,
        "deterministic_fingerprint": result.deterministic_fingerprint,
        **result.summary,
        "output_dir": None if args.dry_run else str(args.output_dir),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
