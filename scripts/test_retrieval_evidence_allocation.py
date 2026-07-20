from app import retrieval
from app.vector_index import RetrievalResult


def _result(path, text, score, *, chunk_index=0, object_type="document", metadata=None):
    return RetrievalResult(
        score=score,
        chunk_id=f"{path}:{chunk_index}",
        knowledge_object_id=path,
        object_type=object_type,
        chunk_index=chunk_index,
        text=text,
        citation={"title": path.rsplit("/", 1)[-1], "relative_path": path},
        metadata=dict(metadata or {}),
    )


def _retrieve(monkeypatch, candidates, **overrides):
    def fake_search_index(**kwargs):
        if kwargs.get("object_type_filter") == "constitutional_knowledge":
            return [item for item in candidates if item.object_type == "constitutional_knowledge"]
        return [item for item in candidates if item.object_type != "constitutional_knowledge"]

    monkeypatch.setattr(retrieval, "search_index", fake_search_index)
    options = dict(
        query="national enrollment trends and program implications",
        vector_db_dir="unused",
        model_name="unused",
        fetch_k=20,
        dedupe_by="text",
        rerank=False,
        return_trace=True,
        constitutional_top_k=0,
        empirical_top_k=4,
        max_per_document_family=2,
    )
    options.update(overrides)
    return retrieval.retrieve(**options)


def test_related_weak_variants_do_not_displace_strong_evidence(monkeypatch) -> None:
    candidates = [
        _result(f"ABET/Criterion_1_Students_{variant}.pdf", f"variant {variant}", score)
        for variant, score in (("Final", 1.0), ("FinalDraft", 0.99), ("Draft", 0.98), ("V03", 0.97))
    ] + [
        _result("External/National Trend Report.pdf", "long-term enrollment trend", 0.90),
        _result("External/Recent Survey.pdf", "recent enrollment and degrees", 0.89),
    ]

    results, report, trace, _ = _retrieve(monkeypatch, candidates)

    assert [item.text for item in results] == [
        "variant Final",
        "variant FinalDraft",
        "long-term enrollment trend",
        "recent enrollment and degrees",
    ]
    assert report.num_removed_by_family_diversity == 2
    assert len(trace.family_removed_candidates) == 2
    assert all(
        "document-family diversity cap" in item.metadata["evidence_exclusion_reason"]
        for item in trace.family_removed_candidates
    )


def test_complementary_chunks_from_one_report_can_survive(monkeypatch) -> None:
    candidates = [
        _result("External/Trend Report.pdf", "historic program counts", 1.0, chunk_index=0),
        _result("External/Trend Report.pdf", "recent degree production", 0.9, chunk_index=1),
        _result("External/Trend Report.pdf", "repeated background", 0.8, chunk_index=2),
    ]

    results, report, trace, _ = _retrieve(
        monkeypatch,
        candidates,
        empirical_top_k=3,
    )

    assert [item.chunk_index for item in results] == [0, 1]
    assert report.num_removed_by_family_diversity == 1
    assert trace.family_removed_candidates[0].chunk_index == 2


def test_constitutional_fallback_remains_separate(monkeypatch) -> None:
    constitutional = _result(
        "Constitution/Strategic Compass.json",
        "institutional value",
        0.1,
        object_type="constitutional_knowledge",
    )
    empirical = _result("External/Survey.pdf", "empirical trend", 0.9)

    results, report, trace, profile = _retrieve(
        monkeypatch,
        [empirical, constitutional],
        constitutional_top_k=1,
        empirical_top_k=1,
    )

    assert len((results, report, trace, profile)) == 4
    assert [item.object_type for item in results] == [
        "constitutional_knowledge",
        "document",
    ]
    assert [item.text for item in results] == ["institutional value", "empirical trend"]
    assert report.constitutional_fallback_used
    assert results[0].metadata["constitutional_fallback"] is True
    assert "constitutional evidence quota" in results[0].metadata["evidence_selection_reason"]
    assert "empirical evidence quota" in results[1].metadata["evidence_selection_reason"]


def test_retrieval_non_trace_contract_remains_three_values(monkeypatch) -> None:
    candidate = _result("External/Survey.pdf", "empirical trend", 0.9)
    monkeypatch.setattr(retrieval, "search_index", lambda **kwargs: [candidate])

    response = retrieval.retrieve(
        query="enrollment trend",
        vector_db_dir="unused",
        model_name="unused",
        rerank=False,
        return_trace=False,
        constitutional_top_k=0,
        empirical_top_k=1,
        max_per_document_family=2,
    )

    assert len(response) == 3
    results, report, _profile = response
    assert [item.text for item in results] == ["empirical trend"]
    assert report.num_results == 1
