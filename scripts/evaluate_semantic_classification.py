#!/usr/bin/env python3
"""Evaluate semantic classification against a small reviewed fixture suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.classification.evaluation import (
    ClassificationEvaluationService,
    QualityGates,
    load_evaluation_cases,
)
from app.classification.policy import AuditPolicy


DEFAULT_CASES = Path("config/classification_evaluation_cases.yaml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument(
        "--json-output",
        nargs="?",
        const="-",
        metavar="PATH",
        help="Write machine-readable JSON to PATH, or stdout when omitted.",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--seed", default="iso-classification-audit-v1")
    parser.set_defaults(fail_on_forbidden=True)
    parser.add_argument(
        "--fail-on-forbidden",
        dest="fail_on_forbidden",
        action="store_true",
        help="Fail when a case emits an explicitly forbidden assertion (default).",
    )
    parser.add_argument(
        "--allow-forbidden",
        dest="fail_on_forbidden",
        action="store_false",
        help="Report forbidden assertions without making them a quality-gate failure.",
    )
    parser.add_argument("--minimum-precision", type=float, default=1.0)
    parser.add_argument("--minimum-coverage", type=float)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    cases = load_evaluation_cases(args.cases)
    service = ClassificationEvaluationService(
        audit_policy=AuditPolicy(seed=args.seed)
    )
    report = service.evaluate(
        cases,
        quality_gates=QualityGates(
            fail_on_forbidden=args.fail_on_forbidden,
            minimum_precision=args.minimum_precision,
            minimum_coverage=args.minimum_coverage,
        ),
    )
    if args.json_output:
        rendered = json.dumps(report.to_dict(), indent=2, sort_keys=True)
        if args.json_output == "-":
            print(rendered)
        else:
            Path(args.json_output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(report.to_text(verbose=args.verbose))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
