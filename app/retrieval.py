from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import List, Optional
import copy
import re
import time

from sentence_transformers import CrossEncoder

from app.vector_index import search_index, RetrievalResult
from app.document_family import document_family_key


@dataclass
class RetrievalProfile:
    total_seconds: float
    search_seconds: float
    dedupe_seconds: float
    rerank_seconds: float
    threshold_seconds: float
    family_diversity_seconds: float = 0.0


@dataclass
class RetrievalTrace:
    raw_candidates: List[RetrievalResult]
    deduped_candidates: List[RetrievalResult]
    reranked_candidates: List[RetrievalResult]
    thresholded_candidates: List[RetrievalResult]
    final_results: List[RetrievalResult]
    family_diversified_candidates: List[RetrievalResult] = field(default_factory=list)
    family_removed_candidates: List[RetrievalResult] = field(default_factory=list)
    allocation_removed_candidates: List[RetrievalResult] = field(default_factory=list)


@dataclass
class RetrievalReport:
    query: str
    requested_top_k: int
    fetch_k: int
    dedupe_by: Optional[str]

    constitutional_top_k: int
    empirical_top_k: int
    constitutional_results: int
    empirical_results: int
    constitutional_fallback_used: bool

    num_candidates: int
    num_after_dedup: int
    num_after_rerank: int
    num_after_threshold: int
    num_results: int

    reranking_enabled: bool = False
    reranker_model: Optional[str] = None
    min_rerank_score: Optional[float] = None
    max_per_document_family: Optional[int] = None
    num_after_family_diversity: int = 0
    num_removed_by_family_diversity: int = 0
    num_removed_by_evidence_allocation: int = 0


def clone_results(results: List[RetrievalResult]) -> List[RetrievalResult]:
    """
    Make shallow independent copies of retrieval results for tracing.

    This prevents reranking from mutating the FAISS-stage objects in-place,
    so Developer Mode can honestly show raw FAISS scores, deduped results,
    reranked results, and thresholded results as separate stages.
    """
    cloned = []

    for result in results:
        item = copy.copy(result)
        item.metadata = dict(result.metadata)
        item.citation = dict(result.citation)
        cloned.append(item)

    return cloned


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


CROSS_FORMAT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".odt",
    ".rtf",
    ".txt",
    ".html",
    ".htm",
    ".xls",
    ".xlsx",
    ".csv",
    ".ppt",
    ".pptx",
}


def canonical_document_key(result: RetrievalResult) -> str:
    """
    Return a stable cross-format identity for one retrieved document.

    Files such as report.docx and report.pdf are treated as representations
    of the same underlying document when they occupy the same source path.
    The original path and citation remain unchanged.
    """
    citation = result.citation or {}

    raw_path = (
        citation.get("relative_path")
        or citation.get("source_path")
        or ""
    )

    normalized_path = (
        str(raw_path)
        .strip()
        .replace("\\", "/")
        .lower()
    )

    if not normalized_path:
        return result.knowledge_object_id

    source_path = PurePosixPath(normalized_path)
    suffix = source_path.suffix.lower()

    if suffix in CROSS_FORMAT_EXTENSIONS:
        source_path = source_path.with_suffix("")

    # Normalize minor separator differences without merging substantively
    # different filenames.
    normalized_stem = re.sub(
        r"[\s_-]+",
        " ",
        source_path.name,
    ).strip()

    parent = str(source_path.parent)

    if parent == ".":
        return normalized_stem

    return f"{parent}/{normalized_stem}"


def dedupe_results(
    results: List[RetrievalResult],
    dedupe_by: Optional[str] = "text",
) -> List[RetrievalResult]:
    if dedupe_by is None:
        return results

    seen = set()
    deduped = []

    for result in results:
        if dedupe_by == "text":
            key = result.text.strip()

        elif dedupe_by in ("document", "relative_path"):
            key = canonical_document_key(result)

        elif dedupe_by == "source_path":
            key = result.citation.get("source_path")

        else:
            raise ValueError(f"Unknown dedupe_by mode: {dedupe_by}")

        if key is None:
            key = result.text.strip()

        if key in seen:
            continue

        seen.add(key)
        deduped.append(result)

    return deduped


def diversify_document_families(
    results: List[RetrievalResult],
    max_per_family: Optional[int],
) -> tuple[List[RetrievalResult], List[RetrievalResult]]:
    """Preserve rank while limiting revision-heavy document families."""
    if max_per_family is not None and max_per_family < 1:
        raise ValueError("max_per_document_family must be at least 1 or None")

    kept = []
    removed = []
    counts = {}

    for result in results:
        key = document_family_key(result)
        result.metadata["document_family_key"] = key
        count = counts.get(key, 0)
        if max_per_family is not None and count >= max_per_family:
            result.metadata["evidence_exclusion_reason"] = (
                "Excluded by document-family diversity cap "
                f"({max_per_family} per family)."
            )
            removed.append(result)
            continue
        counts[key] = count + 1
        result.metadata["evidence_selection_reason"] = (
            "Retained in reranker order within the document-family cap."
        )
        kept.append(result)

    return kept, removed


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
    min_rerank_score: Optional[float] = None,
    return_trace: bool = False,
    constitutional_top_k: int = 2,
    empirical_top_k: int = 10,
    max_per_document_family: Optional[int] = None,
):
    query = query.strip()

    if constitutional_top_k < 0:
        raise ValueError("constitutional_top_k cannot be negative")

    if empirical_top_k < 0:
        raise ValueError("empirical_top_k cannot be negative")

    if fetch_k is None:
        fetch_k = 200

    requested_total = constitutional_top_k + empirical_top_k

    # Preserve compatibility with callers that still supply only top_k.
    # Explicit evidence quotas determine the final result count.
    top_k = requested_total

    t_total_start = time.perf_counter()

    t0 = time.perf_counter()
    raw_candidates = search_index(
        query=query,
        vector_db_dir=vector_db_dir,
        model_name=model_name,
        device=device,
        top_k=fetch_k,
        fetch_k=fetch_k,
        dedupe_by=None,
    )
    constitutional_in_initial_pool = sum(
        1
        for result in raw_candidates
        if result.object_type == "constitutional_knowledge"
    )
    for result in raw_candidates:
        result.metadata["constitutional_fallback"] = False

    constitutional_fallback_used = (
        constitutional_in_initial_pool < constitutional_top_k
    )

    if constitutional_fallback_used and constitutional_top_k > 0:
        fallback_results = search_index(
            query=query,
            vector_db_dir=vector_db_dir,
            model_name=model_name,
            device=device,
            top_k=max(constitutional_top_k * 5, constitutional_top_k),
            fetch_k=None,
            dedupe_by=None,
            object_type_filter="constitutional_knowledge",
        )

        existing_chunk_ids = {
            result.chunk_id
            for result in raw_candidates
        }

        for result in fallback_results:
            if result.chunk_id not in existing_chunk_ids:
                result.metadata["constitutional_fallback"] = True
                raw_candidates.append(result)
                existing_chunk_ids.add(result.chunk_id)

    t1 = time.perf_counter()

    deduped_candidates = dedupe_results(
        raw_candidates,
        dedupe_by=dedupe_by,
    )
    t2 = time.perf_counter()

    if rerank:
        if reranker_model is None:
            raise ValueError("reranker_model must be provided when rerank=True")

        # Clone so reranking does not mutate raw/deduped trace objects.
        rerank_input = clone_results(deduped_candidates)

        reranked_candidates = rerank_results(
            query=query,
            results=rerank_input,
            model_name=reranker_model,
            device=reranker_device,
        )
    else:
        reranked_candidates = clone_results(deduped_candidates)
    t3 = time.perf_counter()

    (
        family_diversified_candidates,
        family_removed_candidates,
    ) = diversify_document_families(
        reranked_candidates,
        max_per_family=max_per_document_family,
    )
    t_family = time.perf_counter()

    if rerank and min_rerank_score is not None:
        thresholded_candidates = [
            result
            for result in family_diversified_candidates
            if result.score >= min_rerank_score
        ]
    else:
        thresholded_candidates = family_diversified_candidates
    t4 = time.perf_counter()

    constitutional_candidates = [
        result
        for result in thresholded_candidates
        if result.object_type == "constitutional_knowledge"
    ]

    empirical_candidates = [
        result
        for result in thresholded_candidates
        if result.object_type != "constitutional_knowledge"
    ]

    selected_constitutional = constitutional_candidates[
        :constitutional_top_k
    ]

    selected_empirical = empirical_candidates[
        :empirical_top_k
    ]

    for rank, result in enumerate(selected_constitutional, start=1):
        result.metadata["final_evidence_rank"] = rank
        result.metadata["evidence_selection_reason"] = (
            "Selected for the constitutional evidence quota after separate "
            "constitutional ranking."
        )

    for offset, result in enumerate(selected_empirical, start=1):
        result.metadata["final_evidence_rank"] = len(selected_constitutional) + offset
        result.metadata["evidence_selection_reason"] = (
            "Selected for the empirical evidence quota in diversified "
            "reranker order."
        )

    allocation_removed_candidates = (
        constitutional_candidates[constitutional_top_k:]
        + empirical_candidates[empirical_top_k:]
    )
    for result in allocation_removed_candidates:
        result.metadata["evidence_exclusion_reason"] = (
            "Excluded after the applicable constitutional or empirical "
            "evidence quota was filled."
        )

    final_results = (
        selected_constitutional
        + selected_empirical
    )

    t_total_end = time.perf_counter()

    profile = RetrievalProfile(
        total_seconds=t_total_end - t_total_start,
        search_seconds=t1 - t0,
        dedupe_seconds=t2 - t1,
        rerank_seconds=t3 - t2,
        family_diversity_seconds=t_family - t3,
        threshold_seconds=t4 - t_family,
    )

    report = RetrievalReport(
        query=query,
        requested_top_k=top_k,
        fetch_k=fetch_k,
        dedupe_by=dedupe_by,
        constitutional_top_k=constitutional_top_k,
        empirical_top_k=empirical_top_k,
        constitutional_results=len(selected_constitutional),
        empirical_results=len(selected_empirical),
        constitutional_fallback_used=constitutional_fallback_used,
        num_candidates=len(raw_candidates),
        num_after_dedup=len(deduped_candidates),
        num_after_rerank=len(reranked_candidates),
        num_after_family_diversity=len(family_diversified_candidates),
        num_removed_by_family_diversity=len(family_removed_candidates),
        num_removed_by_evidence_allocation=len(allocation_removed_candidates),
        num_after_threshold=len(thresholded_candidates),
        num_results=len(final_results),
        reranking_enabled=rerank,
        reranker_model=reranker_model if rerank else None,
        min_rerank_score=min_rerank_score,
        max_per_document_family=max_per_document_family,
    )

    if return_trace:
        trace = RetrievalTrace(
            raw_candidates=raw_candidates,
            deduped_candidates=deduped_candidates,
            reranked_candidates=reranked_candidates,
            family_diversified_candidates=family_diversified_candidates,
            family_removed_candidates=family_removed_candidates,
            allocation_removed_candidates=allocation_removed_candidates,
            thresholded_candidates=thresholded_candidates,
            final_results=final_results,
        )
        return final_results, report, trace, profile

    return final_results, report, profile


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


@dataclass
class EvidenceGroups:
    constitutional: List[RetrievalResult]
    empirical: List[RetrievalResult]


def partition_evidence(
    results: List[RetrievalResult],
) -> EvidenceGroups:
    """
    Separate retrieved evidence by semantic object type.

    Retrieval itself remains unified. Classification happens only after
    ranking, using metadata already carried by each indexed record.
    """
    constitutional = []
    empirical = []

    for result in results:
        if result.object_type == "constitutional_knowledge":
            constitutional.append(result)
        else:
            empirical.append(result)

    return EvidenceGroups(
        constitutional=constitutional,
        empirical=empirical,
    )


def _format_result(
    result: RetrievalResult,
    label: str,
) -> str:
    citation = result.citation
    metadata = result.metadata

    lines = [
        f"[{label}]",
        f"Title: {citation.get('title')}",
        f"Path: {citation.get('relative_path')}",
        (
            "Chars: "
            f"{citation.get('start_char')}–"
            f"{citation.get('end_char')}"
        ),
        f"Score: {result.score:.4f}",
    ]

    constitutional_type = metadata.get("constitutional_type")
    if constitutional_type:
        lines.append(
            f"Constitutional type: {constitutional_type}"
        )

    institutional_scope = metadata.get("institutional_scope")
    if institutional_scope:
        lines.append(
            "Institutional scope: "
            + ", ".join(str(item) for item in institutional_scope)
        )

    principles = metadata.get("principles")
    if principles:
        lines.append("Principles:")
        lines.extend(
            f"- {principle}"
            for principle in principles
        )

    lines.extend(["", result.text])

    return "\n".join(lines)


def build_grouped_context(
    results: List[RetrievalResult],
) -> str:
    groups = partition_evidence(results)

    sections = []

    constitutional_parts = [
        _format_result(
            result,
            f"Constitutional Source {index}",
        )
        for index, result in enumerate(
            groups.constitutional,
            start=1,
        )
    ]

    empirical_parts = [
        _format_result(
            result,
            f"Empirical Source {index}",
        )
        for index, result in enumerate(
            groups.empirical,
            start=1,
        )
    ]

    if constitutional_parts:
        constitutional_text = (
            "\n\n"
            + ("-" * 70 + "\n\n").join(
                constitutional_parts
            )
        )
    else:
        constitutional_text = (
            "\n\nNo constitutional evidence was retrieved."
        )

    if empirical_parts:
        empirical_text = (
            "\n\n"
            + ("-" * 70 + "\n\n").join(empirical_parts)
        )
    else:
        empirical_text = (
            "\n\nNo empirical evidence was retrieved."
        )

    sections.append(
        "Institutional Values\n"
        "===================="
        + constitutional_text
    )

    sections.append(
        "Empirical Evidence\n"
        "=================="
        + empirical_text
    )

    return "\n\n\n".join(sections)
