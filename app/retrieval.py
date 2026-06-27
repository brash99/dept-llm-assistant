from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from app.vector_index import search_index, RetrievalResult


@dataclass
class RetrievalReport:
    query: str
    requested_top_k: int
    fetch_k: int
    dedupe_by: Optional[str]
    num_results: int
    reranking_enabled: bool = False


def retrieve(
    query: str,
    vector_db_dir,
    model_name: str,
    device: str = "cuda",
    top_k: int = 5,
    fetch_k: Optional[int] = None,
    dedupe_by: Optional[str] = "text",
) -> tuple[List[RetrievalResult], RetrievalReport]:
    if fetch_k is None:
        fetch_k = max(50, top_k * 10)

    results = search_index(
        query=query,
        vector_db_dir=vector_db_dir,
        model_name=model_name,
        device=device,
        top_k=top_k,
        fetch_k=fetch_k,
        dedupe_by=dedupe_by,
    )

    report = RetrievalReport(
        query=query,
        requested_top_k=top_k,
        fetch_k=fetch_k,
        dedupe_by=dedupe_by,
        num_results=len(results),
        reranking_enabled=False,
    )

    return results, report


def build_context(results: List[RetrievalResult]) -> str:
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
