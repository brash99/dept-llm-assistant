#!/usr/bin/env python3
"""Populate Knowledge Object Semantic Identity through governed classification."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.classification.corpus import (
    CorpusClassificationOptions,
    SemanticCorpusPopulationService,
)
from app.config import load_config


def _default_inputs() -> tuple[Path, ...]:
    config = load_config()
    configured_root = Path(config["project"]["root"])
    project_root = configured_root if configured_root.exists() else PROJECT_ROOT
    storage = config["storage"]
    keys = (
        "normalized",
        "constitutional",
        "schedule_observations",
        "faculty_observations",
        "catalog_observations",
    )
    return tuple(project_root / storage[key] for key in keys if storage.get(key))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        dest="inputs",
        action="append",
        type=Path,
        help="Knowledge Object file or directory; repeat to include multiple roots.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="apply",
        action="store_false",
        help="Classify and report without modifying Knowledge Objects (default).",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Atomically apply policy-approved assertions.",
    )
    parser.set_defaults(apply=False)
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("storage/reports/classification"),
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--object-type", action="append", default=[])
    parser.add_argument("--knowledge-object-id", action="append", default=[])
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be a positive integer")
    inputs = tuple(args.inputs) if args.inputs else _default_inputs()
    if not any(path.exists() for path in inputs):
        raise SystemExit(
            "No Knowledge Object input exists. Supply one or more --input paths."
        )
    options = CorpusClassificationOptions(
        input_roots=inputs,
        report_dir=args.report_dir,
        apply=args.apply,
        limit=args.limit,
        object_types=tuple(args.object_type),
        knowledge_object_ids=tuple(args.knowledge_object_id),
        resume=args.resume,
        verbose=args.verbose,
    )
    report = SemanticCorpusPopulationService().run(options)
    values = report.overall.to_dict()
    print("Semantic Corpus Population")
    print(f"Mode: {report.mode}")
    for name, value in values.items():
        print(f"{name.replace('_', ' ').title()}: {value}")
    print(f"Manifest: {report.manifest_path}")
    print(f"Summary: {args.report_dir / 'classification_summary.json'}")
    print(f"Report: {args.report_dir / 'classification_report.md'}")
    return 1 if values["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
