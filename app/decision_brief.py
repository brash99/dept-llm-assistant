from dataclasses import dataclass, field
from typing import Dict, List, Optional

from openai import OpenAI

from app.retrieval import retrieve
from app.reasoning.query import constitutional_quota_for_query
from app.vector_index import RetrievalResult
from app.observatory.metrics import ObservatoryAssessment, build_observatory_assessment
from app.observatory.evidence_fitness import EvidenceFitnessService
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


from app.observatory.decision_brief import (
    DecisionBrief,
    DecisionBriefService,
    EvidenceGroup,
    build_decision_brief_prompt,
    build_grouped_evidence_context,
)

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
    constitutional_top_k=2,
    empirical_top_k=10,
    topology_entity_query=None,
    max_per_document_family=2,
    constitutional_orientation=None,
    decision_type=None,
    max_per_evidence_role=4,
    evidence_role_relevance_margin=0.5,
):
    """
    Generate an institutional Decision Brief knowledge product.

    This is intentionally parallel to app.rag.answer_question(), but separate
    from it. The QA pipeline remains optimized for concise grounded answers.
    The Decision Brief pipeline retrieves a broader evidence set and asks the
    LLM to organize the evidence into decision-support sections.

    Retrieval, evidence classification, Evidence Fitness, governed synthesis,
    and deterministic Dashboard V2 rendering are connected here. Scenario
    Modeling and department-level recommendation remain intentionally out of
    scope until explicit scenario services and adequate evidence exist.
    """
    question = question.strip()
    constitutional_top_k = constitutional_quota_for_query(
        question, constitutional_top_k
    )
    if decision_type is None:
        from app.observatory.evidence_fitness import EvidenceFitnessService

        classified_type, _ = EvidenceFitnessService.classify_decision_type(question)
        decision_type = classified_type.value

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

    evidence_items = make_evidence(results)

    brief = DecisionBriefService.generate(
        question=question,
        evidence_items=evidence_items,
        sources=results,
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        topology_entity_query=topology_entity_query,
        constitutional_orientation=constitutional_orientation,
    )

    if return_trace:
        return brief, results, retrieval_report, trace, profile

    return brief, results, profile
