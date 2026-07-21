from datetime import datetime, timezone
from pathlib import Path

import fitz

from app.adapters.catalog_adapter import (
    AcademicUnitObservation,
    CatalogAdapter,
    CatalogFacultyObservation,
    CatalogObservation,
    DepartmentFacultyRosterObservation,
    write_observations,
)
from app.chunk import chunk_document
from app.knowledge import load_knowledge_object


def _make_catalog(path: Path, year: str, unit: str = "Department of Physics") -> None:
    document = fitz.open()
    pages = [
        f"Christopher Newport University\nUndergraduate Catalog {year}\nVolume 60, August 2025",
        (
            f"{unit}\nDr. Ada Dean, Chair\nFaculty\n"
            "Professor: Jane Exact\nAssociate Professor: Alex Published\n"
            "Mission\nCatalog prose not in the roster."
        ),
        (
            "FACULTY\nNote: The parenthetical date indicates the year of appointment.\n"
            "EXACT, JANE\nProfessor in Physics. Ph.D., Example University (1999)\n"
            "PUBLISHED, ALEX\nAssociate Professor in Physics. M.S., Example University (2012)"
        ),
        "EMERITI FACULTY\nRETIRED, SAMPLE",
    ]
    for text in pages:
        page = document.new_page()
        page.insert_text((72, 72), text, fontsize=10)
    document.set_metadata({"title": f"Undergraduate Catalog {year}"})
    document.save(path)
    document.close()


def test_catalog_parser_rosters_registry_provenance_and_chunks(tmp_path):
    source = tmp_path / "catalogs"
    source.mkdir()
    path = source / "2025-26_catalog.pdf"
    _make_catalog(path, "2025-26")

    stamp = datetime(2026, 7, 20, tzinfo=timezone.utc)
    first = CatalogAdapter(source).adapt(timestamp=stamp)
    second = CatalogAdapter(source).adapt(timestamp=stamp)
    assert not first.failures
    assert [item.id for item in first.observations] == [
        item.id for item in second.observations
    ]

    catalog = next(x for x in first.observations if isinstance(x, CatalogObservation))
    unit = next(x for x in first.observations if isinstance(x, AcademicUnitObservation))
    roster = next(
        x for x in first.observations if isinstance(x, DepartmentFacultyRosterObservation)
    )
    registry = [x for x in first.observations if isinstance(x, CatalogFacultyObservation)]

    assert catalog.catalog_year == "2025-26"
    assert catalog.document_hash == catalog.provenance["source_sha256"]
    assert unit.published_name == "Department of Physics"
    assert unit.published_leadership == ("Dr. Ada Dean, Chair",)
    assert [(x.published_category, x.published_name) for x in roster.entries] == [
        ("Professor", "Jane Exact"),
        ("Associate Professor", "Alex Published"),
    ]
    assert [x.published_name for x in registry] == ["EXACT, JANE", "PUBLISHED, ALEX"]
    assert registry[0].published_title == "Professor"
    assert registry[0].academic_unit == "Physics"
    assert registry[0].appointment_year == "1999"
    assert "Ph.D., Example University" in registry[0].education

    chunks = chunk_document(roster, chunk_size=3000)
    assert len(chunks) == 1
    assert "Professor: Jane Exact" in chunks[0].text
    assert "Mission" not in chunks[0].text
    assert chunks[0].metadata["semantic_space"] == "institutional_academics"
    assert chunks[0].metadata["catalog_year"] == "2025-26"
    assert chunks[0].metadata["academic_unit"] == "Department of Physics"
    assert chunks[0].metadata["page_numbers"] == [2]
    assert chunks[0].id == chunk_document(roster, chunk_size=3000)[0].id

    output = tmp_path / "normalized"
    assert write_observations(first.observations, output) == len(first.observations)
    loaded = load_knowledge_object(
        next((output / "2025-26").glob("department_faculty_roster*.json"))
    )
    assert isinstance(loaded, DepartmentFacultyRosterObservation)
    assert loaded.entries == roster.entries


def test_directory_is_longitudinal_and_one_bad_pdf_does_not_abort(tmp_path):
    source = tmp_path / "catalogs"
    source.mkdir()
    _make_catalog(source / "2024-25_catalog.pdf", "2024-25")
    _make_catalog(source / "2025-26_catalog.pdf", "2025-26")
    (source / "2023-24_broken.pdf").write_bytes(b"not a PDF")

    result = CatalogAdapter(source).adapt()
    assert result.files_discovered == 3
    assert result.files_processed == 2
    assert result.files_failed == 1
    assert {x.catalog_year for x in result.observations} == {"2024-25", "2025-26"}
    assert result.duplicate_observation_ids == 0


def test_repository_catalogs_parse_when_available():
    source = Path("data/acquisition/catalogs")
    if not source.is_dir():
        return
    result = CatalogAdapter(source).adapt()
    assert result.files_discovered == 5
    assert result.files_processed == 5
    assert result.files_failed == 0
    assert result.objects_by_type["catalog_observation"] == 5
    assert result.objects_by_type["department_faculty_roster_observation"] > 0
    assert result.objects_by_type["catalog_faculty_observation"] > 0
    assert result.duplicate_observation_ids == 0
