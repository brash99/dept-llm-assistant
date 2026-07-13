from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.acquisition import (
    AcquisitionManifest,
    AcquisitionMethod,
    AcquisitionStatus,
    SourceAuthority,
    SourceDocument,
)


BASE_TIME = datetime(
    2026,
    7,
    13,
    20,
    0,
    tzinfo=timezone.utc,
)


def make_document(
    *,
    relative_path: str,
    content_hash: str,
    acquired_at: datetime = BASE_TIME,
    title: str = "Example Document",
) -> SourceDocument:
    return SourceDocument(
        id=f"sha256:{content_hash}",
        title=title,
        source_organization="Christopher Newport University",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=AcquisitionMethod.FILESYSTEM_IMPORT,
        relative_path=relative_path,
        content_hash=content_hash,
        acquired_at=acquired_at,
        media_type="application/pdf",
    )


def test_missing_manifest_reads_as_empty(tmp_path):
    manifest = AcquisitionManifest(
        tmp_path / "manifest.jsonl"
    )

    assert manifest.read_all() == []
    assert manifest.latest_documents() == []


def test_new_document_is_classified_and_recorded(tmp_path):
    manifest = AcquisitionManifest(
        tmp_path / "manifest.jsonl"
    )

    document = make_document(
        relative_path="reports/enrollment.pdf",
        content_hash="aaa111",
    )

    decision = manifest.record(document)

    assert decision.status is AcquisitionStatus.NEW
    assert decision.previous_document is None
    assert decision.duplicate_documents == ()
    assert manifest.read_all() == [document]


def test_unchanged_document_is_not_appended(tmp_path):
    manifest = AcquisitionManifest(
        tmp_path / "manifest.jsonl"
    )

    first = make_document(
        relative_path="reports/enrollment.pdf",
        content_hash="aaa111",
    )

    second = make_document(
        relative_path="reports/enrollment.pdf",
        content_hash="aaa111",
        acquired_at=BASE_TIME + timedelta(hours=1),
    )

    manifest.record(first)
    decision = manifest.record(second)

    assert decision.status is AcquisitionStatus.UNCHANGED
    assert decision.previous_document == first
    assert decision.should_append is False
    assert manifest.read_all() == [first]


def test_changed_document_is_appended_as_new_version(tmp_path):
    manifest = AcquisitionManifest(
        tmp_path / "manifest.jsonl"
    )

    first = make_document(
        relative_path="reports/enrollment.pdf",
        content_hash="aaa111",
    )

    second = make_document(
        relative_path="reports/enrollment.pdf",
        content_hash="bbb222",
        acquired_at=BASE_TIME + timedelta(days=1),
    )

    manifest.record(first)
    decision = manifest.record(second)

    assert decision.status is AcquisitionStatus.CHANGED
    assert decision.previous_document == first
    assert decision.should_append is True
    assert manifest.read_all() == [first, second]
    assert manifest.latest_documents() == [second]


def test_same_content_at_different_path_is_duplicate_content(
    tmp_path,
):
    manifest = AcquisitionManifest(
        tmp_path / "manifest.jsonl"
    )

    first = make_document(
        relative_path="reports/enrollment.pdf",
        content_hash="aaa111",
    )

    duplicate = make_document(
        relative_path="archive/enrollment-copy.pdf",
        content_hash="aaa111",
        acquired_at=BASE_TIME + timedelta(hours=1),
    )

    manifest.record(first)
    decision = manifest.record(duplicate)

    assert (
        decision.status
        is AcquisitionStatus.DUPLICATE_CONTENT
    )
    assert decision.previous_document is None
    assert decision.duplicate_documents == (first,)
    assert manifest.read_all() == [first, duplicate]


def test_latest_documents_returns_one_version_per_path(
    tmp_path,
):
    manifest = AcquisitionManifest(
        tmp_path / "manifest.jsonl"
    )

    first_old = make_document(
        relative_path="a/report.pdf",
        content_hash="old111",
    )

    second = make_document(
        relative_path="b/report.pdf",
        content_hash="bbb222",
    )

    first_new = make_document(
        relative_path="a/report.pdf",
        content_hash="new333",
        acquired_at=BASE_TIME + timedelta(days=1),
    )

    manifest.append(first_old)
    manifest.append(second)
    manifest.append(first_new)

    latest = manifest.latest_documents()

    assert latest == [
        first_new,
        second,
    ]


def test_manifest_is_valid_jsonl(tmp_path):
    manifest_path = tmp_path / "manifest.jsonl"
    manifest = AcquisitionManifest(manifest_path)

    first = make_document(
        relative_path="a/report.pdf",
        content_hash="aaa111",
    )

    second = make_document(
        relative_path="b/report.pdf",
        content_hash="bbb222",
    )

    manifest.append(first)
    manifest.append(second)

    lines = manifest_path.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 2
    assert '"relative_path": "a/report.pdf"' in lines[0]
    assert '"relative_path": "b/report.pdf"' in lines[1]


def test_invalid_manifest_record_reports_line_number(
    tmp_path,
):
    manifest_path = tmp_path / "manifest.jsonl"

    manifest_path.write_text(
        '{"valid": "json but not a SourceDocument"}\n'
        'not valid json\n',
        encoding="utf-8",
    )

    manifest = AcquisitionManifest(manifest_path)

    with pytest.raises(
        ValueError,
        match=r"manifest\.jsonl:1",
    ):
        manifest.read_all()


def test_blank_manifest_lines_are_ignored(tmp_path):
    manifest_path = tmp_path / "manifest.jsonl"

    document = make_document(
        relative_path="reports/example.pdf",
        content_hash="aaa111",
    )

    manifest_path.write_text(
        "\n"
        + __import__("json").dumps(document.to_dict())
        + "\n\n",
        encoding="utf-8",
    )

    manifest = AcquisitionManifest(manifest_path)

    assert manifest.read_all() == [document]
