from app.evidence_roles import (
    EvidenceRole,
    allocate_empirical_by_role,
    derive_evidence_role,
)
from app.vector_index import RetrievalResult


def _result(name, score, *, metadata=None):
    return RetrievalResult(
        score=score,
        chunk_id=name,
        knowledge_object_id=name,
        object_type="document",
        chunk_index=0,
        text=f"Evidence from {name}",
        citation={"title": name, "relative_path": f"evidence/{name}.pdf"},
        metadata=dict(metadata or {}),
    )


def _explicit(role, document_type):
    return {
        "evidence_role": role,
        "document_type": document_type,
        "evidence_domains": ["Enrollment Demand"],
    }


def test_highly_relevant_items_can_share_a_role() -> None:
    candidates = [
        _result(f"trend-{index}", 1.0 - index / 10, metadata=_explicit("Federal Study", "enrollment_survey"))
        for index in range(3)
    ]

    allocation = allocate_empirical_by_role(
        candidates,
        limit=3,
        decision_type="academic_program",
        max_per_role=4,
        relevance_margin=0.5,
    )

    assert list(allocation.selected) == candidates
    assert allocation.role_counts == {EvidenceRole.EXTERNAL_TRENDS.value: 3}


def test_comparable_complementary_role_is_not_crowded_out() -> None:
    repeated = [
        _result(f"institutional-{index}", 1.0 - index / 20, metadata={"evidence_role": "Institutional Self-Study"})
        for index in range(5)
    ]
    workforce = _result(
        "labor-market",
        0.79,
        metadata=_explicit("Federal Labor-Market Statistic", "occupational_outlook"),
    )

    allocation = allocate_empirical_by_role(
        repeated + [workforce],
        limit=5,
        decision_type="academic_program",
        max_per_role=4,
        relevance_margin=0.5,
    )

    assert workforce in allocation.selected
    assert repeated[4] in allocation.excluded
    assert "concentration control" in repeated[4].metadata["evidence_exclusion_reason"]
    assert allocation.changed_baseline_order


def test_weak_evidence_is_not_promoted_to_fill_a_role() -> None:
    repeated = [
        _result(f"institutional-{index}", 1.0 - index / 20, metadata={"evidence_role": "Institutional Self-Study"})
        for index in range(5)
    ]
    weak_workforce = _result(
        "weak-labor-market",
        -5.0,
        metadata=_explicit("Federal Labor-Market Statistic", "occupational_outlook"),
    )

    allocation = allocate_empirical_by_role(
        repeated + [weak_workforce],
        limit=5,
        decision_type="academic_program",
        max_per_role=4,
        relevance_margin=0.5,
    )

    assert weak_workforce not in allocation.selected
    assert "below the reranker-relative relevance floor" in weak_workforce.metadata["evidence_exclusion_reason"]
    assert EvidenceRole.WORKFORCE_DEMAND.value in allocation.missing_roles


def test_missing_roles_and_role_provenance_are_reported() -> None:
    trend = _result(
        "trend",
        1.0,
        metadata=_explicit("Federal Study", "enrollment_survey"),
    )
    allocation = allocate_empirical_by_role(
        [trend],
        limit=3,
        decision_type="academic_program",
        max_per_role=4,
        relevance_margin=0.5,
    )

    assert derive_evidence_role(trend).source == "explicit_metadata"
    assert allocation.roles_represented == (EvidenceRole.EXTERNAL_TRENDS.value,)
    assert EvidenceRole.WORKFORCE_DEMAND.value in allocation.missing_roles
    assert EvidenceRole.REGIONAL_DEMAND.value in allocation.missing_roles
    assert EvidenceRole.COMPARATOR.value in allocation.missing_roles
    assert EvidenceRole.INSTITUTIONAL_CAPACITY.value in allocation.missing_roles


def test_nested_external_provenance_drives_role_derivation() -> None:
    labor_market = _result(
        "labor-market",
        1.0,
        metadata={
            "external_provenance": {
                "evidence_role": "Federal Labor-Market Statistic",
                "document_type": "occupational_outlook",
                "evidence_domains": ["Workforce Demand", "Enrollment / Demand"],
            }
        },
    )

    assessment = derive_evidence_role(labor_market)

    assert assessment.role == EvidenceRole.WORKFORCE_DEMAND.value
    assert assessment.source == "explicit_metadata"
    assert assessment.confidence == 0.95


def test_missing_role_metadata_falls_back_to_reranker_order() -> None:
    candidates = [_result("first", 1.0), _result("second", 0.9), _result("third", 0.8)]

    allocation = allocate_empirical_by_role(
        candidates,
        limit=2,
        decision_type="academic_program",
        max_per_role=1,
        relevance_margin=0.5,
    )

    assert list(allocation.selected) == candidates[:2]
    assert not allocation.changed_baseline_order
    assert all(item.metadata["evidence_role_source"] == "fallback" for item in candidates)


def test_enrollment_planning_reports_complementary_missing_roles() -> None:
    trend = _result(
        "trend",
        1.0,
        metadata=_explicit("Federal Study", "enrollment_survey"),
    )

    allocation = allocate_empirical_by_role(
        [trend],
        limit=5,
        decision_type="enrollment_planning",
        max_per_role=4,
        relevance_margin=0.5,
    )

    assert EvidenceRole.EXTERNAL_TRENDS.value in allocation.roles_represented
    assert EvidenceRole.WORKFORCE_DEMAND.value in allocation.missing_roles
    assert EvidenceRole.REGIONAL_DEMAND.value in allocation.missing_roles
    assert EvidenceRole.COMPARATOR.value in allocation.missing_roles
    assert EvidenceRole.INSTITUTIONAL_CAPACITY.value in allocation.missing_roles
