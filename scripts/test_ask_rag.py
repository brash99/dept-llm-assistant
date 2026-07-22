from types import SimpleNamespace

from scripts import ask_rag


def _result():
    return SimpleNamespace(
        score=0.75,
        object_type="document",
        citation={"title": "Health Physics Evidence", "relative_path": "evidence.json"},
        metadata={
            "final_evidence_rank": 1,
            "document_family_key": "health physics evidence",
            "evidence_selection_reason": "Selected for testing.",
        },
    )


def _profile():
    return SimpleNamespace(
        total_seconds=1.0,
        search_seconds=0.4,
        dedupe_seconds=0.1,
        rerank_seconds=0.2,
        family_diversity_seconds=0.2,
        threshold_seconds=0.1,
    )


def _config():
    return {
        "project": {"root": "/tmp/iso"},
        "storage": {"vector_db": "storage/vector_db"},
        "embedding": {"device": "cpu"},
        "llm": {"base_url": "http://localhost:8000/v1", "model": "fixture"},
        "reranking": {"enabled": False},
    }


def test_cli_uses_standard_three_value_answer_contract(monkeypatch, capsys) -> None:
    captured = {}

    def fake_answer_question(**kwargs):
        captured.update(kwargs)
        return "Grounded answer", [_result()], _profile()

    monkeypatch.setattr(ask_rag, "load_config", _config)
    monkeypatch.setattr("sys.argv", ["ask_rag", "Health Physics question"])

    ask_rag.main(fake_answer_question)

    output = capsys.readouterr().out
    assert captured["return_trace"] is False
    assert captured["dedupe_by"] == "text"
    assert captured["max_per_document_family"] == 2
    assert "Grounded answer" in output
    assert "Health Physics Evidence" in output
    assert "Retrieval Diagnostics" not in output


def test_cli_uses_five_value_trace_contract_for_diagnostics(monkeypatch, capsys) -> None:
    report = SimpleNamespace(
        num_candidates=20,
        num_after_dedup=15,
        num_after_rerank=15,
        num_after_family_diversity=12,
        num_after_threshold=12,
        num_results=5,
        num_removed_by_evidence_allocation=3,
        num_removed_by_role_allocation=2,
        num_removed_for_insufficient_relevance=1,
        evidence_roles_represented=("external_landscape_trends",),
        evidence_role_counts={"external_landscape_trends": 2},
        expected_evidence_roles=("external_landscape_trends", "workforce_labor_demand"),
        missing_evidence_roles=("workforce_labor_demand",),
        concentrated_evidence_roles=(),
        role_aware_allocation_changed_order=True,
    )
    trace = SimpleNamespace(
        final_results=[_result()] * 5,
        family_removed_candidates=[],
        allocation_removed_candidates=[],
        role_removed_candidates=[],
        insufficient_relevance_candidates=[],
    )

    def fake_answer_question(**kwargs):
        assert kwargs["return_trace"] is True
        return "Grounded answer", [_result()], report, trace, _profile()

    monkeypatch.setattr(ask_rag, "load_config", _config)
    monkeypatch.setattr(
        "sys.argv",
        ["ask_rag", "Health Physics question", "--diagnostics"],
    )

    ask_rag.main(fake_answer_question)

    output = capsys.readouterr().out
    assert "Retrieval Diagnostics" in output
    assert "Raw candidates       : 20" in output
    assert "Trace final results  : 5" in output
    assert "Family diversity : 0.200s" in output


def test_cli_routes_schedule_aggregation_without_calling_retrieval(monkeypatch, capsys) -> None:
    monkeypatch.setattr(ask_rag, "load_config", _config)
    monkeypatch.setattr(
        "sys.argv", ["ask_rag", "How many adjunct course offerings were there by term?"]
    )
    calls = {"retrieval": 0}

    def forbidden_retrieval(**kwargs):
        calls["retrieval"] += 1
        raise AssertionError("analytical request must not invoke retrieval")

    analytical = SimpleNamespace(
        analytical_result={
            "metric": "course_offerings",
            "grouped_results": [{"academic_term": "2024_fall", "value": 12}],
            "deterministic_result_fingerprint": "fixture-fingerprint",
        },
        retrieved_evidence_request=None,
    )
    ask_rag.main(forbidden_retrieval, lambda request: analytical)
    output = capsys.readouterr().out
    assert calls["retrieval"] == 0
    assert "Deterministic Analytical Output" in output
    assert "fixture-fingerprint" in output


def test_cli_refuses_unsupported_analytical_fallback(monkeypatch, capsys) -> None:
    monkeypatch.setattr(ask_rag, "load_config", _config)
    monkeypatch.setattr("sys.argv", ["ask_rag", "Average class size by subject"])

    def forbidden_retrieval(**kwargs):
        raise AssertionError("unsupported analysis must not invoke retrieval")

    ask_rag.main(forbidden_retrieval)
    output = capsys.readouterr().out
    assert "Unsupported Analysis" in output
    assert "will not substitute a top-k retrieval answer" in output
