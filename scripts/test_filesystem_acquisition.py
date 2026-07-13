import hashlib
from datetime import date
from pathlib import Path

import pytest

from app.acquisition import (
    AcquisitionMethod,
    FilesystemAcquisitionService,
    SourceAuthority,
)


def test_acquire_creates_source_document(tmp_path):
    source_file = tmp_path / "reports" / "enrollment.txt"
    source_file.parent.mkdir()
    source_file.write_text(
        "Fall enrollment: 4,500\n",
        encoding="utf-8",
    )

    service = FilesystemAcquisitionService(tmp_path)

    document = service.acquire(
        source_file=source_file,
        title="Fall Enrollment Report",
        source_organization="CNU Institutional Research",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=AcquisitionMethod.FILESYSTEM_IMPORT,
        source_url="https://example.cnu.edu/enrollment",
        publication_date=date(2026, 7, 1),
    )

    expected_hash = hashlib.sha256(
        source_file.read_bytes()
    ).hexdigest()

    assert document.id == f"sha256:{expected_hash}"
    assert document.content_hash == expected_hash
    assert document.relative_path == "reports/enrollment.txt"
    assert document.media_type == "text/plain"
    assert document.title == "Fall Enrollment Report"
    assert (
        document.source_organization
        == "CNU Institutional Research"
    )
    assert (
        document.authority
        is SourceAuthority.INSTITUTIONAL_PRIMARY
    )
    assert (
        document.acquisition_method
        is AcquisitionMethod.FILESYSTEM_IMPORT
    )
    assert document.source_url == (
        "https://example.cnu.edu/enrollment"
    )
    assert document.publication_date == date(2026, 7, 1)


def test_same_bytes_produce_same_identity(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "nested" / "second.pdf"

    second.parent.mkdir()

    content = b"identical institutional evidence"
    first.write_bytes(content)
    second.write_bytes(content)

    service = FilesystemAcquisitionService(tmp_path)

    first_document = service.acquire(
        source_file=first,
        title="First copy",
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=AcquisitionMethod.FILESYSTEM_IMPORT,
    )

    second_document = service.acquire(
        source_file=second,
        title="Second copy",
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=AcquisitionMethod.FILESYSTEM_IMPORT,
    )

    assert first_document.id == second_document.id
    assert (
        first_document.content_hash
        == second_document.content_hash
    )
    assert (
        first_document.relative_path
        != second_document.relative_path
    )


def test_changed_bytes_produce_new_identity(tmp_path):
    source_file = tmp_path / "report.txt"
    service = FilesystemAcquisitionService(tmp_path)

    source_file.write_text("version one", encoding="utf-8")

    first_document = service.acquire(
        source_file=source_file,
        title="Report",
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=AcquisitionMethod.FILESYSTEM_IMPORT,
    )

    source_file.write_text("version two", encoding="utf-8")

    second_document = service.acquire(
        source_file=source_file,
        title="Report",
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=AcquisitionMethod.FILESYSTEM_IMPORT,
    )

    assert first_document.id != second_document.id
    assert (
        first_document.content_hash
        != second_document.content_hash
    )


def test_explicit_media_type_overrides_detection(tmp_path):
    source_file = tmp_path / "document.unknown"
    source_file.write_bytes(b"example")

    service = FilesystemAcquisitionService(tmp_path)

    document = service.acquire(
        source_file=source_file,
        title="Unknown-format document",
        source_organization="CNU",
        authority=SourceAuthority.USER_SUPPLIED,
        acquisition_method=AcquisitionMethod.MANUAL_UPLOAD,
        media_type="application/x-cnu-example",
    )

    assert document.media_type == "application/x-cnu-example"


def test_unknown_extension_uses_binary_media_type(tmp_path):
    source_file = tmp_path / "document.unknown-extension"
    source_file.write_bytes(b"example")

    service = FilesystemAcquisitionService(tmp_path)

    document = service.acquire(
        source_file=source_file,
        title="Unknown-format document",
        source_organization="CNU",
        authority=SourceAuthority.USER_SUPPLIED,
        acquisition_method=AcquisitionMethod.MANUAL_UPLOAD,
    )

    assert document.media_type == "application/octet-stream"


def test_missing_source_file_is_rejected(tmp_path):
    service = FilesystemAcquisitionService(tmp_path)

    with pytest.raises(
        FileNotFoundError,
        match="Source file does not exist",
    ):
        service.acquire(
            source_file=tmp_path / "missing.pdf",
            title="Missing document",
            source_organization="CNU",
            authority=SourceAuthority.USER_SUPPLIED,
            acquisition_method=AcquisitionMethod.MANUAL_UPLOAD,
        )


def test_directory_is_rejected_as_source_file(tmp_path):
    directory = tmp_path / "directory"
    directory.mkdir()

    service = FilesystemAcquisitionService(tmp_path)

    with pytest.raises(
        ValueError,
        match="not a regular file",
    ):
        service.acquire(
            source_file=directory,
            title="Invalid source",
            source_organization="CNU",
            authority=SourceAuthority.USER_SUPPLIED,
            acquisition_method=AcquisitionMethod.MANUAL_UPLOAD,
        )


def test_file_outside_storage_root_is_rejected(
    tmp_path,
    tmp_path_factory,
):
    outside_root = tmp_path_factory.mktemp("outside")
    outside_file = outside_root / "outside.pdf"
    outside_file.write_bytes(b"outside")

    service = FilesystemAcquisitionService(tmp_path)

    with pytest.raises(
        ValueError,
        match="must be located beneath",
    ):
        service.acquire(
            source_file=outside_file,
            title="Outside document",
            source_organization="CNU",
            authority=SourceAuthority.USER_SUPPLIED,
            acquisition_method=AcquisitionMethod.MANUAL_UPLOAD,
        )


def test_missing_storage_root_is_rejected(tmp_path):
    missing_root = tmp_path / "missing-root"

    with pytest.raises(
        FileNotFoundError,
        match="storage root does not exist",
    ):
        FilesystemAcquisitionService(missing_root)


def test_storage_root_must_be_directory(tmp_path):
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("example", encoding="utf-8")

    with pytest.raises(
        NotADirectoryError,
        match="not a directory",
    ):
        FilesystemAcquisitionService(file_path)


def test_compute_sha256_matches_hashlib(tmp_path):
    source_file = tmp_path / "large-enough.bin"
    source_file.write_bytes((b"abcdef" * 400000))

    expected = hashlib.sha256(
        source_file.read_bytes()
    ).hexdigest()

    actual = FilesystemAcquisitionService.compute_sha256(
        source_file,
        block_size=4096,
    )

    assert actual == expected
