from pathlib import Path

from app.config import load_config
from app.semantic_pipeline import resolve_pipeline_paths
from scripts import classify_knowledge_corpus


def test_config_defines_one_normalized_root_and_structured_outputs() -> None:
    config = load_config()

    assert config["storage"]["normalized"] == "storage/normalized"
    assert "schedule_observations" not in config["storage"]
    assert "faculty_observations" not in config["storage"]
    assert "catalog_observations" not in config["storage"]
    assert config["schedule_ingestion"]["normalized_output"] == (
        "storage/normalized/schedules/canonical"
    )
    assert config["faculty_ingestion"]["normalized_output_root"] == (
        "storage/normalized/faculty"
    )
    assert config["catalog_ingestion"]["normalized_output_root"] == (
        "storage/normalized/catalogs"
    )


def test_pipeline_uses_only_normalized_and_constitutional_roots() -> None:
    _, paths, _ = resolve_pipeline_paths("config/settings.yaml")

    relative = tuple(
        path.relative_to(paths.repository_root) for path in paths.normalized_roots
    )
    assert relative == (
        Path("storage/normalized"),
        Path("storage/constitutional"),
    )


def test_classifier_defaults_to_one_recursive_normalized_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "storage/normalized").mkdir(parents=True)
    (tmp_path / "storage/constitutional").mkdir(parents=True)
    monkeypatch.setattr(
        classify_knowledge_corpus,
        "load_config",
        lambda: {
            "project": {"root": str(tmp_path)},
            "storage": {
                "normalized": "storage/normalized",
                "constitutional": "storage/constitutional",
            },
        },
    )

    assert classify_knowledge_corpus._default_inputs() == (
        tmp_path / "storage/normalized",
        tmp_path / "storage/constitutional",
    )
