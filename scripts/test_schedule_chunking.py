from dataclasses import asdict
from pathlib import Path

from app.adapters.schedule_adapter import CourseOfferingObservation
from app.chunk import chunk_document, run_chunking
from app.constitution.objects import ConstitutionalKnowledgeObject
from app.knowledge import Document, save_knowledge_object


def _observation(**overrides) -> CourseOfferingObservation:
    values = {
        "id": "schedule-observation-1",
        "object_type": "course_offering_observation",
        "title": "Course Offering: PHY 201 Section 01 (2026_fall)",
        "text": "Legacy adapter projection must not control schedule chunking.",
        "metadata": {"semantic_layer": "course_offering_observation"},
        "source": {
            "kind": "institutional_schedule_csv",
            "path": "data/acquisition/schedules/2026_fall.csv",
            "row": 2,
        },
        "normalized_at": "2026-07-20T12:30:00+00:00",
        "observation_id": "schedule-observation-1",
        "source_file": "2026_fall.csv",
        "source_row": 2,
        "academic_term": "2026_fall",
        "subject": "PHY",
        "course_number": "201",
        "course_code": "PHY 201",
        "course_title": "University Physics",
        "section": "01",
        "crn": "12345",
        "credits": 4,
        "credits_raw": "1-4",
        "instructor_name": "Doe, Jane  ",
        "instructor_raw": "Doe, Jane  ",
        "instructional_method": "Lecture",
        "modality": "In Person",
        "meeting_days": "MWF",
        "meeting_time_raw": "0800-0850; 1400-1500",
        "meeting_date_range_raw": "08/24/2026-12/05/2026",
        "location_raw": "FORBES 2070C; LUTC 121",
        "enrollment": 22,
        "capacity": 24,
        "seats_available": 2,
        "llc_area_raw": "Investigating the Natural World",
        "provenance": {
            "source_path": "data/acquisition/schedules/2026_fall.csv",
            "source_row": 2,
            "source_sha256": "a" * 64,
            "adapter": "schedule_csv_adapter",
            "adapter_version": "0.1",
        },
        "raw_record": {"private_raw_marker": "must-not-be-embedded"},
    }
    values.update(overrides)
    return CourseOfferingObservation(**values)


def test_complete_schedule_observation_has_one_deterministic_chunk() -> None:
    observation = _observation()

    first = chunk_document(observation)
    second = chunk_document(observation, chunk_size=10, overlap=9)

    assert len(first) == 1
    assert [asdict(chunk) for chunk in first] == [asdict(chunk) for chunk in second]
    chunk = first[0]
    assert chunk.text == (
        "Scheduled course offering for 2026_fall.\n"
        "Course: PHY 201 — University Physics.\n"
        "Section: 01.\n"
        "CRN: 12345.\n"
        "Credits: 1-4.\n"
        "Instructor: Doe, Jane  .\n"
        "Instructional method: Lecture.\n"
        "Modality: In Person.\n"
        "Meeting days: MWF.\n"
        "Meeting time: 0800-0850; 1400-1500.\n"
        "Meeting date range: 08/24/2026-12/05/2026.\n"
        "Location: FORBES 2070C; LUTC 121.\n"
        "Enrollment: 22.\n"
        "Capacity: 24.\n"
        "Seats available: 2.\n"
        "Liberal Learning Core designation: Investigating the Natural World."
    )
    assert "must-not-be-embedded" not in chunk.text
    assert chunk.metadata["instructor_text"] == "Doe, Jane  "
    assert chunk.metadata["semantic_space"] == "institutional_operations"
    assert chunk.metadata["knowledge_object_id"] == observation.id
    assert chunk.metadata["knowledge_object_type"] == observation.object_type
    assert chunk.metadata["source_sha256"] == "a" * 64


def test_sparse_schedule_observation_omits_missing_fields() -> None:
    observation = _observation(
        course_title=None,
        crn=None,
        credits=None,
        credits_raw=None,
        instructor_name=None,
        instructor_raw=None,
        instructional_method=None,
        modality=None,
        meeting_days=None,
        meeting_time_raw=None,
        meeting_date_range_raw=None,
        location_raw=None,
        enrollment=None,
        capacity=None,
        seats_available=None,
        llc_area_raw=None,
    )

    chunk = chunk_document(observation)[0]

    assert chunk.text == (
        "Scheduled course offering for 2026_fall.\n"
        "Course: PHY 201.\n"
        "Section: 01."
    )
    assert "instructor_text" not in chunk.metadata
    assert "crn" not in chunk.metadata


def test_recursive_run_chunking_preserves_other_object_types(tmp_path: Path) -> None:
    normalized = tmp_path / "normalized"
    chunks = tmp_path / "chunks"
    schedule_dir = normalized / "schedules" / "2026_fall"
    schedule_dir.mkdir(parents=True)
    save_knowledge_object(_observation(), schedule_dir / "offering.json")

    document = Document(
        id="document-1",
        object_type="document",
        title="Institutional report",
        text="A factual institutional report.",
    )
    save_knowledge_object(document, normalized / "document.json")

    constitutional = ConstitutionalKnowledgeObject(
        id="constitutional-1",
        object_type="constitutional_knowledge",
        title="Mission",
        text="An institutional mission statement.",
        metadata={"semantic_space": "constitutional"},
        constitutional_type="mission",
    )
    save_knowledge_object(constitutional, normalized / "constitution.json")

    result = run_chunking(source_dirs=[normalized], chunks_dir=chunks)

    assert result["attempted"] == 3
    assert result["succeeded"] == 3
    assert result["failed"] == 0
    assert result["total_chunks"] == 3
    assert result["documents_by_object_type"] == {
        "constitutional_knowledge": 1,
        "document": 1,
        "course_offering_observation": 1,
    }
    assert len(list(chunks.glob("*.json"))) == 3


def test_scalar_credits_are_rendered_when_raw_value_is_unavailable() -> None:
    chunk = chunk_document(_observation(credits=3, credits_raw=None))[0]

    assert "Credits: 3." in chunk.text
