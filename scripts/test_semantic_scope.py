from app import retrieval
from app.chunk import chunk_document
from app.knowledge import KnowledgeObject
from app.semantic_scope import (
    OrganizationalRelationship,
    ScopeRegistry,
    SemanticScope,
    load_scope_registry,
    record_matches_semantic_memberships,
    resolve_retrieval_profile,
    semantic_membership_ids,
)
from app.vector_index import RetrievalResult


def _registry():
    return ScopeRegistry(
        (
            SemanticScope("institution", "institution", "Example University"),
            SemanticScope(
                "department:biology",
                "department",
                "Department of Biology",
                aliases=("biology",),
            ),
        )
    )


def _result():
    return RetrievalResult(
        score=0.8,
        chunk_id="chunk-1",
        knowledge_object_id="object-1",
        object_type="document",
        chunk_index=0,
        text="Published biology facts.",
        citation={"title": "Biology", "relative_path": "biology/report.pdf"},
        metadata={"semantic_memberships": ["institution", "department:biology"]},
    )


def test_repository_registry_contains_current_departments_and_historical_pcse():
    registry = load_scope_registry()
    active = registry.by_kind("department", active_only=True)
    assert len(active) == 16
    assert registry.resolve("english", kind="department").id == "department:english"
    assert registry.resolve("department:pcse").status == "historical"
    assert registry.resolve("cnu").id == "institution"


def test_semantic_memberships_are_many_to_many_metadata_and_inherit_to_chunks():
    relationship = OrganizationalRelationship(
        relationship_type="belongs_to",
        target="department:biology",
        published_label="Department of Biology",
    )
    obj = KnowledgeObject(
        id="ko-1",
        object_type="document",
        title="Annual report",
        text="Published institutional and departmental facts.",
        metadata={
            "semantic_memberships": ["institution", "department:biology"],
            "organizational_relationships": [relationship.to_dict()],
            "decision_domains": ["academic_workforce_planning"],
            "institutional_relevance": {"published_scope": "university-wide"},
        },
    )
    assert obj.semantic_memberships == ("institution", "department:biology")
    chunks = chunk_document(obj)
    assert len(chunks) == 1
    for field in (
        "semantic_memberships",
        "organizational_relationships",
        "decision_domains",
        "institutional_relevance",
    ):
        assert chunks[0].metadata[field] == obj.metadata[field]
    assert chunks[0].text == obj.text


def test_membership_normalization_supports_future_mapping_shape():
    assert semantic_membership_ids(
        ["institution", {"scope": "department:biology"}, {"id": "institution"}]
    ) == ("institution", "department:biology")
    record = {"metadata": {"semantic_memberships": ["department:biology"]}}
    assert record_matches_semantic_memberships(record, ("department:biology",))
    assert not record_matches_semantic_memberships(record, ("institution",))
    assert not record_matches_semantic_memberships({"metadata": {}}, ("institution",))


def test_retrieval_profiles_resolve_registry_scopes():
    registry = _registry()
    institution = resolve_retrieval_profile("institution", registry=registry)
    department = resolve_retrieval_profile(
        "department", department="biology", registry=registry
    )
    assert institution.eligible_memberships == ("institution",)
    assert department.eligible_memberships == ("department:biology",)


def test_department_profile_requires_valid_department():
    registry = _registry()
    try:
        resolve_retrieval_profile("department", registry=registry)
    except ValueError as exc:
        assert "requires department" in str(exc)
    else:
        raise AssertionError("department profile accepted a missing selector")


def test_retrieve_passes_scope_filter_without_changing_default(monkeypatch):
    observed = []

    def fake_search_index(**kwargs):
        observed.append(kwargs.get("semantic_memberships_filter"))
        return [_result()]

    monkeypatch.setattr(retrieval, "search_index", fake_search_index)
    scoped, scoped_report, _ = retrieval.retrieve(
        query="biology",
        vector_db_dir="unused",
        model_name="unused",
        constitutional_top_k=0,
        empirical_top_k=1,
        profile="department",
        department="biology",
        scope_registry=_registry(),
    )
    assert scoped
    assert observed == [("department:biology",)]
    assert scoped_report.retrieval_profile == "department"
    assert scoped_report.selected_semantic_scope == "department:biology"
    assert scoped_report.semantic_scope_filter_applied

    observed.clear()
    retrieval.retrieve(
        query="biology",
        vector_db_dir="unused",
        model_name="unused",
        constitutional_top_k=0,
        empirical_top_k=1,
    )
    assert observed == [None]
