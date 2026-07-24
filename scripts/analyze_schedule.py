#!/usr/bin/env python3
"""Run deterministic Reasoning Layer analysis over schedule observations."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.academic_terms import academic_term_order, academic_term_sort_key
from app.config import load_config
from app.reasoning import ReasoningRouter, ScheduleAnalysisMetric, ScheduleAnalysisService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute governed schedule analytics without vector retrieval or an LLM."
    )
    parser.add_argument("request", help="Natural-language analytical request.")
    parser.add_argument("--metric", choices=[item.value for item in ScheduleAnalysisMetric])
    parser.add_argument(
        "--group-by", nargs="+",
        choices=["subject", "academic_unit", "academic_term", "normalized_instructor_type"],
        help="Approved grouping dimensions in the requested order.",
    )
    parser.add_argument("--trend", action="store_true", help="Compute endpoint trend changes.")
    parser.add_argument("--subject", action="append", default=[], help="Include one subject code; repeatable.")
    parser.add_argument("--academic-unit", action="append", default=[], help="Include one governed unit ID/name; repeatable.")
    parser.add_argument("--term", action="append", default=[], help="Include one normalized term; repeatable.")
    parser.add_argument("--term-from", help="Inclusive normalized starting term.")
    parser.add_argument("--term-to", help="Inclusive normalized ending term.")
    parser.add_argument("--schedule-root", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/settings.yaml"))
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="Emit JSON.")
    output.add_argument("--csv", action="store_true", help="Emit grouped/trend rows as CSV.")
    parser.add_argument("--diagnostics", action="store_true", help="Print compact coverage diagnostics to stderr.")
    return parser.parse_args()


def _configured_schedule_root(config_path: Path) -> Path:
    configured = Path(load_config(config_path)["schedule_ingestion"]["normalized_output"])
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


def _term_filter(observations, args) -> tuple[str, ...]:
    explicit = set(args.term)
    if not args.term_from and not args.term_to:
        return tuple(sorted(explicit, key=academic_term_sort_key))
    terms = {str(getattr(item, "academic_term", "") or "") for item in observations}
    lower = academic_term_sort_key(args.term_from) if args.term_from else None
    upper = academic_term_sort_key(args.term_to) if args.term_to else None
    for term in terms:
        if not academic_term_order(term).supported:
            continue
        key = academic_term_sort_key(term)
        if (lower is None or key >= lower) and (upper is None or key <= upper):
            explicit.add(term)
    return tuple(sorted(explicit, key=academic_term_sort_key))


def _print_csv(result) -> None:
    rows = result.trends if hasattr(result, "trends") else result.grouped_results
    dictionaries = [row.to_dict() for row in rows]
    if not dictionaries:
        return
    writer = csv.DictWriter(sys.stdout, fieldnames=list(dictionaries[0]))
    writer.writeheader()
    writer.writerows(dictionaries)


def _print_table(result) -> None:
    if hasattr(result, "trends"):
        print(f"Deterministic schedule trend analysis | metric={result.metric}")
        for row in result.trends:
            label = row.subject or row.academic_unit_name or "All observations"
            change = row.percentage_point_change if row.percentage_point_change is not None else row.absolute_change
            print(f"{label} | {row.first_term}: {row.first_value} | {row.last_term}: {row.last_value} | change: {change}")
        print(f"Fingerprint: {result.deterministic_result_fingerprint}")
        return
    print(f"Deterministic schedule analysis | metric={result.metric}")
    for row in result.grouped_results:
        labels = [row.subject, row.academic_unit_name, row.academic_term, row.instructor_type]
        label = " | ".join(value for value in labels if value) or "All observations"
        denominator = f" ({row.numerator}/{row.denominator})" if row.denominator is not None else ""
        print(f"{label}: {row.value}{denominator}")
    print(f"Source objects: {result.source_object_count}; included: {result.included_object_count}; excluded: {result.excluded_object_count}")
    print(f"Fingerprint: {result.deterministic_result_fingerprint}")


def main() -> int:
    args = parse_args()
    route = ReasoningRouter().route(args.request)
    if route.execution_service != "schedule_analysis":
        print(
            f"Unsupported analytical execution: route={route.execution_service}; type={route.query_type.value}. "
            "ISO will not substitute a top-k retrieval answer.", file=sys.stderr,
        )
        return 2
    service = ScheduleAnalysisService(args.schedule_root or _configured_schedule_root(args.config))
    observations = service.load_observations()
    filters = {
        "subject_filter": tuple(args.subject),
        "academic_unit_filter": tuple(args.academic_unit),
        "term_filter": _term_filter(observations, args),
    }
    if args.trend:
        if not args.metric:
            parser_message = "--trend requires --metric for an auditable production command"
            print(parser_message, file=sys.stderr); return 2
        result = service.analyze_trend(
            args.request, observations=observations, metric=args.metric,
            group_by=tuple(args.group_by or ("subject",)), **filters,
        )
        fitness = result.source_aggregation.evidence_fitness
    else:
        result = service.analyze_observations(
            args.request, observations, metric=args.metric,
            group_by=tuple(args.group_by) if args.group_by else None, **filters,
        )
        fitness = result.evidence_fitness
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    elif args.csv:
        _print_csv(result)
    else:
        _print_table(result)
    if args.diagnostics and fitness:
        print(
            f"coverage: total={fitness.total_schedule_observations} "
            f"resolved={fitness.observations_with_resolved_instructor_type} "
            f"mapped={fitness.mapped_observations} "
            f"unmapped={fitness.unmapped_observations} ambiguous={fitness.ambiguous_mappings}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
