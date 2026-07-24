#!/usr/bin/env python3
"""Validate and summarize the governed undergraduate capstone registry."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from app.undergraduate_major_capstones import (
    DEFAULT_MAJOR_CAPSTONE_REGISTRY,
    UndergraduateMajorCapstoneRegistry,
)


def audit(registry: UndergraduateMajorCapstoneRegistry) -> dict[str, Any]:
    rows = []
    for item in sorted(
        registry.requirements, key=lambda value: value.display_name.casefold()
    ):
        rows.append({
            "major_id": item.major_id,
            "major": item.display_name,
            "requirement_type": item.requirement_type,
            "pathways": [
                {
                    "label": pathway.label,
                    "requirement_type": pathway.requirement_type,
                    "course_ids": list(pathway.course_ids),
                    "non_course_requirement": pathway.non_course_requirement,
                    "catalog_pages": list(pathway.evidence.catalog_pages),
                    "evidence_confidence": (
                        pathway.evidence.evidence_confidence
                    ),
                }
                for pathway in item.pathways
            ],
            "notes": list(item.notes),
        })
    counts = Counter(item["requirement_type"] for item in rows)
    unresolved = [
        item["major"] for item in rows
        if item["requirement_type"] == "unresolved"
        or any(
            pathway["requirement_type"] == "unresolved"
            for pathway in item["pathways"]
        )
    ]
    ambiguous = [
        item["major"] for item in rows
        if item["requirement_type"] in {
            "alternative_capstone_choices",
            "thesis_or_seminar_options",
            "multiple_pathways",
        }
    ]
    multiple = [
        item["major"] for item in rows
        if len(item["pathways"]) > 1
        or item["requirement_type"] in {
            "required_capstone_sequence",
            "multiple_required_capstones",
            "alternative_capstone_choices",
            "thesis_or_seminar_options",
            "multiple_pathways",
        }
    ]
    return {
        "schema_version": 1,
        "registry_id": registry.registry_id,
        "catalog_year": registry.catalog_year,
        "major_count": len(rows),
        "requirement_type_counts": dict(sorted(counts.items())),
        "unresolved_major_count": len(unresolved),
        "unresolved_majors": unresolved,
        "ambiguous_or_choice_major_count": len(ambiguous),
        "ambiguous_or_choice_majors": ambiguous,
        "multiple_pathway_or_requirement_count": len(multiple),
        "multiple_pathway_or_requirement_majors": multiple,
        "deterministic_fingerprint": registry.deterministic_fingerprint,
        "majors": rows,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Undergraduate Major → Capstone Validation",
        "",
        f"Catalog year: **{summary['catalog_year']}**",
        "",
        f"Current majors validated: **{summary['major_count']}**",
        "",
        "## Complete inventory",
        "",
        "| Major | Classification | Capstone requirement(s) | Pages | Confidence |",
        "|---|---|---|---|---|",
    ]
    for item in summary["majors"]:
        requirements = []
        pages = set()
        confidence = set()
        for pathway in item["pathways"]:
            value = ", ".join(pathway["course_ids"])
            if pathway["non_course_requirement"]:
                value = (
                    f"{value}; " if value else ""
                ) + pathway["non_course_requirement"]
            requirements.append(f"{pathway['label']}: {value or 'none identified'}")
            pages.update(pathway["catalog_pages"])
            confidence.add(pathway["evidence_confidence"])
        lines.append(
            f"| {item['major']} | {item['requirement_type']} | "
            f"{'<br>'.join(requirements)} | "
            f"{', '.join(str(page) for page in sorted(pages))} | "
            f"{', '.join(sorted(confidence))} |"
        )
    lines.extend([
        "",
        "## Unresolved majors",
        "",
    ])
    lines.extend(
        [f"- {name}" for name in summary["unresolved_majors"]]
        or ["- None"]
    )
    lines.extend([
        "",
        "## Ambiguous majors or explicit choices",
        "",
    ])
    lines.extend(
        [f"- {name}" for name in summary["ambiguous_or_choice_majors"]]
        or ["- None"]
    )
    lines.extend([
        "",
        "## Majors with multiple pathways or requirements",
        "",
    ])
    lines.extend(
        [
            f"- {name}"
            for name in summary["multiple_pathway_or_requirement_majors"]
        ]
        or ["- None"]
    )
    lines.extend([
        "",
        "## Interpretation limits",
        "",
        "- `no_identifiable_capstone` means the catalog's exhaustive major "
        "requirements do not identify a required capstone; it does not assert "
        "that students complete no culminating work.",
        "- Optional independent study, undergraduate research, internships, "
        "and minor-only capstones are not promoted into major requirements.",
        "- Music remains pathway-specific because the catalog defines different "
        "final assessments for BA and BM concentrations.",
        "- No graduate estimates or degree-completion counts are produced.",
        "",
        f"Deterministic fingerprint: `{summary['deterministic_fingerprint']}`",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry", type=Path, default=DEFAULT_MAJOR_CAPSTONE_REGISTRY
    )
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    args = parser.parse_args()
    registry = UndergraduateMajorCapstoneRegistry.load(args.registry)
    summary = audit(registry)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = (
        args.output_dir / "undergraduate_major_capstone_validation.json"
    )
    md_path = args.output_dir / "undergraduate_major_capstone_validation.md"
    json_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps({
        "major_count": summary["major_count"],
        "unresolved_major_count": summary["unresolved_major_count"],
        "ambiguous_or_choice_major_count": (
            summary["ambiguous_or_choice_major_count"]
        ),
        "fingerprint": summary["deterministic_fingerprint"],
        "json": str(json_path),
        "markdown": str(md_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
