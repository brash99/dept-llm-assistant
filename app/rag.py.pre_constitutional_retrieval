from openai import OpenAI

from app.retrieval import retrieve


def build_context(results):
    parts = []

    for i, result in enumerate(results, start=1):
        citation = result.citation
        parts.append(
            f"[Source {i}]\n"
            f"Title: {citation.get('title')}\n"
            f"Path: {citation.get('relative_path')}\n"
            f"Chars: {citation.get('start_char')}–{citation.get('end_char')}\n\n"
            f"{result.text}"
        )

    return "\n\n" + ("-" * 70 + "\n\n").join(parts)


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
):
    query = query.strip()

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
    )

    if return_trace:
        results, retrieval_report, trace, profile = retrieved
    else:
        results, retrieval_report, profile = retrieved
        trace = None

    context = build_context(results)

    prompt = f"""
You are a careful assistant answering questions using only the provided sources.

Rules:
- Answer only from the sources below.
- If the sources do not contain the answer, say that clearly.
- Cite sources inline using [Source 1], [Source 2], etc.
- Be concise but complete.

Question:
{query}

Sources:
{context}

Answer:
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
        return answer, results, retrieval_report, trace, profile

    return answer, results, profile
