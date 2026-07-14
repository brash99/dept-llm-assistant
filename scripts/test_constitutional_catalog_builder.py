from pathlib import Path

from app.knowledge import (
    KnowledgeObject,
    load_knowledge_object,
    save_knowledge_object,
)
from scripts.build_constitutional_catalog import (
    build_catalog,
)


def test_builds_curated_constitutional_catalog(
    tmp_path,
):
    normalized = tmp_path / "normalized"
    output = tmp_path / "constitutional"
    normalized.mkdir()

    source = KnowledgeObject(
        id="source:strategic-compass",
        object_type="document",
        title="Strategic Compass",
        text=(
            "The institution values student success "
            "and experiential learning."
        ),
        metadata={
            "qualified_relative_path": (
                "cnu_website/cnu.edu/"
                "who-we-are/strategic-compass/"
                "index.html"
            ),
        },
        source={
            "url": (
                "https://cnu.edu/who-we-are/"
                "strategic-compass/"
            )
        },
    )

    # The builder also supports objects whose parser-generated
    # Document.relative_path is unavailable.
    save_knowledge_object(
        source,
        normalized / "source.json",
    )

    registry = tmp_path / "constitution.yaml"

    registry.write_text(
        """
institution:
  name: Test University

objects:
  - key: strategic_compass
    enabled: true
    constitutional_type: strategic_compass
    source:
      relative_path: cnu_website/cnu.edu/who-we-are/strategic-compass/index.html
    principles:
      - student success
      - experiential learning
    institutional_scope:
      - Test University
""",
        encoding="utf-8",
    )

    results = build_catalog(
        registry_path=registry,
        normalized_dir=normalized,
        output_dir=output,
    )

    assert results["attempted"] == 1
    assert results["created"] == 1
    assert results["failed"] == 0

    result = load_knowledge_object(
        output / "strategic_compass.json"
    )

    assert result.object_type == (
        "constitutional_knowledge"
    )

    assert result.constitutional_type == (
        "strategic_compass"
    )

    assert result.principles == (
        "student success",
        "experiential learning",
    )


def test_builder_is_idempotent(
    tmp_path,
):
    normalized = tmp_path / "normalized"
    output = tmp_path / "constitutional"
    normalized.mkdir()

    source = KnowledgeObject(
        id="source:mission",
        object_type="document",
        title="Mission",
        text="The institutional mission.",
        metadata={
            "qualified_relative_path": (
                "cnu_website/cnu.edu/"
                "who-we-are/mission/index.html"
            ),
        },
        source={},
    )

    save_knowledge_object(
        source,
        normalized / "source.json",
    )

    registry = tmp_path / "constitution.yaml"

    registry.write_text(
        """
objects:
  - key: mission
    enabled: true
    constitutional_type: mission
    source:
      relative_path: cnu_website/cnu.edu/who-we-are/mission/index.html
    principles:
      - undergraduate education
""",
        encoding="utf-8",
    )

    first = build_catalog(
        registry_path=registry,
        normalized_dir=normalized,
        output_dir=output,
    )

    second = build_catalog(
        registry_path=registry,
        normalized_dir=normalized,
        output_dir=output,
    )

    assert first["created"] == 1
    assert second["unchanged"] == 1
