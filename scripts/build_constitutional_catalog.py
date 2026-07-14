#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List

import yaml

from app.config import load_config
from app.constitution import (
    ConstitutionalObservationRequest,
    ConstitutionalObserver,
    ConstitutionalType,
)
from app.knowledge import (
    KnowledgeObject,
    load_knowledge_object,
    save_knowledge_object,
)


def load_registry(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Constitutional registry not found: {path}"
        )

    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    objects = payload.get("objects", [])

    if not isinstance(objects, list):
        raise ValueError(
            "'objects' must be a YAML list."
        )

    return payload


def iter_normalized_objects(
    normalized_dir: Path,
) -> Iterable[KnowledgeObject]:
    for path in sorted(normalized_dir.glob("*.json")):
        yield load_knowledge_object(path)


def index_normalized_objects(
    normalized_dir: Path,
) -> Dict[str, List[KnowledgeObject]]:
    by_relative_path: Dict[
        str,
        List[KnowledgeObject],
    ] = {}

    for obj in iter_normalized_objects(normalized_dir):
        relative_path = getattr(
            obj,
            "relative_path",
            "",
        )

        if not relative_path:
            relative_path = (
                obj.metadata.get(
                    "qualified_relative_path",
                    "",
                )
                if obj.metadata
                else ""
            )

        if relative_path:
            by_relative_path.setdefault(
                relative_path,
                [],
            ).append(obj)

    return by_relative_path


def resolve_source(
    *,
    record: dict,
    by_relative_path: Dict[
        str,
        List[KnowledgeObject],
    ],
) -> KnowledgeObject:
    source_cfg = record.get("source", {})
    relative_path = source_cfg.get(
        "relative_path"
    )

    if not relative_path:
        raise ValueError(
            f"Object {record.get('key')!r} "
            "does not define source.relative_path."
        )

    matches = by_relative_path.get(
        relative_path,
        [],
    )

    if not matches:
        raise FileNotFoundError(
            "No normalized Knowledge Object found for "
            f"{relative_path!r}. Acquire and normalize "
            "the configured source first."
        )

    if len(matches) > 1:
        raise RuntimeError(
            "Multiple normalized Knowledge Objects found "
            f"for {relative_path!r}."
        )

    return matches[0]


def output_path(
    *,
    record: dict,
    output_dir: Path,
) -> Path:
    key = record["key"]
    return output_dir / f"{key}.json"


def build_catalog(
    *,
    registry_path: Path,
    normalized_dir: Path,
    output_dir: Path,
    clear: bool = False,
) -> dict:
    registry = load_registry(registry_path)
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if clear:
        for path in output_dir.glob("*.json"):
            path.unlink()

    by_relative_path = index_normalized_objects(
        normalized_dir
    )

    observer = ConstitutionalObserver()

    results = {
        "attempted": 0,
        "created": 0,
        "unchanged": 0,
        "disabled": 0,
        "failed": 0,
        "outputs": [],
        "errors": [],
    }

    for record in registry.get("objects", []):
        if not record.get("enabled", True):
            results["disabled"] += 1
            continue

        results["attempted"] += 1

        try:
            source = resolve_source(
                record=record,
                by_relative_path=by_relative_path,
            )

            request = ConstitutionalObservationRequest(
                constitutional_type=ConstitutionalType(
                    record["constitutional_type"]
                ),
                principles=tuple(
                    record.get("principles", [])
                ),
                institutional_scope=tuple(
                    record.get(
                        "institutional_scope",
                        [],
                    )
                ),
                effective_from=record.get(
                    "effective_from"
                ),
                effective_until=record.get(
                    "effective_until"
                ),
                notes=record.get("notes"),
            )

            constitutional = observer.observe(
                source=source,
                request=request,
            )

            destination = output_path(
                record=record,
                output_dir=output_dir,
            )

            serialized = json.dumps(
                constitutional.to_dict(),
                indent=2,
                sort_keys=True,
            ) + "\n"

            if (
                destination.exists()
                and destination.read_text(
                    encoding="utf-8"
                )
                == serialized
            ):
                status = "unchanged"
                results["unchanged"] += 1
            else:
                save_knowledge_object(
                    constitutional,
                    destination,
                )
                status = "created"
                results["created"] += 1

            results["outputs"].append(
                str(destination)
            )

            print(
                f"[{status.upper():9}] "
                f"{record['key']:24} "
                f"{constitutional.constitutional_type}"
            )

        except Exception as error:
            results["failed"] += 1
            results["errors"].append(
                {
                    "key": record.get("key"),
                    "error": str(error),
                }
            )

            print(
                f"[FAIL] "
                f"{record.get('key', '<unknown>')}: "
                f"{error}"
            )

    return results


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build ISO's curated Institutional "
            "Constitution from normalized observations."
        )
    )

    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(
            "config/institutional_constitution.yaml"
        ),
    )

    parser.add_argument(
        "--clear",
        action="store_true",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config()

    project_root = Path(
        config["project"]["root"]
    )

    storage = config["storage"]

    registry_path = args.registry

    if not registry_path.is_absolute():
        registry_path = (
            project_root / registry_path
        )

    normalized_dir = (
        project_root
        / storage["normalized"]
    )

    output_dir = (
        project_root
        / storage.get(
            "constitutional",
            "storage/constitutional",
        )
    )

    print("=" * 72)
    print("ISO Institutional Constitution")
    print("=" * 72)
    print(f"Registry:       {registry_path}")
    print(f"Normalized:     {normalized_dir}")
    print(f"Constitution:   {output_dir}")
    print()

    results = build_catalog(
        registry_path=registry_path,
        normalized_dir=normalized_dir,
        output_dir=output_dir,
        clear=args.clear,
    )

    print()
    print("=" * 72)
    print("Summary")
    print("=" * 72)
    print(f"Attempted : {results['attempted']}")
    print(f"Created   : {results['created']}")
    print(f"Unchanged : {results['unchanged']}")
    print(f"Disabled  : {results['disabled']}")
    print(f"Failed    : {results['failed']}")

    if results["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
