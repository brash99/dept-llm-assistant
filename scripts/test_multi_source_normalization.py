from pathlib import Path

from app.knowledge import load_knowledge_object
from app.normalize import normalize_source_roots


def test_multiple_sources_receive_qualified_paths(
    tmp_path,
):
    raw_web = tmp_path / "raw_web"
    raw_drive = tmp_path / "raw_drive"
    normalized = tmp_path / "normalized"

    raw_web.mkdir()
    raw_drive.mkdir()

    web_file = raw_web / "same-name.txt"
    drive_file = raw_drive / "other-name.txt"

    web_file.write_text(
        "public website observation",
        encoding="utf-8",
    )

    drive_file.write_text(
        "internal drive observation",
        encoding="utf-8",
    )

    results = normalize_source_roots(
        sources=[
            {
                "key": "cnu_website",
                "root": raw_web,
            },
            {
                "key": "sec_google_drive",
                "root": raw_drive,
            },
        ],
        normalized_dir=normalized,
    )

    assert results["succeeded"] == 2

    documents = [
        load_knowledge_object(path)
        for path in normalized.glob("*.json")
    ]

    relative_paths = {
        document.relative_path
        for document in documents
    }

    assert relative_paths == {
        "cnu_website/same-name.txt",
        "sec_google_drive/other-name.txt",
    }

    for document in documents:
        assert document.metadata["source_key"] in {
            "cnu_website",
            "sec_google_drive",
        }

        assert document.source["source_key"] in {
            "cnu_website",
            "sec_google_drive",
        }


def test_duplicate_content_is_deduplicated_across_sources(
    tmp_path,
):
    raw_web = tmp_path / "raw_web"
    raw_drive = tmp_path / "raw_drive"
    normalized = tmp_path / "normalized"

    raw_web.mkdir()
    raw_drive.mkdir()

    content = "identical institutional observation"

    (raw_web / "public.txt").write_text(
        content,
        encoding="utf-8",
    )

    (raw_drive / "internal.txt").write_text(
        content,
        encoding="utf-8",
    )

    results = normalize_source_roots(
        sources=[
            {
                "key": "cnu_website",
                "root": raw_web,
            },
            {
                "key": "sec_google_drive",
                "root": raw_drive,
            },
        ],
        normalized_dir=normalized,
    )

    assert results["succeeded"] == 1
    assert (
        results["skipped_duplicate_content"]
        == 1
    )

    document_path = next(
        normalized.glob("*.json")
    )

    document = load_knowledge_object(
        document_path
    )

    assert document.relative_path == (
        "cnu_website/public.txt"
    )
