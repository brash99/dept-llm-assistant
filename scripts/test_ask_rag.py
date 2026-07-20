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
    )
    trace = SimpleNamespace(
        final_results=[_result()] * 5,
        family_removed_candidates=[],
        allocation_removed_candidates=[],
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
