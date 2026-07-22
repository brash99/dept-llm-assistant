from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path

import fitz
import yaml

from app.catalog_subject_ownership import (
    CatalogCoursePrefixExtractor, CatalogEdition, CatalogEditionSelector,
    CatalogSectionAcademicUnitResolver, CatalogSubjectOwnershipCandidateService,
    CatalogSubjectOwnershipObservation, build_catalog_subject_report,
    compare_catalog_subject_reports,
)
from app.control_plane.catalog import ProgramCatalog
from app.reasoning import AcademicUnitMappingService
from app.subject_ownership import SubjectOwnershipRegistry
from scripts.extract_catalog_subject_ownership import _filtered, parse_args, write_outputs


def _pdf(path, pages):
    document = fitz.open()
    for text in pages:
        page = document.new_page(); page.insert_text((72, 72), text, fontsize=10)
    document.save(path); document.close()


def _edition(path, year="2025-26", kind="undergraduate"):
    return CatalogEdition(f"catalog:{year}:{kind}", f"{kind.title()} Catalog {year}", year, int(year[:4]), 2000 + int(year[-2:]), kind, str(path), "abc")


def _observation(section, subject, codes=("TEST 101",), catalog="catalog:2025-26:undergraduate"):
    semantic = f"{catalog}:{section}:{subject}"
    return CatalogSubjectOwnershipObservation(
        semantic, catalog, "Undergraduate Catalog 2025-26", "2025-26", 2025, 2026,
        "data/acquisition/catalogs/test.pdf", (1,), section, (section,), section,
        subject, tuple(codes), len(codes), "test", 1.0, ("page:1",),
        (f"{codes[0]}. Title",), {"source_sha256": "abc"},
        "2026-07-22T00:00:00+00:00", semantic,
    )


def test_is_is_not_subject_but_information_science_program_remains_sec():
    assert SubjectOwnershipRegistry.load().records_for_subject("IS") == ()
    assert AcademicUnitMappingService().map_subject("IS").status == "unmapped"
    program = ProgramCatalog.from_yaml(Path("config/institutional_programs.yaml")).get("program.information_science")
    assert program is not None
    assert "BSIS" in program.aliases
    assert program.school == "School of Engineering and Computing"
    assert len(SubjectOwnershipRegistry.load().records) == 6
    assert SubjectOwnershipRegistry.load().records_for_subject("PCSE")
    assert all("program" not in record.to_dict() for record in SubjectOwnershipRegistry.load().records)


def test_catalog_selection_uses_year_kind_and_override_not_mtime(tmp_path):
    old = tmp_path / "2024-25-undergraduate_catalog.pdf"; new = tmp_path / "2025-26-undergraduate_catalog.pdf"
    _pdf(old, ["old"]); _pdf(new, ["new"])
    old.touch(); new.touch()
    selector = CatalogEditionSelector(); editions = selector.discover(tmp_path)
    selected = selector.select(editions)
    assert selected.selected.academic_year == "2025-26"
    assert selector.select(editions, override=editions[0].catalog_id).selected == editions[0]
    assert selector.select(editions, kind="graduate").status == "missing"


def test_catalog_selection_exposes_latest_tie(tmp_path):
    _pdf(tmp_path / "2025-26-undergraduate_a.pdf", ["a"])
    _pdf(tmp_path / "2025-26-undergraduate_b.pdf", ["b"])
    result = CatalogEditionSelector().select(CatalogEditionSelector().discover(tmp_path))
    assert result.status == "ambiguous"
    assert result.selected is None


def test_course_prefix_extraction_is_structural_deduplicated_and_deterministic(tmp_path):
    path = tmp_path / "2025-26-undergraduate_catalog.pdf"
    _pdf(path, [
        "Department of Fine Art and Art History\n2025-26\nARTX 101. Introduction (3-3-0)\nARTX 101. Introduction (3-3-0)\nARTX is a program abbreviation.\nBAD 12. Malformed",
        "Department of Fine Art and Art History\n2025-26\nARTX 202. Studio (3-3-0)",
    ])
    edition = _edition(path)
    first, malformed = CatalogCoursePrefixExtractor().extract(edition, created_at="one")
    second, _ = CatalogCoursePrefixExtractor().extract(edition, created_at="two")
    assert len(first) == 1
    assert first[0].observed_course_codes == ("ARTX 101", "ARTX 202")
    assert first[0].deterministic_fingerprint == second[0].deterministic_fingerprint
    assert malformed and malformed[0]["line"].startswith("BAD 12")


def test_interdisciplinary_program_designation_comes_only_from_catalog_heading(tmp_path):
    path = tmp_path / "2025-26-undergraduate_catalog.pdf"
    _pdf(path, ["Interdisciplinary Studies\n2025-2026\nMinor in Film Studies (15 credit hours)\nIDST 205. Introduction (3-3-0)"])
    observations, malformed = CatalogCoursePrefixExtractor().extract(_edition(path), created_at="fixed")
    candidates = CatalogSubjectOwnershipCandidateService().generate(observations, CatalogSectionAcademicUnitResolver())
    selection = CatalogEditionSelector().select((_edition(path),))
    report = build_catalog_subject_report(selection, observations, malformed, candidates, SubjectOwnershipRegistry.load())
    assert report["interdisciplinary_studies_program_designation"] == "minor"


def test_section_resolution_exact_unresolved_and_exceptions():
    resolver = CatalogSectionAcademicUnitResolver()
    direct = resolver.resolve(_observation("Department of Fine Art and Art History", "ARTX"))
    assert direct.status == "resolved"
    assert direct.selected_unit_id == "academic_unit:department_fine_art_art_history"
    assert resolver.resolve(_observation("Unknown Heading", "ZZZZ")).status == "unresolved"
    coll = resolver.resolve(_observation("College Studies", "COLL"))
    assert coll.status == "central_or_interdisciplinary_section"
    assert coll.exception_classification == "service_subject"
    idst = resolver.resolve(_observation("Interdisciplinary Studies", "IDST"))
    assert idst.exception_classification == "interdisciplinary"
    assert idst.selected_unit_id is None
    competing = replace(
        _observation("Department of Fine Art and Art History", "MIXD"),
        section_title_path=("Department of Fine Art and Art History", "Department of Music, Theatre, and Dance"),
    )
    assert resolver.resolve(competing).status == "ambiguous"


def test_candidate_generation_distinguishes_normal_sec_exception_and_conflict():
    resolver = CatalogSectionAcademicUnitResolver()
    observations = (
        _observation("Department of Fine Art and Art History", "ARTX"),
        _observation("Physics, Computer Science and Engineering", "CPSC"),
        _observation("College Studies", "COLL"),
        _observation("Interdisciplinary Studies", "IDST"),
        _observation("Unknown Heading", "ZZZZ"),
    )
    candidates = {x.subject_code: x for x in CatalogSubjectOwnershipCandidateService().generate(observations, resolver)}
    assert candidates["ARTX"].candidate_status == "high_confidence_candidate"
    assert candidates["CPSC"].proposed_analytical_academic_unit_id == "academic_unit:sec"
    assert candidates["CPSC"].proposed_mapping_status == "intentionally_grouped_department_equivalent"
    assert candidates["COLL"].candidate_status == "exception_candidate"
    assert candidates["COLL"].proposed_relationship_type == "centrally_administered_subject"
    assert candidates["IDST"].proposed_relationship_type == "interdisciplinary_subject"
    assert candidates["ZZZZ"].candidate_status == "requires_review"


def test_multi_section_prefix_is_ambiguous_when_units_compete():
    resolver = CatalogSectionAcademicUnitResolver()
    values = (
        _observation("Department of Fine Art and Art History", "SHRD"),
        _observation("Department of Music, Theatre, and Dance", "SHRD"),
    )
    result = CatalogSubjectOwnershipCandidateService().generate(values, resolver)[0]
    assert result.candidate_status == "ambiguous"
    assert "prefix_appears_under_multiple_academic_units" in result.conflicts


def test_candidate_compares_catalog_target_with_governed_registry():
    governed = SubjectOwnershipRegistry.load()
    supported = CatalogSubjectOwnershipCandidateService().generate(
        (_observation("School of Engineering and Computing", "CPSC"),),
        CatalogSectionAcademicUnitResolver(), governed,
    )[0]
    assert supported.candidate_status == "high_confidence_candidate"
    assert "supports the existing governed record" in supported.review_recommendation
    conflicting = CatalogSubjectOwnershipCandidateService().generate(
        (_observation("Department of Fine Art and Art History", "CPSC"),),
        CatalogSectionAcademicUnitResolver(), governed,
    )[0]
    assert conflicting.candidate_status == "requires_review"
    assert "catalog_candidate_differs_from_governed_target" in conflicting.conflicts


def test_report_keeps_historical_governed_absence_and_three_way_comparison():
    selection = type("Selection", (), {"selected": _edition(Path("x.pdf")), "confidence": 1.0,
        "to_dict": lambda self: {"status": "selected", "selected": self.selected.to_dict(), "candidates": [self.selected.to_dict()], "confidence": 1.0, "rationale": "test"}})()
    observations = (_observation("Department of Fine Art and Art History", "ARTX"),)
    candidates = CatalogSubjectOwnershipCandidateService().generate(observations, CatalogSectionAcademicUnitResolver())
    report = build_catalog_subject_report(selection, observations, (), candidates, SubjectOwnershipRegistry.load(), ("ARTX", "PCSE", "COLL"))
    assert "PCSE" in report["comparison"]["governed_absent_from_catalog"]
    assert "PCSE" in report["comparison"]["in_schedule_not_catalog"]
    assert "ARTX" in report["comparison"]["catalog_candidates_ungoverned"]
    assert report["evidence_fitness"]["suitability"]["governed_automatic_promotion"] == "insufficient"
    assert report["evidence_fitness"]["suitability"]["staffing_recommendations"] == "insufficient"


def test_report_outputs_and_filters_never_write_governed_registry(tmp_path):
    selection = type("Selection", (), {"selected": _edition(Path("x.pdf")), "confidence": 1.0,
        "to_dict": lambda self: {"status": "selected", "selected": self.selected.to_dict(), "candidates": [self.selected.to_dict()], "confidence": 1.0, "rationale": "test"}})()
    observations = (_observation("College Studies", "COLL"), _observation("Unknown", "ZZZZ"))
    candidates = CatalogSubjectOwnershipCandidateService().generate(observations, CatalogSectionAcademicUnitResolver())
    report = build_catalog_subject_report(selection, observations, (), candidates, SubjectOwnershipRegistry.load())
    args = parse_args(["--exceptions-only"]); rows = _filtered(report, args)
    assert [x["subject_code"] for x in rows] == ["COLL"]
    write_outputs(report, rows, tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == {"catalog_subject_ownership.json", "catalog_subject_candidates.csv", "catalog_subject_ownership.md", "catalog_subject_candidates.review.yaml", "catalog_subject_review_queue.csv"}
    review = yaml.safe_load((tmp_path / "catalog_subject_candidates.review.yaml").read_text())
    assert review["candidates"][0]["review_status"] == "requires_review"
    assert not hasattr(parse_args([]), "write_governed_registry")


def test_catalog_report_comparison_is_timestamp_independent():
    candidate = CatalogSubjectOwnershipCandidateService().generate(
        (_observation("Department of Fine Art and Art History", "ARTX"),),
        CatalogSectionAcademicUnitResolver(),
    )[0].to_dict()
    old = {"candidates": [candidate], "deterministic_report_fingerprint": "same", "created_at": "old"}
    new = {"candidates": [candidate], "deterministic_report_fingerprint": "same", "created_at": "new"}
    assert compare_catalog_subject_reports(old, new)["semantic_changes"] is False
    changed = {**candidate, "candidate_status": "requires_review"}
    result = compare_catalog_subject_reports(old, {"candidates": [changed], "deterministic_report_fingerprint": "new"})
    assert result["changed_candidate_status"] == ["ARTX"]
    assert result["semantic_changes"] is True
