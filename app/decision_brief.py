from dataclasses import dataclass, field
from typing import Dict, List, Optional

from openai import OpenAI

from app.retrieval import retrieve
from app.vector_index import RetrievalResult
from app.evidence import (
    Evidence,
    EvidenceClass,
    evidence_class_guidance,
    group_evidence_by_class,
    make_evidence,
)


DEFAULT_EVIDENCE_TOPICS = [
    "curriculum",
    "faculty expertise",
    "facilities",
    "laboratory equipment",
    "accreditation",
    "budget",
    "strategic planning",
    "enrollment demand",
    "historical precedent",
]


@dataclass
class EvidenceGroup:
    topic: str
    summary: str
    source_numbers: List[int] = field(default_factory=list)


@dataclass
class DecisionBrief:
    question: str
    executive_summary: str
    evidence_groups: List[EvidenceGroup]
    areas_of_uncertainty: List[str]
    missing_information: List[str]
    recommended_follow_up: List[str]
    sources: List[RetrievalResult]
    evidence_items: List[Evidence]
    raw_markdown: str


def build_grouped_evidence_context(evidence_items: List[Evidence]) -> str:
    """Build source context grouped by Evidence Class for the Decision Brief prompt."""
    grouped = group_evidence_by_class(evidence_items)
    parts = []

    for evidence_class, items in grouped.items():
        if not items:
            continue

        class_parts = [f"## {evidence_class.value}"]

        for item in items:
            result = item.result
            citation = result.citation
            class_parts.append(
                f"[Source {item.source_number}]\n"
                f"Evidence Class: {item.evidence_class.value}\n"
                f"Classification Confidence: {item.confidence:.2f}\n"
                f"Classification Rationale: {item.rationale}\n"
                f"Title: {citation.get('title')}\n"
                f"Path: {citation.get('relative_path')}\n"
                f"Chars: {citation.get('start_char')}–{citation.get('end_char')}\n"
                f"Score: {result.score:.4f}\n\n"
                f"{result.text}"
            )

        parts.append("\n\n".join(class_parts))

    return "\n\n" + ("\n\n" + "-" * 70 + "\n\n").join(parts)


def build_decision_brief_prompt(
    question: str,
    evidence_context: str,
    evidence_topics: Optional[List[str]] = None,
) -> str:
    if evidence_topics is None:
        evidence_topics = DEFAULT_EVIDENCE_TOPICS

    topics = "\n".join(f"- {topic}" for topic in evidence_topics)

    return f"""
You are generating an institutional Decision Brief using only the provided sources.

Rules:
- Use only the provided sources.
- Cite claims inline using [Source N].
- Respect the Evidence Class of each source when reasoning.
- Do not treat external comparator evidence as evidence about CNU.
- Use External Standards for requirements or expectations, not as proof of CNU capacity.
- Distinguish evidence from inference.
- Do not invent information that is not in the sources.
- If evidence is missing, say so explicitly.
- Be useful to a university decision maker, but do not make the decision.

Institutional Question:
{question}

Evidence topics to look for:
{topics}

Evidence Class Guidance:
{evidence_class_guidance()}

Sources grouped by Evidence Class:
{evidence_context}

Write a Decision Brief with exactly these sections:

# Decision Brief

## Executive Summary

## Institutional Question

## Evidence Summary

## Evidence Classes Used

Summarize how Institutional Evidence, Planning Documents, Historical Documents, External Standards, External Comparators, and Background Knowledge were used. If a class was not present, say so.

## Supporting Evidence

### Curriculum

### Faculty Expertise

### Facilities and Laboratory Space

### Laboratory Equipment

### Accreditation

### Budget and Staffing

### Strategic Planning and Enrollment

### Historical Precedent

## Areas of Agreement

## Areas of Uncertainty

## Missing Information

## Strategic Considerations

## Recommended Follow-Up

## Sources Used

Group sources by Evidence Class.
""".strip()


def generate_decision_brief(
    question,
    vector_db_dir,
    model_name,
    embedding_device,
    llm_base_url,
    llm_model,
    top_k=12,
    fetch_k=100,
    dedupe_by="relative_path",
    rerank=False,
    reranker_model=None,
    reranker_device="cuda",
    min_rerank_score=None,
    return_trace=False,
):
    """
    Generate a first-pass institutional Decision Brief.

    This is intentionally parallel to app.rag.answer_question(), but separate
    from it. The QA pipeline remains optimized for concise grounded answers.
    The Decision Brief pipeline retrieves a broader evidence set and asks the
    LLM to organize the evidence into decision-support sections.

    Version 0.1 deliberately does not attempt clustering, scenario modeling,
    confidence scoring, or structured JSON extraction. Those should be added
    after DB-001 reveals the next real bottlenecks.
    """
    question = question.strip()

    retrieved = retrieve(
        query=question,
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

    evidence_items = make_evidence(results)
    evidence_context = build_grouped_evidence_context(evidence_items)
    prompt = build_decision_brief_prompt(question, evidence_context)

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

    brief_markdown = response.choices[0].message.content

    # Structured fields will become more meaningful after we add JSON-mode or
    # section parsing. For v0.1, the markdown is the canonical brief artifact.
    brief = DecisionBrief(
        question=question,
        executive_summary="",
        evidence_groups=[],
        areas_of_uncertainty=[],
        missing_information=[],
        recommended_follow_up=[],
        sources=results,
        evidence_items=evidence_items,
        raw_markdown=brief_markdown,
    )

    if return_trace:
        return brief, results, retrieval_report, trace, profile

    return brief, results, profile
