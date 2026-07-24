import json

import pytest

from app.ontology_explorer import (
    DepartmentContributionExplorerAdapter,
    OntologyExplorerRegistry,
    OntologyObjectRepository,
)
from app.contribution_ontology import ContributionPredicate
from scripts.test_contribution_inspection import _object


def test_repository_loads_and_validates_canonical_department_objects(tmp_path):
    value = _object()
    path = tmp_path / "department.json"
    path.write_text(value.to_json(), encoding="utf-8")
    (tmp_path / "structural_signatures.json").write_text(
        "[]", encoding="utf-8"
    )

    result = OntologyObjectRepository().load_directory(tmp_path)

    assert not result.errors
    assert result.ignored_paths == (
        tmp_path / "structural_signatures.json",
    )
    assert len(result.objects) == 1
    loaded = result.objects[0]
    assert loaded.object_type == "department_contribution"
    assert loaded.display_label == "Department of English"
    assert loaded.semantic_object == value


def test_repository_surfaces_tampered_objects_instead_of_loading_them(tmp_path):
    payload = _object().to_dict()
    payload["deterministic_fingerprint"] = "0" * 64
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = OntologyObjectRepository().load_directory(tmp_path)

    assert not result.objects
    assert len(result.errors) == 1
    assert "fingerprint does not match" in result.errors[0]


def test_hierarchy_exposes_semantic_content_without_interpretation():
    value = _object()
    adapter = DepartmentContributionExplorerAdapter()
    hierarchy = adapter.hierarchy(value)

    assert hierarchy["object_identity"]["contribution_object_id"] == (
        value.contribution_object_id
    )
    assert hierarchy["governed_entity"]["entity_id"] == value.entity.entity_id
    assertions = hierarchy["contribution_assertions"]
    assert len(assertions) == len(value.assertions)
    ownership = next(
        item
        for item in assertions
        if item["relationship"]["predicate"] == "owns_curriculum"
    )
    assert ownership["relationship"]["subject"]["entity_id"] == (
        value.entity.entity_id
    )
    assert ownership["relationship"]["object"]["entity_id"] == (
        "instructional_subject:ENGL"
    )
    assert set(hierarchy) == {
        "object_identity",
        "governed_entity",
        "temporal_scope",
        "provenance",
        "contribution_assertions",
    }


def test_graph_has_one_edge_per_assertion_and_preserves_relationships():
    value = _object()
    graph = DepartmentContributionExplorerAdapter().graph(value)

    assert len(graph.edges) == len(value.assertions)
    assert len({item.edge_id for item in graph.edges}) == len(graph.edges)
    assert all(item.subject_id == value.entity.entity_id for item in graph.edges)
    assert {
        item.predicate for item in graph.edges
    } == {item.predicate.value for item in value.assertions}
    dot = graph.to_dot(
        (ContributionPredicate.OWNS_CURRICULUM.value,),
        ("instructional_subject",),
    )
    assert "owns_curriculum" in dot
    assert "instructional_subject:ENGL" in dot
    assert "supports_program" not in dot
    empty = graph.to_dot((), ())
    assert " -> " not in empty


def test_registry_rejects_duplicate_adapters_and_is_future_extensible():
    adapter = DepartmentContributionExplorerAdapter()
    registry = OntologyExplorerRegistry((adapter,))
    with pytest.raises(ValueError, match="Duplicate"):
        registry.register(DepartmentContributionExplorerAdapter())
    assert registry.supported_object_types == ("department_contribution",)


def test_missing_directory_is_an_inspection_error_not_an_empty_success(tmp_path):
    result = OntologyObjectRepository().load_directory(tmp_path / "missing")
    assert not result.objects
    assert result.errors == (
        f"Ontology object directory does not exist: {tmp_path / 'missing'}",
    )
