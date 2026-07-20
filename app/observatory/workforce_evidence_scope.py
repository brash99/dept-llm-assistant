"""Scope-aware qualification of Academic Workforce Planning evidence."""

from __future__ import annotations

from typing import Sequence

from app.document_family import document_family_key
from app.evidence import Evidence, EvidenceClass, evidence_role_label
from app.question_scope import QuestionScope


_BROAD_SCOPE_TERMS = (
    "institution-wide", "institution wide", "university-wide", "university wide",
    "all departments", "by department", "across departments", "faculty roster",
)
_FINANCIAL_DECISION_TERMS = (
    "faculty salary", "faculty compensation", "salary savings", "projected savings",
    "faculty-line cost", "faculty line cost", "departmental budget",
    "adjunct replacement cost", "revenue effect", "scenario-specific",
)
_DIRECT_FACULTY_TERMS = (
    "faculty headcount", "faculty fte", "faculty roster", "faculty members",
    "faculty lines", "staffing level", "teaching load",
)


def _text(item: Evidence) -> str:
    citation = item.result.citation or {}
    return " ".join(
        str(value)
        for value in (
            citation.get("title"), citation.get("relative_path"),
            citation.get("source_path"), item.result.text,
        )
        if value
    ).casefold()


def _supporting_items(
    keywords: Sequence[str], evidence_items: Sequence[Evidence]
) -> list[Evidence]:
    return [
        item for item in evidence_items
        if any(keyword.casefold() in _text(item) for keyword in keywords)
    ]


def qualify_workforce_domain(
    *,
    topic: str,
    keywords: Sequence[str],
    evidence_items: Sequence[Evidence],
    question_scope: QuestionScope,
    grade: str,
    score: float,
) -> tuple[str, float, dict[str, object]]:
    """Cap keyword support when it does not fit the decision's scope."""
    items = _supporting_items(keywords, evidence_items)
    families = {document_family_key(item.result) for item in items}
    roles = tuple(dict.fromkeys(evidence_role_label(item) for item in items))
    texts = [_text(item) for item in items]
    broad_items = [item for item, text in zip(items, texts) if any(term in text for term in _BROAD_SCOPE_TERMS)]
    institutional_items = [item for item in items if item.evidence_class == EvidenceClass.INSTITUTIONAL]

    scope_value = (
        "institution-wide" if broad_items
        else "single-unit or program-specific" if institutional_items
        else "generic external or contextual"
    )
    breadth = (
        "comprehensive" if broad_items and len(families) >= 3
        else "multi-unit but incomplete" if broad_items
        else "isolated unit" if institutional_items
        else "generic or non-unit-specific"
    )
    directness = "keyword or conceptual mention only"
    limitation = ""

    if question_scope != QuestionScope.INSTITUTION_WIDE:
        return grade, score, {
            "directness": directness,
            "evidence_scope": scope_value,
            "authority_roles": roles,
            "coverage_breadth": breadth,
            "unique_document_families": len(families),
        }

    if topic == "Faculty Capacity":
        direct = [text for text in texts if any(term in text for term in _DIRECT_FACULTY_TERMS)]
        directness = "direct quantitative or staffing evidence" if direct else directness
        if not broad_items:
            if direct:
                grade, score = "partial", min(score, 0.65)
                limitation = "Evidence is direct but limited to one academic unit."
            elif items:
                grade, score = "weak", min(score, 0.30)
                limitation = "Faculty concepts are present, but institution-wide staffing coverage is absent."

    elif topic == "Financial Implications":
        direct = [text for text in texts if any(term in text for term in _FINANCIAL_DECISION_TERMS)]
        if direct:
            directness = "direct decision-specific financial evidence"
        elif items:
            grade, score = "weak", min(score, 0.30)
            limitation = "Financial concepts are present, but no decision-specific cost evidence was retrieved."

    elif topic == "Accreditation and External Constraints":
        formal = [item for item in items if evidence_role_label(item) == "Formal External Standard"]
        local = [item for item in items if item.evidence_class == EvidenceClass.INSTITUTIONAL]
        directness = "direct qualitative external constraint evidence" if formal else directness
        if items and (not formal or not local):
            grade, score = "partial", min(score, 0.65)
            limitation = (
                "Sources establish an external constraint but not current unit-level compliance, "
                "local margin, or institution-wide applicability."
            )

    elif grade == "strong" and not broad_items:
        grade, score = "partial", min(score, 0.65)
        limitation = "Evidence is present but does not provide institution-wide comparative coverage."

    # Repeated chunks or revisions from one family cannot corroborate one another.
    if grade == "strong" and len(families) < 2:
        grade, score = "partial", min(score, 0.65)
        limitation = limitation or "Support comes from one document family and lacks independent corroboration."

    if items and len(families) == 1:
        # Multiple chunks or revisions from one family may add keyword breadth,
        # but they do not provide independent source corroboration.
        score = min(score, 0.52)

    return grade, score, {
        "directness": directness,
        "evidence_scope": scope_value,
        "authority_roles": roles,
        "coverage_breadth": breadth,
        "unique_document_families": len(families),
        "scope_limitation": limitation,
    }


__all__ = ["qualify_workforce_domain"]
