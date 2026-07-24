#!/usr/bin/env python3
"""Validate overrides and rebuild analytical-workforce review artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytical_workforce import load_overrides  # noqa: E402
from scripts.a100_testing_scripts.build_analytical_workforce_review_matrix import (  # noqa: E402
    build_matrix, write_reports,
)
from scripts.build_analytical_workforce import main as build_workforce  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-root", type=Path, default=Path("storage/normalized"))
    parser.add_argument("--policy", type=Path, default=Path("config/analytical_workforce_policy.yaml"))
    parser.add_argument("--overrides", type=Path, default=Path("config/analytical_workforce_overrides.yaml"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    load_overrides(args.overrides)
    output = args.output_dir or Path("storage/logs") / (
        "analytical_workforce_override_application_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    workforce = output / "workforce_1"
    build_workforce([
        "--normalized-root", str(args.normalized_root),
        "--policy", str(args.policy),
        "--overrides", str(args.overrides),
        "--output-dir", str(workforce),
    ])
    payload = build_matrix(output)
    write_reports(payload, output / "review_matrix")
    population = payload
    print("\nInstitutional review status")
    print(f"Starting population: {population['starting_population']}")
    print(f"Included: {population['workforce_included']}")
    print(f"Excluded: {population['workforce_excluded']}")
    print(f"Workforce review remaining: {population['workforce_review_required']}")
    print(f"Department review remaining: {population['department_assignment_review_required']}")
    print(f"Reports: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
