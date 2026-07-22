#!/usr/bin/env python3
"""Run deterministic Reasoning Layer analysis over schedule observations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_config
from app.reasoning import (
    ReasoningRouter,
    ScheduleAnalysisMetric,
    ScheduleAnalysisService,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute deterministic counts directly from normalized schedule "
            "Knowledge Objects; no vector retrieval or LLM is used."
        )
    )
    parser.add_argument("request", help="Natural-language analytical request.")
    parser.add_argument(
        "--metric",
        choices=[item.value for item in ScheduleAnalysisMetric],
        help="Override deterministic metric selection from the request.",
    )
    parser.add_argument(
        "--schedule-root",
        type=Path,
        help="Schedule Knowledge Object root (defaults to configured normalized root).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/settings.yaml"),
        help="Settings YAML (default: config/settings.yaml).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    return parser.parse_args()


def _configured_schedule_root(config_path: Path) -> Path:
    config = load_config(config_path)
    configured = Path(config["schedule_ingestion"]["normalized_output"])
    if configured.is_absolute():
        return configured
    return PROJECT_ROOT / configured


def main() -> int:
    args = parse_args()
    route = ReasoningRouter().route(args.request)
    if route.execution_service != "schedule_analysis":
        print(
            f"Request routes to {route.execution_service}, not schedule_analysis "
            f"({route.query_type.value}).",
            file=sys.stderr,
        )
        return 2
    root = args.schedule_root or _configured_schedule_root(args.config)
    result = ScheduleAnalysisService(root).analyze(args.request, metric=args.metric)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0

    print(f"Metric: {result.metric}")
    print(f"Source objects: {result.source_object_count}")
    print(f"Included objects: {result.included_object_count}")
    print(f"Excluded objects: {result.excluded_object_count}")
    print("Totals:")
    for category, value in result.totals.items():
        print(f"  {category}: {value}")
    print("By term and Instructor Type:")
    for group in result.grouped_results:
        print(f"  {group.academic_term} | {group.instructor_type}: {group.value}")
    print(f"Fingerprint: {result.deterministic_result_fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
