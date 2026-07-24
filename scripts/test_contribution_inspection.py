import json

from app.contribution_inspection import ContributionOntologyInspector
from app.contribution_ontology import ContributionPredicate
from scripts.test_department_contributions import (
    _attribution,
    _profile,
    _scope,
)
from app.department_contributions import DepartmentContributionBuilder
from scripts.inspect_department_contributions import main


def _object():
    return DepartmentContributionBuilder().build(
        (_profile(),),
        temporal_scope=_scope(),
        instructional_attribution=_attribution(),
        llc_attribution=_attribution(llc_only=True),
    )[0]


def test_inspector_renders_ontology_without_deriving_narrative():
    value = _object()
    rendered = ContributionOntologyInspector().render(value)

    assert value.contribution_object_id in rendered
    assert value.deterministic_fingerprint in rendered
    assert "TEMPORAL SCOPE" in rendered
    assert "ASSERTIONS" in rendered
    assert "--owns_curriculum-->" in rendered
    assert "Measures" in rendered
    assert "Evidence bindings" in rendered
    assert "Evidence fitness" in rendered
    assert "CANONICAL JSON SERIALIZATION" in rendered
    assert value.to_json() in rendered
    assert "recommend" not in rendered.casefold()


def test_structural_signature_is_deterministic_and_non_evaluative():
    inspector = ContributionOntologyInspector()
    first = inspector.structural_signature(_object())
    second = inspector.structural_signature(_object())

    assert first == second
    assert first["predicate_counts"][
        ContributionPredicate.OWNS_CURRICULUM.value
    ] >= 1
    assert set(first) == {
        "contribution_object_id",
        "entity_id",
        "assertion_count",
        "predicate_counts",
        "object_type_counts",
        "deterministic_fingerprint",
    }


def test_inspection_cli_writes_byte_identical_canonical_objects(tmp_path):
    profiles = tmp_path / "profiles.jsonl"
    profiles.write_text(
        json.dumps(_profile(), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    outputs = (tmp_path / "first", tmp_path / "second")
    arguments = [
        "--profiles",
        str(profiles),
        "--unit-id",
        "academic_unit:department_english",
        "--reporting-label",
        "Fixture reporting period",
        "--publication-time",
        "2026-07-24T12:00:00-04:00",
        "--omit-canonical-json",
    ]
    for output in outputs:
        assert main([*arguments, "--output-dir", str(output)]) == 0

    assert {item.name for item in outputs[0].iterdir()} == {
        item.name for item in outputs[1].iterdir()
    }
    for item in outputs[0].iterdir():
        assert item.read_bytes() == (outputs[1] / item.name).read_bytes()
