from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from app.adapters.faculty_adapter import (
    FacultyDirectoryAdapter,
    FacultyObservation,
    write_observations,
)
from app.chunk import chunk_document, run_chunking
from app.constitution.objects import ConstitutionalKnowledgeObject
from app.knowledge import load_knowledge_object, save_knowledge_object


FIXED_TIME = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)


def _profile_html(*, sparse: bool = False, unknown_section: bool = False) -> str:
    optional = "" if sparse else """
      <a class="phone" href="tel:7575940000"> (757) 594-0000 </a>
      <p> Luter Hall   200 </p>
      <ul class="inline-list">
        <li><a href="https://cnu.edu/academics/areasofstudy/naturalandbehavioralsciences/"> College of Natural and Behavioral Sciences </a></li>
        <li><a href="https://cnu.edu/academics/departments/physics/"> Department of Physics </a></li>
      </ul>
    """
    narratives = "" if sparse else """
      <div class="bio"><h2>Biography</h2>
        <div class="education"><h3>Education</h3><ul class="degrees">
          <li> Ph D   in Physics, Example University </li>
          <li> BS in Physics, Another University </li>
        </ul></div>
        <p>Studies particles and instrumentation.</p>
      </div>
      <div class="disciplines">
        <div class="teaching"><h2>Teaching</h2><p>Physics laboratories</p></div>
        <div class="research"><h2>Research</h2><p>Detector physics</p></div>
      </div>
    """
    accomplishments = "" if not unknown_section else """
      <div class="accomplishments"><h2>Selected Accomplishments</h2>
        <button class="accordion-button" data-bs-target="#publications">Publications</button>
        <div id="publications"><ul class="facultyData"><li>Published factual work</li></ul></div>
        <button class="accordion-button" data-bs-target="#grants">Grants and Sponsored Research</button>
        <div id="grants"><ul class="facultyData"><li>Grant description</li></ul></div>
      </div>
    """
    education = (
        "<div class='education'><h2>Education</h2><ul class='degrees'></ul></div>"
        if sparse
        else ""
    )
    return f"""<!doctype html><html><head>
      <meta property="og:url" content="https://cnu.edu/faculty/janedoe.html">
      <title>Jane Doe | Christopher Newport University</title></head><body>
      <nav>UNRELATED NAVIGATION CHROME</nav>
      <section class="component-faculty-page"><div class="profile">
        <div class="contact-info">
          <h2 class="name"> Jane   Doe </h2>
          <p class="job"> Professor of Physics <br> Program Director </p>
          <a class="email" href="mailto:jane.doe@cnu.edu"> jane.doe@cnu.edu </a>
          {optional}
        </div></div>
        {education}{narratives}{accomplishments}
      </section>
      <footer>UNRELATED FOOTER CHROME faculty@cnu.edu</footer>
    </body></html>"""


def _snapshot(tmp_path: Path, html_values: list[str]) -> Path:
    snapshot = tmp_path / "2026-07-21"
    snapshot.mkdir()
    records = []
    for index, html in enumerate(html_values, start=1):
        filename = f"faculty_profile{index}.html"
        path = snapshot / filename
        path.write_text(html, encoding="utf-8")
        records.append(
            {
                "crawl_timestamp": "2026-07-21T01:50:40+00:00",
                "original_url": f"https://cnu.edu/faculty/profile{index}.html",
                "saved_filename": filename,
                "http_status": 200,
                "content_length": len(html.encode("utf-8")),
                "sha256_hash": hashlib.sha256(html.encode("utf-8")).hexdigest(),
            }
        )
    (snapshot / "faculty_index.html").write_text(
        "<html>directory index</html>", encoding="utf-8"
    )
    (snapshot / "manifest.json").write_text(json.dumps(records), encoding="utf-8")
    return snapshot


def test_dominant_profile_preserves_factual_fields_and_unknown_labels(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(tmp_path, [_profile_html(unknown_section=True)])

    result = FacultyDirectoryAdapter(snapshot).adapt(timestamp=FIXED_TIME)

    assert result.files_discovered == 1
    assert result.objects_created == 1
    assert not result.failures
    observation = result.observations[0]
    assert observation.display_name == "Jane Doe"
    assert observation.published_titles == (
        "Professor of Physics",
        "Program Director",
    )
    assert observation.published_department == "Department of Physics"
    assert observation.published_college == (
        "College of Natural and Behavioral Sciences"
    )
    assert observation.email == "jane.doe@cnu.edu"
    assert observation.phone == "(757) 594-0000"
    assert observation.office == "Luter Hall 200"
    assert observation.education_entries == (
        "Ph D in Physics, Example University",
        "BS in Physics, Another University",
    )
    assert observation.biography == "Studies particles and instrumentation."
    assert observation.teaching_interests == "Physics laboratories"
    assert observation.research_interests == "Detector physics"
    assert observation.publications == ("Published factual work",)
    assert observation.other_labeled_sections == {
        "Grants and Sponsored Research": ("Grant description",)
    }
    assert observation.original_labeled_fields["Publications"] == (
        "Published factual work",
    )
    assert result.unknown_labels == {"Grants and Sponsored Research": 1}


def test_sparse_variant_omits_missing_fields_and_does_not_infer(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path, [_profile_html(sparse=True)])
    observation = FacultyDirectoryAdapter(snapshot).adapt(
        timestamp=FIXED_TIME
    ).observations[0]

    assert observation.display_name == "Jane Doe"
    assert observation.family_name is None
    assert observation.given_name is None
    assert observation.published_department is None
    assert observation.published_college is None
    assert observation.office is None
    assert observation.biography is None
    assert not hasattr(observation, "employment_category")


def test_ids_are_snapshot_deterministic_and_objects_round_trip(tmp_path: Path) -> None:
    snapshot = _snapshot(tmp_path, [_profile_html()])
    adapter = FacultyDirectoryAdapter(snapshot)
    first = adapter.adapt(timestamp=FIXED_TIME).observations[0]
    second = adapter.adapt(
        timestamp=datetime(2026, 7, 22, tzinfo=timezone.utc)
    ).observations[0]

    assert first.id == second.id
    output = tmp_path / "normalized"
    assert write_observations([first], output) == 1
    loaded = load_knowledge_object(next(output.glob("faculty_observation_*.json")))
    assert isinstance(loaded, FacultyObservation)
    assert loaded.to_dict() == first.to_dict()


def test_faculty_chunk_is_deterministic_and_excludes_html_chrome(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(tmp_path, [_profile_html(unknown_section=True)])
    observation = FacultyDirectoryAdapter(snapshot).adapt(
        timestamp=FIXED_TIME
    ).observations[0]

    first = chunk_document(observation, chunk_size=10000, overlap=200)
    second = chunk_document(observation, chunk_size=10000, overlap=200)

    assert [asdict(chunk) for chunk in first] == [asdict(chunk) for chunk in second]
    assert len(first) == 1
    chunk = first[0]
    assert "Name: Jane Doe" in chunk.text
    assert "Published title: Professor of Physics; Program Director" in chunk.text
    assert "UNRELATED NAVIGATION CHROME" not in chunk.text
    assert "UNRELATED FOOTER CHROME" not in chunk.text
    assert "<section" not in chunk.text
    assert chunk.metadata["semantic_space"] == "institutional_people"
    assert chunk.metadata["display_name"] == "Jane Doe"
    assert chunk.metadata["published_department"] == "Department of Physics"
    assert chunk.metadata["email"] == "jane.doe@cnu.edu"
    assert chunk.metadata["source_sha256"] == observation.raw_acquisition_hash


def test_recursive_discovery_preserves_schedule_and_constitutional_chunking(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(tmp_path, [_profile_html(sparse=True)])
    faculty = FacultyDirectoryAdapter(snapshot).adapt(
        timestamp=FIXED_TIME
    ).observations[0]
    source = tmp_path / "normalized"
    faculty_dir = source / "faculty" / "2026-07-21"
    faculty_dir.mkdir(parents=True)
    save_knowledge_object(faculty, faculty_dir / "faculty.json")

    constitutional = ConstitutionalKnowledgeObject(
        id="constitution-1",
        object_type="constitutional_knowledge",
        title="Mission",
        text="Institutional mission evidence.",
        metadata={"semantic_space": "constitutional"},
        constitutional_type="mission",
    )
    save_knowledge_object(constitutional, source / "constitution.json")

    output = tmp_path / "chunks"
    result = run_chunking(source_dirs=[source], chunks_dir=output)

    assert result["attempted"] == 2
    assert result["succeeded"] == 2
    assert result["failed"] == 0
    assert result["documents_by_object_type"] == {
        "constitutional_knowledge": 1,
        "faculty_observation": 1,
    }


def test_full_snapshot_adapts_one_object_per_profile_when_available() -> None:
    snapshot = Path("data/acquisition/faculty/raw/2026-07-21")
    if not snapshot.is_dir():
        pytest.skip("acquired faculty snapshot is not present")

    result = FacultyDirectoryAdapter(snapshot).adapt(timestamp=FIXED_TIME)

    assert result.files_discovered == 301
    assert result.objects_created == 301
    assert result.skipped_files == 0
    assert result.failures == []
    assert result.duplicate_observation_ids == 0
    assert len({item.id for item in result.observations}) == 301
    chunks = [
        chunk
        for observation in result.observations
        for chunk in chunk_document(observation, chunk_size=1000, overlap=200)
    ]
    assert all(chunks)
    assert {chunk.knowledge_object_id for chunk in chunks} == {
        item.id for item in result.observations
    }
    assert len({chunk.id for chunk in chunks}) == len(chunks)
