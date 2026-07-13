from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone

import pytest

from app.acquisition import (
    AcquisitionMethod,
    SourceAuthority,
    SourceDocument,
)


def make_document() -> SourceDocument:
    return SourceDocument(
        id="sha256:abc123",
        title="CNU Strategic Plan",
        source_organization="Christopher Newport University",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=AcquisitionMethod.WEB_CRAWL,
        relative_path="web/cnu/strategic-plan.pdf",
        source_url="https://example.cnu.edu/strategic-plan.pdf",
        publication_date=date(2025, 7, 1),
        acquired_at=datetime(
            2026,
            7,
            13,
            19,
            0,
            tzinfo=timezone.utc,
        ),
        content_hash="abc123",
        media_type="application/pdf",
    )


def test_source_document_preserves_provenance_facts():
    document = make_document()

    assert document.title == "CNU Strategic Plan"
    assert (
        document.source_organization
        == "Christopher Newport University"
    )
    assert (
        document.authority
        is SourceAuthority.INSTITUTIONAL_PRIMARY
    )
    assert (
        document.acquisition_method
        is AcquisitionMethod.WEB_CRAWL
    )
    assert (
        document.relative_path
        == "web/cnu/strategic-plan.pdf"
    )
    assert document.content_hash == "abc123"


def test_source_document_is_immutable():
    document = make_document()

    with pytest.raises(FrozenInstanceError):
        document.title = "Changed title"


def test_source_document_round_trip_is_lossless():
    original = make_document()

    restored = SourceDocument.from_dict(original.to_dict())

    assert restored == original


def test_manifest_representation_is_json_compatible():
    payload = make_document().to_dict()

    assert payload["authority"] == "institutional_primary"
    assert payload["acquisition_method"] == "web_crawl"
    assert payload["publication_date"] == "2025-07-01"
    assert payload["acquired_at"] == "2026-07-13T19:00:00+00:00"


def test_relative_path_must_not_be_absolute():
    with pytest.raises(
        ValueError,
        match="relative_path must be relative",
    ):
        SourceDocument(
            id="sha256:abc123",
            title="Invalid path example",
            source_organization="Christopher Newport University",
            authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
            acquisition_method=AcquisitionMethod.FILESYSTEM_IMPORT,
            relative_path="/tmp/document.pdf",
            content_hash="abc123",
            acquired_at=datetime.now(timezone.utc),
        )


def test_acquired_at_must_be_timezone_aware():
    with pytest.raises(
        ValueError,
        match="acquired_at must be timezone-aware",
    ):
        SourceDocument(
            id="sha256:abc123",
            title="Naive timestamp example",
            source_organization="Christopher Newport University",
            authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
            acquisition_method=AcquisitionMethod.FILESYSTEM_IMPORT,
            relative_path="documents/example.pdf",
            content_hash="abc123",
            acquired_at=datetime(2026, 7, 13, 19, 0),
        )


@pytest.mark.parametrize(
    "field_name, replacement, expected_message",
    [
        ("id", "", "id must not be empty"),
        ("title", "   ", "title must not be empty"),
        (
            "source_organization",
            "",
            "source_organization must not be empty",
        ),
        (
            "relative_path",
            "",
            "relative_path must not be empty",
        ),
        (
            "content_hash",
            "",
            "content_hash must not be empty",
        ),
    ],
)
def test_required_string_fields_are_validated(
    field_name,
    replacement,
    expected_message,
):
    payload = make_document().to_dict()
    payload[field_name] = replacement

    with pytest.raises(ValueError, match=expected_message):
        SourceDocument.from_dict(payload)


def test_acquired_now_uses_timezone_aware_utc_timestamp():
    document = SourceDocument.acquired_now(
        id="sha256:def456",
        title="Faculty Senate Minutes",
        source_organization="CNU Faculty Senate",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=AcquisitionMethod.GOOGLE_DRIVE_SYNC,
        relative_path="drive/faculty-senate/minutes.pdf",
        content_hash="def456",
        media_type="application/pdf",
    )

    assert document.acquired_at.tzinfo is not None
    assert document.acquired_at.utcoffset().total_seconds() == 0
