#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.acquisition.external import EvidenceAcquisitionPlanner, ExternalEvidenceAcquisitionService, ExternalSourceRegistry
from app.config import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan or execute curated external evidence acquisition.")
    parser.add_argument("--assessment-json", type=Path)
    parser.add_argument("--decision-type", default="academic_program")
    parser.add_argument("--decision-label", default="Academic Program Decision")
    parser.add_argument("--missing-domain", action="append", default=[])
    parser.add_argument("--registry", type=Path, default=Path("config/external_evidence_sources.yaml"))
    parser.add_argument("--execute", action="store_true", help="Retrieve, stage, validate, and promote the planned resources.")
    return parser.parse_args()


def load_assessment(args: argparse.Namespace):
    if args.assessment_json:
        payload = json.loads(args.assessment_json.read_text(encoding="utf-8"))
        return SimpleNamespace(
            decision_type=payload["decision_type"],
            decision_type_label=payload.get("decision_type_label", payload["decision_type"]),
            missing_topics=payload.get("missing_topics", []),
        )
    if not args.missing_domain:
        raise SystemExit("Provide --assessment-json or at least one --missing-domain.")
    return SimpleNamespace(
        decision_type=args.decision_type,
        decision_type_label=args.decision_label,
        missing_topics=args.missing_domain,
    )


def main() -> None:
    args = parse_args()
    assessment = load_assessment(args)
    registry = ExternalSourceRegistry.from_yaml(args.registry)
    planner = EvidenceAcquisitionPlanner(registry)
    plan = planner.plan(assessment)

    # The deterministic plan is always emitted before any optional retrieval.
    print(planner.render_dry_run(plan))

    if not args.execute:
        return

    config = load_config()
    project_root = Path(config["project"]["root"])
    storage = config["storage"]
    service = ExternalEvidenceAcquisitionService(
        registry=registry,
        staging_dir=project_root / storage.get("external_staging", "storage/external_staging"),
        normalized_dir=project_root / storage["normalized"],
    )
    outcome = service.acquire_validate_promote(plan)
    validations = outcome["validations"]
    print()
    print(f"Staged: {len(outcome['staged'])}")
    print(f"Validated: {sum(item.valid for item in validations)}")
    print(f"Promoted: {len(outcome['promoted'])}")
    for validation in validations:
        if not validation.valid:
            print(f"INVALID {validation.resource_id}: {'; '.join(validation.errors)}")


if __name__ == "__main__":
    main()
