from pathlib import Path

import pytest

from app.acquisition import (
    AcquisitionManifest,
    AcquisitionMethod,
    AcquisitionStatus,
    DirectoryAcquisitionRunner,
    FilesystemAcquisitionService,
    SourceAuthority,
)


def build_runner(tmp_path):
    storage_root = tmp_path / "storage"
    storage_root.mkdir()

    manifest = AcquisitionManifest(
        tmp_path / "manifest.jsonl"
    )

    filesystem_service = FilesystemAcquisitionService(
        storage_root
    )

    runner = DirectoryAcquisitionRunner(
        filesystem_service=filesystem_service,
        manifest=manifest,
    )

    return storage_root, manifest, runner


def write_test_files(directory: Path):
    (directory / "a.txt").write_text(
        "alpha",
        encoding="utf-8",
    )

    nested = directory / "nested"
    nested.mkdir()

    (nested / "b.txt").write_text(
        "beta",
        encoding="utf-8",
    )

    (nested / "c.pdf").write_bytes(
        b"fake-pdf-content"
    )


def test_first_run_records_all_files_as_new(tmp_path):
    storage_root, manifest, runner = build_runner(
        tmp_path
    )

    write_test_files(storage_root)

    report = runner.run(
        directory=storage_root,
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=(
            AcquisitionMethod.FILESYSTEM_IMPORT
        ),
    )

    assert report.files_examined == 3
    assert report.new_documents == 3
    assert report.unchanged_documents == 0
    assert report.changed_documents == 0
    assert report.duplicate_documents == 0
    assert report.failed_documents == 0
    assert report.successful_documents == 3
    assert len(manifest.read_all()) == 3


def test_second_run_records_all_files_as_unchanged(
    tmp_path,
):
    storage_root, manifest, runner = build_runner(
        tmp_path
    )

    write_test_files(storage_root)

    runner.run(
        directory=storage_root,
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=(
            AcquisitionMethod.FILESYSTEM_IMPORT
        ),
    )

    report = runner.run(
        directory=storage_root,
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=(
            AcquisitionMethod.FILESYSTEM_IMPORT
        ),
    )

    assert report.files_examined == 3
    assert report.new_documents == 0
    assert report.unchanged_documents == 3
    assert report.changed_documents == 0
    assert report.duplicate_documents == 0
    assert report.failed_documents == 0
    assert len(manifest.read_all()) == 3


def test_modified_file_is_recorded_as_changed(tmp_path):
    storage_root, manifest, runner = build_runner(
        tmp_path
    )

    write_test_files(storage_root)

    runner.run(
        directory=storage_root,
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=(
            AcquisitionMethod.FILESYSTEM_IMPORT
        ),
    )

    (storage_root / "a.txt").write_text(
        "alpha changed",
        encoding="utf-8",
    )

    report = runner.run(
        directory=storage_root,
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=(
            AcquisitionMethod.FILESYSTEM_IMPORT
        ),
    )

    assert report.files_examined == 3
    assert report.new_documents == 0
    assert report.unchanged_documents == 2
    assert report.changed_documents == 1
    assert report.failed_documents == 0
    assert len(manifest.read_all()) == 4


def test_duplicate_content_is_detected(tmp_path):
    storage_root, _, runner = build_runner(tmp_path)

    first = storage_root / "first.txt"
    first.write_text("same bytes", encoding="utf-8")

    first_report = runner.run(
        directory=storage_root,
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=(
            AcquisitionMethod.FILESYSTEM_IMPORT
        ),
    )

    assert first_report.new_documents == 1

    second = storage_root / "second.txt"
    second.write_text("same bytes", encoding="utf-8")

    second_report = runner.run(
        directory=storage_root,
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=(
            AcquisitionMethod.FILESYSTEM_IMPORT
        ),
    )

    assert second_report.files_examined == 2
    assert second_report.unchanged_documents == 1
    assert second_report.duplicate_documents == 1


def test_non_recursive_run_ignores_nested_files(tmp_path):
    storage_root, _, runner = build_runner(tmp_path)

    write_test_files(storage_root)

    report = runner.run(
        directory=storage_root,
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=(
            AcquisitionMethod.FILESYSTEM_IMPORT
        ),
        recursive=False,
    )

    assert report.files_examined == 1
    assert report.new_documents == 1


def test_default_ignored_files_are_skipped(tmp_path):
    storage_root, _, runner = build_runner(tmp_path)

    (storage_root / "real.txt").write_text(
        "real",
        encoding="utf-8",
    )
    (storage_root / ".DS_Store").write_bytes(b"noise")
    (storage_root / "cache.pyc").write_bytes(b"noise")
    (storage_root / "partial.tmp").write_bytes(b"noise")

    report = runner.run(
        directory=storage_root,
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=(
            AcquisitionMethod.FILESYSTEM_IMPORT
        ),
    )

    assert report.files_examined == 1
    assert report.new_documents == 1


def test_directory_outside_storage_root_is_rejected(
    tmp_path,
):
    storage_root, _, runner = build_runner(tmp_path)

    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(
        ValueError,
        match="must be located beneath",
    ):
        runner.run(
            directory=outside,
            source_organization="CNU",
            authority=(
                SourceAuthority.INSTITUTIONAL_PRIMARY
            ),
            acquisition_method=(
                AcquisitionMethod.FILESYSTEM_IMPORT
            ),
        )


def test_report_to_dict_is_serializable(tmp_path):
    storage_root, _, runner = build_runner(tmp_path)

    (storage_root / "example.txt").write_text(
        "example",
        encoding="utf-8",
    )

    report = runner.run(
        directory=storage_root,
        source_organization="CNU",
        authority=SourceAuthority.INSTITUTIONAL_PRIMARY,
        acquisition_method=(
            AcquisitionMethod.FILESYSTEM_IMPORT
        ),
    )

    payload = report.to_dict()

    assert payload["files_examined"] == 1
    assert payload["new_documents"] == 1
    assert payload["successful_documents"] == 1
    assert payload["failures"] == []
