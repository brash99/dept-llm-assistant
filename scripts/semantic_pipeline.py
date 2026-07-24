#!/usr/bin/env python3
"""Inspect, safely rebuild, and verify ISO derived semantic artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.semantic_pipeline import SemanticPipelineService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Operate the configured normalized Knowledge Object -> chunks -> "
            "embeddings -> FAISS pipeline without changing source evidence."
        )
    )
    parser.add_argument(
        "--config", type=Path, default=Path("config/settings.yaml"),
        help="Settings YAML (default: config/settings.yaml).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Inspect artifact presence, consistency, and freshness.")
    status.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    rebuild = subparsers.add_parser("rebuild", help="Stage, verify, back up, and promote all derived stages.")
    rebuild.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    rebuild.add_argument("--dry-run", action="store_true", help="Run preflight only; make no filesystem changes.")
    rebuild.add_argument("--device", help="Override the configured embedding device for this build.")
    rebuild.add_argument(
        "--embedding-context", choices=("none", "title", "title_path", "metadata"),
        default="title_path", help="Context prepended by the existing embedding builder.",
    )
    rebuild.add_argument(
        "--cleanup-staging", action="store_true",
        help="Explicitly remove incomplete marked staging runs before rebuilding.",
    )

    verify = subparsers.add_parser("verify", help="Perform full structural and semantic propagation checks.")
    verify.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        service = SemanticPipelineService(args.config)
        if args.command == "status":
            payload = service.status().to_dict()
        elif args.command == "rebuild":
            payload = service.rebuild(
                dry_run=args.dry_run, device=args.device,
                embedding_context=args.embedding_context,
                cleanup_staging=args.cleanup_staging,
            )
        else:
            report = service.verify()
            payload = report.to_dict()
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                _print_verify(payload)
            return 0 if report.valid else 1
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, indent=2))
        else:
            print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "status":
        _print_status(payload)
    else:
        _print_rebuild(payload)
    return 0


def _print_status(payload):
    print("ISO Semantic Pipeline Status")
    for name in ("normalized", "chunks", "embeddings", "vector_index"):
        stage = payload[name]
        print(f"{name.replace('_', ' ').title()}: {stage['state']}")
        for reason in stage["reasons"]:
            print(f"  - {reason}")
        for key, value in stage["details"].items():
            if value is not None:
                print(f"  {key}: {value}")
    print("Paths:")
    for key, value in payload["paths"].items():
        print(f"  {key}: {value}")
    if payload["incomplete_staging_runs"]:
        print("Incomplete staging runs: " + ", ".join(payload["incomplete_staging_runs"]))
    for warning in payload["warnings"]:
        print(f"WARNING: {warning}")


def _print_rebuild(payload):
    if payload["mode"] == "dry_run":
        print("ISO Semantic Pipeline Rebuild — DRY RUN")
        print(f"Normalized objects: {payload['normalized_object_count']}")
        print(f"Embedding model: {payload['embedding_model']}")
        print(f"Embedding device: {payload['embedding_device']}")
        print(f"GPU expected: {payload['gpu_expected']}")
        print(f"Free disk bytes: {payload['free_disk_bytes']}")
        print("Stages: " + " -> ".join(payload["planned_stages"]))
        print("Would replace: " + (", ".join(payload["would_replace"]) or "nothing currently present"))
        print("Dependencies: " + ", ".join(f"{k}={'available' if v else 'MISSING'}" for k, v in payload["dependencies"].items()))
        for conflict in payload["configuration_conflicts"]:
            print(f"CONFLICT: {conflict}")
        print("Filesystem mutations: none")
    else:
        print("ISO Semantic Pipeline Rebuild complete")
        print(f"Run ID: {payload['run_id']}")
        print(f"Manifest: {payload['manifest']}")
        for name, path in payload["backup_paths"].items():
            print(f"Backup {name}: {path}")


def _print_verify(payload):
    print("ISO Semantic Pipeline Verification")
    print(f"Valid: {payload['valid']}")
    for key in (
        "normalized_object_count", "chunk_file_count", "chunk_count",
        "embedding_file_count", "embedding_count", "embedding_dimension",
        "embedding_model", "vector_count", "metadata_record_count",
        "vector_smoke_queries",
    ):
        print(f"{key.replace('_', ' ').title()}: {payload[key]}")
    for error in payload["errors"]:
        print(f"ERROR: {error}")
    for warning in payload["warnings"]:
        print(f"WARNING: {warning}")
    for family, result in payload["family_checks"].items():
        print(f"Semantic propagation {family}: {'PASS' if result['valid'] else 'FAIL'}")


if __name__ == "__main__":
    raise SystemExit(main())
