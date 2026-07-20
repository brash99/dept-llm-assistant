from openai import OpenAI

from app.retrieval import (
    retrieve,
    build_grouped_context,
)


def answer_question(
    query,
    vector_db_dir,
    model_name,
    embedding_device,
    llm_base_url,
    llm_model,
    top_k=5,
    fetch_k=None,
    dedupe_by="text",
    rerank=False,
    reranker_model=None,
    reranker_device="cuda",
    min_rerank_score=None,
    return_trace=False,
    constitutional_top_k=2,
    empirical_top_k=10,
    max_per_document_family=2,
    decision_type=None,
    max_per_evidence_role=4,
    evidence_role_relevance_margin=0.5,
):
    """Answer a question and return retrieval artifacts.

    The canonical return contract is ``(answer, results, profile)``. When
    ``return_trace`` is true, it is ``(answer, results, retrieval_report,
    trace, profile)``. This mirrors the Decision Brief reasoning entry point.
    """
    query = query.strip()
    if decision_type is None:
        from app.observatory.evidence_fitness import EvidenceFitnessService

        classified_type, _ = EvidenceFitnessService.classify_decision_type(query)
        decision_type = classified_type.value

    retrieved = retrieve(
        query=query,
        vector_db_dir=vector_db_dir,
        model_name=model_name,
        device=embedding_device,
        top_k=top_k,
        fetch_k=fetch_k,
        dedupe_by=dedupe_by,
        rerank=rerank,
        reranker_model=reranker_model,
        reranker_device=reranker_device,
        min_rerank_score=min_rerank_score,
        return_trace=return_trace,
        constitutional_top_k=constitutional_top_k,
        empirical_top_k=empirical_top_k,
        max_per_document_family=max_per_document_family,
        decision_type=decision_type,
        max_per_evidence_role=max_per_evidence_role,
        evidence_role_relevance_margin=evidence_role_relevance_margin,
    )

    if return_trace:
        results, retrieval_report, trace, profile = retrieved
    else:
        results, retrieval_report, profile = retrieved
        trace = None

    context = build_grouped_context(results)

    prompt = f"""
You are a careful institutional decision-support assistant.

You must reason using two distinct forms of evidence:

1. Institutional Values
   These are constitutional or normative institutional commitments.
   They indicate what the institution values, prioritizes, or seeks to
   become. They do not by themselves establish empirical facts.

2. Empirical Evidence
   These are observations, reports, policies, data, and other factual
   sources. They describe what is known about the institution or the
   external environment.

Rules:
- Answer only from the supplied evidence.
- Clearly distinguish institutional values from empirical claims.
- Do not present a value statement as though it were an empirical fact.
- Do not present an empirical observation as though it determines what
  the institution ought to value.
- Explain how the empirical evidence relates to the institutional values.
- If either evidence category is missing or insufficient, say so clearly.
- Cite constitutional material as [Constitutional Source 1], etc.
- Cite empirical material as [Empirical Source 1], etc.
- Be concise but complete.

{context}

Question
========

{query}

Answer
======
""".strip()

    client = OpenAI(
        base_url=llm_base_url,
        api_key="not-needed",
    )

    response = client.chat.completions.create(
        model=llm_model,
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    if return_trace:
        return (
            answer,
            results,
            retrieval_report,
            trace,
            profile,
        )

    return answer, results, profile
