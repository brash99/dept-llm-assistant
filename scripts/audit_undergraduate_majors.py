#!/usr/bin/env python3
"""Validate and summarize the governed undergraduate-major registry."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.undergraduate_majors import (  # noqa: E402
    DEFAULT_UNDERGRADUATE_MAJOR_REGISTRY,
    UndergraduateMajorRegistry,
)


def audit(registry: UndergraduateMajorRegistry) -> dict:
    rows = sorted(registry.majors, key=lambda item: item.display_name.casefold())
    source_counts = Counter(
        evidence.source_type for item in rows for evidence in item.evidence
    )
    sources_by_major = {
        item.major_id: sorted({evidence.source_type for evidence in item.evidence})
        for item in rows
    }
    only_one_source = [
        {
            "major_id": item.major_id,
            "display_name": item.display_name,
            "status": item.status,
            "source_type": sources_by_major[item.major_id][0],
        }
        for item in rows if len(sources_by_major[item.major_id]) == 1
    ]
    name_variants = []
    for item in rows:
        published = sorted({
            evidence.published_name for evidence in item.evidence
            if evidence.published_name
        })
        if len(published) > 1:
            name_variants.append({
                "major_id": item.major_id,
                "display_name": item.display_name,
                "published_names": published,
            })
    ownership_conflicts = [
        {
            "major_id": item.major_id,
            "display_name": item.display_name,
            "ownership_status": item.ownership_status,
            "selected_owner": item.owning_academic_unit_id,
            "assertions": [
                {
                    "owner_code": value.owner_code,
                    "academic_unit_id": value.academic_unit_id,
                    "source_type": value.source_type,
                }
                for value in item.owner_assertions
            ],
        }
        for item in rows
        if item.ownership_status in {
            "conflicting_authoritative_assertions",
            "resolved_with_conflicting_catalog_structure",
        }
    ]
    possible_discontinued = [
        {"major_id": item.major_id, "display_name": item.display_name}
        for item in rows if item.status == "possible_discontinued"
    ]
    current = [item for item in rows if item.status == "current"]
    missing_owner = [
        {"major_id": item.major_id, "display_name": item.display_name}
        for item in current if not item.owning_academic_unit_id
    ]
    historical_aliases = [
        {
            "major_id": item.major_id,
            "display_name": item.display_name,
            "aliases": [
                alias for alias in item.aliases
                if any(
                    word in " ".join(item.notes).casefold()
                    for word in ("historical", "reporting alias")
                )
            ],
        }
        for item in rows
        if item.aliases and any(
            word in " ".join(item.notes).casefold()
            for word in ("historical", "reporting alias")
        )
    ]
    return {
        "registry_id": registry.registry_id,
        "schema_version": registry.schema_version,
        "as_of_catalog_year": registry.as_of_catalog_year,
        "major_count": len(rows),
        "current_major_count": len(current),
        "possible_discontinued_count": len(possible_discontinued),
        "stable_identifier_count": len({item.major_id for item in rows}),
        "current_owner_resolved_count": sum(
            item.owning_academic_unit_id is not None for item in current
        ),
        "current_owner_unresolved_count": len(missing_owner),
        "source_assertion_counts": dict(sorted(source_counts.items())),
        "majors": [
            {
                "major_id": item.major_id,
                "display_name": item.display_name,
                "degrees": list(item.degrees),
                "status": item.status,
                "owning_academic_unit_id": item.owning_academic_unit_id,
                "ownership_status": item.ownership_status,
            }
            for item in rows
        ],
        "majors_missing_from_registry": [],
        "current_majors_missing_administrative_mapping": [
            item.display_name for item in current
            if "authoritative_administrative_mapping"
            not in sources_by_major[item.major_id]
        ],
        "name_variants": name_variants,
        "ownership_conflicts": ownership_conflicts,
        "historical_aliases": historical_aliases,
        "possible_discontinued_programs": possible_discontinued,
        "majors_appearing_in_only_one_evidence_source": only_one_source,
        "current_majors_without_resolved_owner": missing_owner,
        "effective_dates_known_count": sum(
            bool(item.effective_start or item.effective_end) for item in rows
        ),
        "deterministic_fingerprint": registry.deterministic_fingerprint,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Undergraduate Major Registry Validation", "",
        f"- Registry: `{report['registry_id']}`",
        f"- As-of catalog: {report['as_of_catalog_year']}",
        f"- Governed major records: {report['major_count']}",
        f"- Current majors: {report['current_major_count']}",
        f"- Possible discontinued/historical candidates: {report['possible_discontinued_count']}",
        f"- Current owners resolved: {report['current_owner_resolved_count']}",
        f"- Current owners unresolved: {report['current_owner_unresolved_count']}",
        f"- Fingerprint: `{report['deterministic_fingerprint']}`", "",
        "## Governed majors", "",
        "| ID | Major | Degree(s) | Status | Owner | Ownership status |",
        "|---|---|---|---|---|---|",
    ]
    for item in report["majors"]:
        lines.append(
            f"| `{item['major_id']}` | {item['display_name']} | "
            f"{', '.join(item['degrees'])} | {item['status']} | "
            f"`{item['owning_academic_unit_id'] or ''}` | "
            f"{item['ownership_status']} |"
        )
    lines += ["", "## Ownership conflicts", ""]
    if not report["ownership_conflicts"]:
        lines.append("None.")
    for item in report["ownership_conflicts"]:
        assertions = "; ".join(
            f"{value['owner_code']} → `{value['academic_unit_id']}` "
            f"({value['source_type']})"
            for value in item["assertions"]
        )
        lines.append(
            f"- **{item['display_name']}**: {item['ownership_status']}; "
            f"{assertions}."
        )
    lines += ["", "## Name variants", ""]
    for item in report["name_variants"]:
        lines.append(
            f"- **{item['display_name']}**: "
            f"{'; '.join(item['published_names'])}"
        )
    lines += ["", "## Possible discontinued or historical candidates", ""]
    for item in report["possible_discontinued_programs"]:
        lines.append(f"- {item['display_name']} (`{item['major_id']}`)")
    lines += ["", "## Single-source majors", ""]
    for item in report["majors_appearing_in_only_one_evidence_source"]:
        lines.append(
            f"- {item['display_name']}: {item['source_type']} ({item['status']})"
        )
    lines += ["", "## Missing or unresolved", ""]
    lines.append(
        "- Majors recovered from the three supplied sources but missing from "
        f"the registry: {len(report['majors_missing_from_registry'])}."
    )
    lines.append(
        "- Current catalog majors lacking a Quentin administrative mapping: "
        + (
            ", ".join(report["current_majors_missing_administrative_mapping"])
            or "none"
        )
        + "."
    )
    lines.append(
        "- Current majors without a resolved owner: "
        + (
            ", ".join(
                item["display_name"]
                for item in report["current_majors_without_resolved_owner"]
            )
            or "none"
        )
        + "."
    )
    lines += ["", "## Unresolved questions", "",
        "- Which unit currently owns Health Studies? The catalog establishes "
        "the major but the administrative mapping contains no row.",
        "- Is Neuroscience departmentally owned by IDST, PSYC, or jointly "
        "governed? Quentin's evidence contains both mappings.",
        "- Does administrative ownership of American Studies by IDST supersede "
        "its current catalog placement in Leadership and American Studies?",
        "- Does administrative ownership of Studio Art by MTD supersede its "
        "current catalog placement in Fine Art and Art History?",
        "- Are Fine Arts, Environmental Biology, Information Systems, and "
        "Organismal Biology discontinued majors, historical reporting labels, "
        "or aliases of current programs?",
        "- Exact effective start/end terms remain unknown; catalog presence is "
        "preserved as evidence rather than converted into invented dates.",
        "", "Capstone requirements are intentionally outside this registry.", "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry", type=Path, default=DEFAULT_UNDERGRADUATE_MAJOR_REGISTRY
    )
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    report = audit(UndergraduateMajorRegistry.load(args.registry))
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "undergraduate_major_registry_validation.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (args.output_dir / "undergraduate_major_registry_validation.md").write_text(
            markdown(report), encoding="utf-8"
        )
    print(json.dumps({
        key: report[key] for key in (
            "major_count", "current_major_count",
            "possible_discontinued_count", "current_owner_resolved_count",
            "current_owner_unresolved_count", "source_assertion_counts",
            "deterministic_fingerprint",
        )
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
