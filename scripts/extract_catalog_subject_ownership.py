#!/usr/bin/env python3
"""Extract catalog subject evidence and reviewable ownership candidates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from app.catalog_subject_ownership import (
    CatalogCoursePrefixExtractor, CatalogEditionSelector,
    CatalogSectionAcademicUnitResolver, CatalogSubjectOwnershipCandidateService,
    build_catalog_subject_report, compare_catalog_subject_reports,
)
from app.subject_ownership import SubjectOwnershipRegistry
from app.semantic_discrepancy import SemanticDiscrepancyAnalyzer


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-root", type=Path, default=Path("data/acquisition/catalogs"))
    parser.add_argument("--catalog", help="Explicit catalog ID or repository-relative PDF path.")
    parser.add_argument("--schedule-root", type=Path, help="Optional normalized schedules for three-way comparison.")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--subject", action="append")
    parser.add_argument("--academic-unit")
    parser.add_argument("--candidate-status")
    parser.add_argument("--exceptions-only", action="store_true")
    parser.add_argument("--unresolved-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("OLD_REPORT", "NEW_REPORT"))
    parser.add_argument("--explain-discrepancies", action="store_true", help="Explain catalog, schedule, and governance differences deterministically.")
    return parser.parse_args(argv)


def _schedule_subjects(root):
    if not root: return {}
    inventory = {}
    for path in Path(root).rglob("*.json"):
        try: value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): continue
        if value.get("object_type") == "course_offering_observation" and value.get("subject"):
            subject = str(value["subject"]).strip().upper()
            row = inventory.setdefault(subject, {"offering_count": 0, "terms": set(), "instructors": set()})
            row["offering_count"] += 1
            if value.get("academic_term"): row["terms"].add(str(value["academic_term"]))
            instructor = str(value.get("instructor_raw") or value.get("instructor_name") or "").strip().casefold()
            if instructor: row["instructors"].add(instructor)
    return {subject: {"offering_count": row["offering_count"], "term_count": len(row["terms"]), "distinct_instructor_count": len(row["instructors"])} for subject, row in sorted(inventory.items())}


def build_report(args):
    selector = CatalogEditionSelector(); editions = selector.discover(args.catalog_root)
    selection = selector.select(editions, override=args.catalog)
    if not selection.selected:
        raise ValueError(selection.rationale)
    observations, malformed = CatalogCoursePrefixExtractor().extract(selection.selected)
    resolver = CatalogSectionAcademicUnitResolver()
    governed = SubjectOwnershipRegistry.load()
    candidates = CatalogSubjectOwnershipCandidateService().generate(observations, resolver, governed)
    report = build_catalog_subject_report(selection, observations, malformed, candidates, governed, _schedule_subjects(args.schedule_root))
    if args.explain_discrepancies:
        report["discrepancy_dashboard"] = SemanticDiscrepancyAnalyzer().analyze(
            governed, report["catalog_observations"], report["candidates"],
            report["schedule_subject_inventory"],
        ).to_dict()
    return report


def _filtered(report, args):
    values = report["candidates"]
    subjects = {x.strip().upper() for x in (args.subject or ())}
    if subjects: values = [x for x in values if x["subject_code"] in subjects]
    if args.academic_unit: values = [x for x in values if x["proposed_analytical_academic_unit_id"] == args.academic_unit]
    if args.candidate_status: values = [x for x in values if x["candidate_status"] == args.candidate_status]
    if args.exceptions_only: values = [x for x in values if x["candidate_status"] == "exception_candidate"]
    if args.unresolved_only: values = [x for x in values if x["candidate_status"] in {"requires_review", "ambiguous", "unsupported"}]
    return values


def _write_csv(rows, handle):
    if not rows: return
    flat = []
    for row in rows:
        value = dict(row)
        for key in ("source_sections", "observed_course_codes", "conflicts"):
            if key in value: value[key] = " | ".join(value[key])
        flat.append(value)
    writer = csv.DictWriter(handle, fieldnames=list(flat[0])); writer.writeheader(); writer.writerows(flat)


def _markdown(report, rows):
    selected = report["selection"]["selected"]; fitness = report["evidence_fitness"]
    lines = ["# Catalog Subject-Ownership Candidate Report", "", f"- Catalog: {selected['catalog_title']} (`{selected['catalog_id']}`)", f"- Academic year: {selected['academic_year']}", f"- Extracted prefixes: {fitness['extracted_unique_prefix_count']}", f"- Course descriptions: {fitness['extracted_course_description_count']}", f"- Deterministic fingerprint: `{report['deterministic_report_fingerprint']}`", "", "| Subject | Status | Proposed unit | Courses | Sections |", "|---|---|---|---:|---:|"]
    for row in rows: lines.append(f"| {row['subject_code']} | {row['candidate_status']} | {row['proposed_analytical_academic_unit_id'] or ''} | {len(row['observed_course_codes'])} | {len(row['source_sections'])} |")
    if report.get("discrepancy_dashboard"):
        dashboard = report["discrepancy_dashboard"]
        source = dashboard["source_comparison"]
        lines += ["", "## Semantic prefix investigation", "",
                  f"- Catalog prefixes: {source['catalog_prefixes']}",
                  f"- Schedule prefixes: {source['schedule_prefixes']}",
                  f"- Found in both: {source['found_in_both']}",
                  f"- Catalog only: {source['catalog_only']}",
                  f"- Schedule only: {source['schedule_only']}",
                  f"- Schedule-only unexplained: {source['schedule_only_unexplained']}", "",
                  "| Prefix | Found in | Category | Confidence | Priority | Action |", "|---|---|---|---:|---|---|"]
        for item in dashboard["records"]:
            evidence = item["evidence"]
            found = ", ".join(name for name, present in (("governance", evidence["governed"]), ("catalog", evidence["current_catalog"]), ("schedule", evidence["production_schedule"])) if present)
            lines.append(f"| {item['prefix']} | {found} | {item['category']} | {item['confidence']:.2f} | {item['review_priority']} | {item['suggested_next_action']} |")
    lines += ["", "Candidates are review artifacts and are never written automatically to the governed registry.", ""]
    return "\n".join(lines)


def _review_yaml(rows):
    return {"schema_version": 1, "source": "catalog_subject_ownership_candidate_report", "candidates": [{"subject_code": x["subject_code"], "display_name": None, "owning_academic_unit_id": x["proposed_owning_academic_unit_id"], "analytical_academic_unit_id": x["proposed_analytical_academic_unit_id"], "relationship_type": x["proposed_relationship_type"], "mapping_status": x["proposed_mapping_status"], "review_status": "requires_review", "evidence": [{"source": x["source_catalog_id"], "source_type": "official_catalog", "assertion": f"Course descriptions appear under: {', '.join(x['source_sections'])}"}], "rationale": None, "notes": x["review_recommendation"]} for x in rows]}


def write_outputs(report, rows, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "catalog_subject_ownership.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output_dir / "catalog_subject_candidates.csv").open("w", encoding="utf-8", newline="") as handle: _write_csv(rows, handle)
    (output_dir / "catalog_subject_ownership.md").write_text(_markdown(report, rows), encoding="utf-8")
    (output_dir / "catalog_subject_candidates.review.yaml").write_text(yaml.safe_dump(_review_yaml(rows), sort_keys=False), encoding="utf-8")
    with (output_dir / "catalog_subject_review_queue.csv").open("w", encoding="utf-8", newline="") as handle: _write_csv(report["review_queue"], handle)
    if report.get("discrepancy_dashboard"):
        with (output_dir / "semantic_prefix_investigation.csv").open("w", encoding="utf-8", newline="") as handle:
            flat = []
            for item in report["discrepancy_dashboard"]["records"]:
                evidence = item["evidence"]
                flat.append({"prefix": item["prefix"], "found_in_governance": evidence["governed"], "found_in_catalog": evidence["current_catalog"], "found_in_schedule": evidence["production_schedule"], "category": item["category"], "rationale": item["rationale"], "confidence": item["confidence"], "suggested_action": item["suggested_next_action"], "review_priority": item["review_priority"]})
            _write_csv(flat, handle)


def main(argv=None):
    args = parse_args(argv)
    if args.compare:
        old = json.loads(args.compare[0].read_text(encoding="utf-8")); new = json.loads(args.compare[1].read_text(encoding="utf-8"))
        print(json.dumps(compare_catalog_subject_reports(old, new), indent=2, sort_keys=True)); return 0
    report = build_report(args); rows = _filtered(report, args)
    if args.output_dir: write_outputs(report, rows, args.output_dir)
    if args.json: print(json.dumps(report, indent=2, sort_keys=True))
    elif args.csv: _write_csv(rows, sys.stdout)
    else:
        selected = report["selection"]["selected"]
        print(f"Catalog: {selected['catalog_id']} ({selected['academic_year']})")
        print(f"Course descriptions: {report['evidence_fitness']['extracted_course_description_count']}")
        print(f"Unique prefixes: {report['evidence_fitness']['extracted_unique_prefix_count']}")
        print(f"Candidates shown: {len(rows)}")
        if report.get("discrepancy_dashboard"):
            dashboard = report["discrepancy_dashboard"]
            source = dashboard["source_comparison"]
            print(f"Catalog prefixes: {source['catalog_prefixes']}")
            print(f"Schedule prefixes: {source['schedule_prefixes']}")
            print(f"Found in both: {source['found_in_both']}")
            print(f"Catalog only: {source['catalog_only']}")
            print(f"Schedule only: {source['schedule_only']}")
            print(f"Schedule-only unexplained: {source['schedule_only_unexplained']}")
            print(f"Investigation fingerprint: {dashboard['deterministic_fingerprint']}")
        print(f"Fingerprint: {report['deterministic_report_fingerprint']}")
        if args.output_dir: print(f"Reports: {args.output_dir}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
