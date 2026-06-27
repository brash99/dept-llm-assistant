from dataclasses import dataclass
from typing import List, Optional

from sentence_transformers import CrossEncoder

from app.vector_index import search_index, RetrievalResult


@dataclass
class RetrievalReport:
    query: str
    requested_top_k: int
    fetch_k: int
    dedupe_by: Optional[str]
    num_candidates: int
    num_results: int
    reranking_enabled: bool = False
    reranker_model: Optional[str] = None


def rerank_results(
    query: str,
    results: List[RetrievalResult],
    model_name: str,
    device: str = "cuda",
) -> List[RetrievalResult]:
    if not results:
        return results

    reranker = CrossEncoder(model_name, device=device)

    pairs = [(query, result.text) for result in results]
    scores = reranker.predict(pairs)

    reranked = []

    for result, score in zip(results, scores):
        result.metadata["faiss_score"] = result.score
        result.metadata["rerank_score"] = float(score)
        result.score = float(score)
        reranked.append(result)

    reranked.sort(key=lambda item: item.score, reverse=True)

    return reranked


def retrieve(
    query: str,
    vector_db_dir,
    model_name: str,
    device: str = "cuda",
    top_k: int = 5,
    fetch_k: Optional[int] = None,
    dedupe_by: Optional[str] = "text",
    rerank: bool = False,
    reranker_model: Optional[str] = None,
    reranker_device: str = "cuda",
) -> tuple[List[RetrievalResult], RetrievalReport]:
    if fetch_k is None:
        fetch_k = max(50, top_k * 10)

    candidate_results = search_index(
        query=query,
        vector_db_dir=vector_db_dir,
        model_name=model_name,
        device=device,
        top_k=fetch_k,
        fetch_k=fetch_k,
        dedupe_by=dedupe_by,
    )

    if rerank:
        if reranker_model is None:
            raise ValueError("reranker_model must be provided when rerank=True")

        ranked_results = rerank_results(
            query=query,
            results=candidate_results,
            model_name=reranker_model,
            device=reranker_device,
        )
    else:
        ranked_results = candidate_results

    final_results = ranked_results[:top_k]

    report = RetrievalReport(
        query=query,
        requested_top_k=top_k,
        fetch_k=fetch_k,
        dedupe_by=dedupe_by,
        num_candidates=len(candidate_results),
        num_results=len(final_results),
        reranking_enabled=rerank,
        reranker_model=reranker_model if rerank else None,
    )

    return final_results, report


def build_context(results: List[RetrievalResult]) -> str:
    parts = []

    for i, result in enumerate(results, start=1):
        citation = result.citation
        parts.append(
            f"[Source {i}]\n"
            f"Title: {citation.get('title')}\n"
            f"Path: {citation.get('relative_path')}\n"
            f"Chars: {citation.get('start_char')}–{citation.get('end_char')}\n"
            f"Score: {result.score:.4f}\n\n"
            f"{result.text}"
        )

    return "\n\n" + ("-" * 70 + "\n\n").join(parts)
