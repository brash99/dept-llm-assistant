#!/usr/bin/env python3
"""Build and inspect canonical Department Contribution Knowledge Objects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.contribution_inspection import ContributionOntologyInspector  # noqa: E402
from app.contribution_ontology import (  # noqa: E402
    ContributionPeriod,
    ContributionTemporalScope,
)
from app.department_contributions import DepartmentContributionBuilder  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--instructional-attribution", type=Path)
    parser.add_argument("--llc-attribution", type=Path)
    parser.add_argument("--unit-id", action="append", dest="unit_ids")
    parser.add_argument("--reporting-label", required=True)
    parser.add_argument("--reporting-start")
    parser.add_argument("--reporting-end")
    parser.add_argument("--observation-start")
    parser.add_argument("--observation-end")
    parser.add_argument("--publication-time", required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--omit-canonical-json",
        action="store_true",
        help="Omit canonical JSON from the human-readable stdout rendering.",
    )
    args = parser.parse_args(argv)

    profiles = _jsonl(args.profiles)
    if args.unit_ids:
        wanted = set(args.unit_ids)
        profiles = tuple(
            item for item in profiles if item["academic_unit_id"] in wanted
        )
        missing = wanted - {item["academic_unit_id"] for item in profiles}
        if missing:
            raise ValueError(f"Requested departments lack profiles: {sorted(missing)}")
    scope = ContributionTemporalScope(
        reporting_period=ContributionPeriod(
            start=args.reporting_start,
            end=args.reporting_end,
            label=args.reporting_label,
        ),
        observation_period=(
            ContributionPeriod(
                start=args.observation_start,
                end=args.observation_end,
            )
            if args.observation_start or args.observation_end
            else None
        ),
        publication_time=args.publication_time,
    )
    objects = DepartmentContributionBuilder().build(
        profiles,
        temporal_scope=scope,
        instructional_attribution=(
            _json(args.instructional_attribution)
            if args.instructional_attribution else None
        ),
        llc_attribution=(
            _json(args.llc_attribution) if args.llc_attribution else None
        ),
    )
    inspector = ContributionOntologyInspector()
    for value in objects:
        sys.stdout.write(
            inspector.render(
                value,
                include_canonical_json=not args.omit_canonical_json,
            )
        )
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for value in objects:
            stem = value.entity.entity_id.replace(":", "__")
            (args.output_dir / f"{stem}.json").write_text(
                value.to_json() + "\n", encoding="utf-8"
            )
            (args.output_dir / f"{stem}.ontology.txt").write_text(
                inspector.render(value, include_canonical_json=True),
                encoding="utf-8",
            )
        (args.output_dir / "structural_signatures.json").write_text(
            json.dumps(
                inspector.compare_structure(objects),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return 0


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path):
    return tuple(
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


if __name__ == "__main__":
    raise SystemExit(main())
