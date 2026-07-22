#!/usr/bin/env python3
"""Report readiness without calculating any faculty denominator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.authoritative_faculty_roster import denominator_readiness  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ingestion-report", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def audit(report: Path | None) -> dict:
    present = bool(report and report.is_file())
    ingestion = json.loads(report.read_text(encoding="utf-8")) if present else None
    summary = ingestion["summary"] if ingestion else {"accepted_observation_count": 0}
    readiness = denominator_readiness(summary)
    return {
        "authoritative_roster_present": present,
        "production_denominator_ready": bool(present) and all(
            value["status"] == "supported_by_explicit_evidence"
            for value in readiness.values()
        ),
        "ingestion_fingerprint": ingestion.get("deterministic_fingerprint") if ingestion else None,
        "summary": summary,
        "denominator_readiness": readiness,
    }


def main(argv=None) -> int:
    args = parse_args(argv)
    payload = audit(args.ingestion_report)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "faculty_roster_readiness.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Faculty Roster Readiness", "",
        f"- Authoritative roster present: {str(payload['authoritative_roster_present']).lower()}",
        f"- Production denominator ready: {str(payload['production_denominator_ready']).lower()}", "",
        "| Future denominator | Status |", "|---|---|",
    ] + [f"| {name} | {value['status']} |" for name, value in payload["denominator_readiness"].items()]
    (args.output_dir / "faculty_roster_readiness.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
