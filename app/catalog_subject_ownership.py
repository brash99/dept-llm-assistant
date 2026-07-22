"""Deterministic catalog evidence and candidates for subject ownership.

Extraction records what a catalog publishes. Candidate generation proposes a
reviewable interpretation. Neither operation mutates governed registries.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import fitz

from app.institutional_units import AcademicUnitRegistry
from app.subject_ownership import SubjectOwnershipRegistry


ALGORITHM_VERSION = "1.0"
COURSE_HEADER = re.compile(r"^(?P<prefix>[A-Z]{2,5})\s+(?P<number>\d{3}[A-Z]?)\.\s*(?P<title>.*)$")
CATALOG_FILENAME = re.compile(
    r"(?P<start>20\d{2})-(?P<end>\d{2})-(?P<kind>undergraduate|graduate).*\.pdf$",
    re.IGNORECASE,
)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


@dataclass(frozen=True)
class CatalogEdition:
    catalog_id: str
    catalog_title: str
    academic_year: str
    effective_start: int
    effective_end: int
    catalog_kind: str
    source_file: str
    source_sha256: str

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class CatalogSelectionResult:
    status: str
    selected: CatalogEdition | None
    candidates: tuple[CatalogEdition, ...]
    confidence: float
    rationale: str

    def to_dict(self):
        return {**asdict(self), "selected": self.selected.to_dict() if self.selected else None,
                "candidates": [item.to_dict() for item in self.candidates]}


class CatalogEditionSelector:
    def discover(self, root: Path) -> tuple[CatalogEdition, ...]:
        editions = []
        for path in sorted(Path(root).glob("*.pdf")):
            match = CATALOG_FILENAME.search(path.name)
            if not match:
                continue
            start = int(match.group("start")); end = 2000 + int(match.group("end"))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            editions.append(CatalogEdition(
                f"catalog:{start}-{match.group('end')}:{match.group('kind').lower()}",
                f"{match.group('kind').title()} Catalog {start}-{match.group('end')}",
                f"{start}-{match.group('end')}", start, end, match.group("kind").lower(),
                _relative(path), digest,
            ))
        return tuple(editions)

    def select(self, editions: Sequence[CatalogEdition], *, kind="undergraduate", override=None):
        eligible = tuple(item for item in editions if item.catalog_kind == kind)
        if override:
            matches = tuple(item for item in eligible if override in {item.catalog_id, item.source_file})
            return CatalogSelectionResult("selected" if len(matches) == 1 else "ambiguous", matches[0] if len(matches) == 1 else None, matches, 1.0 if len(matches) == 1 else 0.0, "Explicit catalog override." if len(matches) == 1 else "Override did not identify exactly one catalog.")
        if not eligible:
            return CatalogSelectionResult("missing", None, (), 0.0, "No applicable catalog edition was discovered.")
        latest = max((item.effective_start, item.effective_end) for item in eligible)
        matches = tuple(item for item in eligible if (item.effective_start, item.effective_end) == latest)
        return CatalogSelectionResult("selected" if len(matches) == 1 else "ambiguous", matches[0] if len(matches) == 1 else None, matches, 1.0 if len(matches) == 1 else 0.0, "Selected by governed academic-year metadata." if len(matches) == 1 else "Multiple editions share the latest governed academic year.")


@dataclass(frozen=True)
class CatalogSubjectOwnershipObservation:
    observation_id: str
    catalog_id: str
    catalog_title: str
    catalog_academic_year: str
    catalog_effective_start: int
    catalog_effective_end: int
    source_file: str
    source_locator: tuple[int, ...]
    section_title: str
    section_title_path: tuple[str, ...]
    section_academic_unit_candidate: str | None
    subject_code: str
    observed_course_codes: tuple[str, ...]
    observed_course_count: int
    extraction_method: str
    extraction_confidence: float
    structural_evidence: tuple[str, ...]
    evidence_excerpts: tuple[str, ...]
    provenance: Mapping[str, Any]
    created_at: str
    deterministic_fingerprint: str

    def to_dict(self): return asdict(self)


class CatalogCoursePrefixExtractor:
    def extract(self, edition: CatalogEdition, *, created_at: str | None = None):
        created = created_at or datetime.now(timezone.utc).isoformat()
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        section_designations: dict[str, set[str]] = defaultdict(set)
        malformed: list[dict[str, Any]] = []
        with fitz.open(Path(edition.source_file)) as document:
            current_section = ""
            for page_index, page in enumerate(document):
                lines = [" ".join(value.split()) for value in page.get_text("text").splitlines() if value.strip()]
                section = _page_section(lines, edition.academic_year) or current_section
                if section:
                    current_section = section
                for line in lines:
                    designation = re.match(r"^(Major|Minor) in\s+", line, re.IGNORECASE)
                    if designation and current_section:
                        section_designations[current_section].add(designation.group(1).casefold())
                for line in lines:
                    match = COURSE_HEADER.match(line)
                    if match:
                        prefix = match.group("prefix").upper()
                        code = f"{prefix} {match.group('number')}"
                        key = (current_section or "Unresolved catalog section", prefix)
                        bucket = grouped.setdefault(key, {"codes": set(), "pages": set(), "headers": []})
                        bucket["codes"].add(code); bucket["pages"].add(page_index + 1)
                        if len(bucket["headers"]) < 8: bucket["headers"].append(line[:240])
                    elif re.match(r"^[A-Z]{2,5}\s+\d{2,4}[A-Z]?\s*\.", line):
                        malformed.append({"page": page_index + 1, "line": line[:160], "section": current_section})
        observations = []
        for (section, prefix), data in sorted(grouped.items()):
            codes = tuple(sorted(data["codes"])); pages = tuple(sorted(data["pages"]))
            semantic = {"catalog_id": edition.catalog_id, "section_title": section, "subject_code": prefix, "course_codes": codes, "pages": pages, "algorithm_version": ALGORITHM_VERSION}
            digest = _fingerprint(semantic)
            observations.append(CatalogSubjectOwnershipObservation(
                f"catalog_subject:{digest}", edition.catalog_id, edition.catalog_title,
                edition.academic_year, edition.effective_start, edition.effective_end,
                edition.source_file, pages, section, (section,), section, prefix, codes,
                len(codes), "catalog_course_description_header_v1", 1.0,
                tuple(f"page:{page}" for page in pages), tuple(data["headers"][:5]),
                {"source_sha256": edition.source_sha256, "algorithm_version": ALGORITHM_VERSION,
                 "section_program_designations": sorted(section_designations.get(section, ()))},
                created, digest,
            ))
        return tuple(observations), tuple(malformed)


def _page_section(lines: Sequence[str], academic_year: str) -> str | None:
    start, end = academic_year.split("-", 1)
    expanded_year = f"{start}-{str(int(start[:2]) * 100 + int(end))}"
    for line in lines[:8]:
        if line.isdigit() or line in {academic_year, expanded_year, ".", "___________________"}:
            continue
        if not line[:1].isupper():
            continue
        if COURSE_HEADER.match(line) or len(line) > 100 or len(line.split()) > 8 or line.endswith(('.', ':', ';', '-', '\xad')):
            continue
        return line
    return None


@dataclass(frozen=True)
class CatalogSectionAcademicUnitResolution:
    status: str
    section_title: str
    section_title_path: tuple[str, ...]
    candidate_unit_ids: tuple[str, ...]
    selected_unit_id: str | None
    match_method: str
    confidence: float
    rationale: str
    competing_candidates: tuple[str, ...]
    source_catalog_id: str
    exception_classification: str | None = None
    proposed_relationship_type: str | None = None

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class CatalogSectionExceptionContext:
    section_title: str
    exception_classification: str
    relationship_type: str
    evidence_source: str
    review_status: str
    rationale: str


DEFAULT_EXCEPTION_CONTEXTS = (
    CatalogSectionExceptionContext(
        "College Studies", "service_subject", "centrally_administered_subject",
        "institutional_review_context:college_studies:2026-07-22", "requires_review",
        "Course ownership is distinct from the home units of instructors who teach COLL offerings.",
    ),
    CatalogSectionExceptionContext(
        "Interdisciplinary Studies", "interdisciplinary", "interdisciplinary_subject",
        "institutional_review_context:interdisciplinary_studies:2026-07-22", "requires_review",
        "IDST is cross-disciplinary and must not be assigned from an instructor's home unit.",
    ),
)


class CatalogSectionAcademicUnitResolver:
    def __init__(self, registry: AcademicUnitRegistry | None = None, reviewed_aliases: Mapping[str, str] | None = None, exception_contexts: Sequence[CatalogSectionExceptionContext] = DEFAULT_EXCEPTION_CONTEXTS):
        self.registry = registry or AcademicUnitRegistry.load()
        self.reviewed_aliases = {_label(k): v for k, v in (reviewed_aliases or {}).items()}
        self.exception_contexts = {_label(item.section_title): item for item in exception_contexts}

    def resolve(self, observation: CatalogSubjectOwnershipObservation):
        labels = tuple(dict.fromkeys((*observation.section_title_path, observation.section_title)))
        candidates = {unit.unit_id for label in labels for unit in [self.registry.resolve(label)] if unit}
        for label in labels:
            target = self.reviewed_aliases.get(_label(label))
            if target: candidates.add(target)
        exceptions = [self.exception_contexts[_label(label)] for label in labels if _label(label) in self.exception_contexts]
        if exceptions:
            context = exceptions[0]
            return CatalogSectionAcademicUnitResolution("central_or_interdisciplinary_section", observation.section_title, observation.section_title_path, (), None, "exact_review_context", 1.0, context.rationale, (), observation.catalog_id, context.exception_classification, context.relationship_type)
        if len(candidates) == 1:
            selected = next(iter(candidates))
            return CatalogSectionAcademicUnitResolution("resolved", observation.section_title, observation.section_title_path, (selected,), selected, "exact_governed_alias", 1.0, "Exact section title/path alias resolves to a governed unit.", (), observation.catalog_id)
        if len(candidates) > 1:
            values = tuple(sorted(candidates))
            return CatalogSectionAcademicUnitResolution("ambiguous", observation.section_title, observation.section_title_path, values, None, "competing_exact_aliases", 0.0, "Multiple governed units match the section path.", values, observation.catalog_id)
        return CatalogSectionAcademicUnitResolution("unresolved", observation.section_title, observation.section_title_path, (), None, "no_exact_governed_alias", 0.0, "No exact governed unit or reviewed section alias matches.", (), observation.catalog_id)


@dataclass(frozen=True)
class SubjectOwnershipCandidate:
    subject_code: str
    proposed_owning_academic_unit_id: str | None
    proposed_analytical_academic_unit_id: str | None
    proposed_relationship_type: str
    proposed_mapping_status: str
    candidate_status: str
    source_catalog_id: str
    source_sections: tuple[str, ...]
    observed_course_codes: tuple[str, ...]
    evidence_count: int
    confidence: float
    review_recommendation: str
    conflicts: tuple[str, ...]
    notes: str
    deterministic_candidate_fingerprint: str

    def to_dict(self): return asdict(self)


class CatalogSubjectOwnershipCandidateService:
    def generate(self, observations, resolver: CatalogSectionAcademicUnitResolver, governed_registry: SubjectOwnershipRegistry | None = None):
        by_subject = defaultdict(list)
        for item in observations: by_subject[item.subject_code].append((item, resolver.resolve(item)))
        results = []
        for subject, pairs in sorted(by_subject.items()):
            units = {resolution.selected_unit_id for _, resolution in pairs if resolution.selected_unit_id}
            exception = {resolution.exception_classification for _, resolution in pairs if resolution.exception_classification}
            statuses = {resolution.status for _, resolution in pairs}
            conflicts = []
            if len(units) > 1: conflicts.append("prefix_appears_under_multiple_academic_units")
            if "ambiguous" in statuses: conflicts.append("ambiguous_section_resolution")
            if exception:
                candidate_status = "exception_candidate"; unit = None
                mapping_status = sorted(exception)[0]
                relationship = next(res.proposed_relationship_type for _, res in pairs if res.proposed_relationship_type)
                confidence = 1.0; recommendation = "Institutional review required; do not treat as an ordinary department mapping."
            elif len(units) == 1 and not conflicts:
                candidate_status = "high_confidence_candidate"; unit = next(iter(units))
                mapping_status = "intentionally_grouped_department_equivalent" if unit == "academic_unit:sec" else "mapped"
                relationship = "owns_instructional_subject"; confidence = 1.0
                recommendation = "Review catalog evidence before adding a governed record."
            elif conflicts or len(units) > 1:
                candidate_status = "ambiguous"; unit = None; mapping_status = "ambiguous"; relationship = "unresolved"; confidence = 0.0; recommendation = "Resolve conflicting catalog sections."
            elif "unresolved" in statuses:
                candidate_status = "requires_review"; unit = None; mapping_status = "unmapped"; relationship = "unresolved"; confidence = 0.0; recommendation = "Review section-to-unit identity."
            else:
                candidate_status = "unsupported"; unit = None; mapping_status = "unsupported"; relationship = "unresolved"; confidence = 0.0; recommendation = "Insufficient catalog structure."
            sections = tuple(sorted({item.section_title for item, _ in pairs})); codes = tuple(sorted({code for item, _ in pairs for code in item.observed_course_codes}))
            governed_records = governed_registry.records_for_subject(subject) if governed_registry else ()
            if len(governed_records) == 1:
                governed_target = governed_records[0].analytical_academic_unit_id
                if unit and governed_target != unit:
                    conflicts.append("catalog_candidate_differs_from_governed_target")
                    candidate_status = "requires_review"
                    recommendation = "Review catalog evidence against the existing governed target; do not overwrite governance."
                elif unit == governed_target:
                    recommendation = "Catalog candidate supports the existing governed record; retain human governance."
            semantic = {"subject": subject, "unit": unit, "status": candidate_status, "mapping_status": mapping_status, "relationship": relationship, "sections": sections, "codes": codes, "conflicts": conflicts, "catalog": pairs[0][0].catalog_id}
            results.append(SubjectOwnershipCandidate(subject, unit, unit, relationship, mapping_status, candidate_status, pairs[0][0].catalog_id, sections, codes, len(pairs), confidence, recommendation, tuple(conflicts), "Candidate only; never automatically governed.", _fingerprint(semantic)))
        return tuple(results)


@dataclass(frozen=True)
class CatalogOwnershipEvidenceFitness:
    catalog_edition_selected: str | None
    catalog_selection_confidence: float
    section_resolution_coverage_percent: float
    extracted_course_description_count: int
    extracted_unique_prefix_count: int
    resolved_candidate_count: int
    ambiguous_candidate_count: int
    exception_candidate_count: int
    prefixes_appearing_under_multiple_sections: int
    prefixes_lacking_governed_ownership: int
    governed_prefixes_lacking_current_catalog_support: int
    schedule_prefixes_lacking_catalog_support: int
    catalog_prefixes_lacking_schedule_observations: int
    suitability: Mapping[str, str]

    def to_dict(self): return asdict(self)


def build_catalog_subject_report(selection, observations, malformed, candidates, governed, schedule_subjects=()):
    catalog_codes = {item.subject_code for item in observations}; governed_codes = {item.subject_code for item in governed.records}
    schedule_inventory = schedule_subjects if isinstance(schedule_subjects, Mapping) else {str(x).upper(): {} for x in schedule_subjects}
    schedule_codes = set(schedule_inventory)
    candidate_by = {item.subject_code: item for item in candidates}
    governed_by = {item.subject_code: item for item in governed.records}
    comparison = {
        "governed_supported_by_catalog": sorted(governed_codes & catalog_codes),
        "governed_absent_from_catalog": sorted(governed_codes - catalog_codes),
        "catalog_candidates_ungoverned": sorted(catalog_codes - governed_codes),
        "in_catalog_and_schedule": sorted(catalog_codes & schedule_codes),
        "in_catalog_not_schedule": sorted(catalog_codes - schedule_codes) if schedule_codes else [],
        "in_schedule_not_catalog": sorted(schedule_codes - catalog_codes),
        "observed_but_unmapped": sorted(schedule_codes - governed_codes),
        "governed_absent_from_catalog_and_schedule": sorted(governed_codes - catalog_codes - schedule_codes) if schedule_codes else [],
        "historical_or_special_prefix_candidates": sorted((governed_codes & schedule_codes) - catalog_codes),
        "possible_data_quality_issues": sorted(schedule_codes - catalog_codes - governed_codes),
        "exception_candidates": sorted(code for code, item in candidate_by.items() if item.candidate_status == "exception_candidate"),
        "governed_target_matches_catalog": sorted(code for code, item in candidate_by.items() if code in governed_by and item.proposed_analytical_academic_unit_id == governed_by[code].analytical_academic_unit_id),
        "governed_target_differs_from_catalog": sorted(code for code, item in candidate_by.items() if code in governed_by and item.proposed_analytical_academic_unit_id and item.proposed_analytical_academic_unit_id != governed_by[code].analytical_academic_unit_id),
    }
    resolved = sum(item.candidate_status == "high_confidence_candidate" for item in candidates)
    fitness = CatalogOwnershipEvidenceFitness(
        selection.selected.catalog_id if selection.selected else None, selection.confidence,
        round(100 * resolved / len(candidates), 6) if candidates else 0.0,
        sum(item.observed_course_count for item in observations), len(catalog_codes), resolved,
        sum(item.candidate_status == "ambiguous" for item in candidates),
        sum(item.candidate_status == "exception_candidate" for item in candidates),
        sum(len(item.source_sections) > 1 for item in candidates), len(catalog_codes - governed_codes),
        len(governed_codes - catalog_codes), len(schedule_codes - catalog_codes),
        len(catalog_codes - schedule_codes) if schedule_codes else 0,
        {"candidate_crosswalk_generation": "conditionally_suitable", "governed_automatic_promotion": "insufficient", "historical_ownership_inference": "conditional", "workforce_assignment": "conditional_on_governance", "staffing_recommendations": "insufficient"},
    )
    idst_designations = {designation for item in observations if _label(item.section_title) == "interdisciplinary studies" for designation in item.provenance.get("section_program_designations", ())}
    idst_result = "both" if idst_designations == {"major", "minor"} else next(iter(idst_designations)) if len(idst_designations) == 1 else "not_determined_by_catalog_structure"
    semantic = {"selection": selection.to_dict(), "observations": [item.deterministic_fingerprint for item in observations], "candidates": [item.deterministic_candidate_fingerprint for item in candidates], "comparison": comparison, "fitness": fitness.to_dict(), "schedule_subject_inventory": schedule_inventory, "interdisciplinary_studies_program_designation": idst_result, "malformed": list(malformed)}
    review_queue = sorted(
        ({"subject_code": item.subject_code, "candidate_status": item.candidate_status,
          "schedule_offering_count": int((schedule_inventory.get(item.subject_code) or {}).get("offering_count", 0)),
          "schedule_term_count": int((schedule_inventory.get(item.subject_code) or {}).get("term_count", 0)),
          "schedule_distinct_instructor_count": int((schedule_inventory.get(item.subject_code) or {}).get("distinct_instructor_count", 0)),
          "review_recommendation": item.review_recommendation}
         for item in candidates if item.subject_code not in governed_codes or item.candidate_status in {"exception_candidate", "ambiguous", "requires_review", "unsupported"}),
        key=lambda item: (-item["schedule_offering_count"], -item["schedule_term_count"], -item["schedule_distinct_instructor_count"], item["subject_code"]),
    )
    return {**semantic, "catalog_observations": [item.to_dict() for item in observations], "candidates": [item.to_dict() for item in candidates], "comparison": comparison, "review_queue": review_queue, "evidence_fitness": fitness.to_dict(), "interdisciplinary_studies_program_designation": idst_result, "deterministic_report_fingerprint": _fingerprint(semantic)}


def compare_catalog_subject_reports(old: Mapping[str, Any], new: Mapping[str, Any]):
    old_rows = {item["subject_code"]: item for item in old.get("candidates") or ()}
    new_rows = {item["subject_code"]: item for item in new.get("candidates") or ()}
    shared = set(old_rows) & set(new_rows)
    changed = lambda key: sorted(code for code in shared if old_rows[code].get(key) != new_rows[code].get(key))
    result = {
        "new_subjects": sorted(set(new_rows) - set(old_rows)),
        "removed_subjects": sorted(set(old_rows) - set(new_rows)),
        "changed_candidate_status": changed("candidate_status"),
        "changed_proposed_unit": changed("proposed_analytical_academic_unit_id"),
        "changed_evidence_source": changed("source_catalog_id"),
        "changed_candidate_fingerprint": changed("deterministic_candidate_fingerprint"),
        "old_report_fingerprint": old.get("deterministic_report_fingerprint"),
        "new_report_fingerprint": new.get("deterministic_report_fingerprint"),
    }
    result["semantic_changes"] = any(result[key] for key in ("new_subjects", "removed_subjects", "changed_candidate_status", "changed_proposed_unit", "changed_evidence_source", "changed_candidate_fingerprint"))
    return result


__all__ = [name for name in globals() if name.startswith("Catalog") or name.startswith("SubjectOwnershipCandidate") or name in {"build_catalog_subject_report", "compare_catalog_subject_reports"}]
