from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
import re
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from app.vector_index import RetrievalResult


class EvidenceClass(Enum):
    """Reasoning role assigned to retrieved evidence."""

    CONSTITUTIONAL = "Constitutional Evidence"
    INSTITUTIONAL = "Institutional Evidence"
    PLANNING = "Planning Document"
    HISTORICAL = "Historical Document"
    EXTERNAL_STANDARD = "External Standard"
    EXTERNAL_COMPARATOR = "External Comparator"
    BACKGROUND = "Background Knowledge"


EVIDENCE_CLASS_ORDER = [
    EvidenceClass.CONSTITUTIONAL,
    EvidenceClass.INSTITUTIONAL,
    EvidenceClass.PLANNING,
    EvidenceClass.HISTORICAL,
    EvidenceClass.EXTERNAL_STANDARD,
    EvidenceClass.EXTERNAL_COMPARATOR,
    EvidenceClass.BACKGROUND,
]


GENERIC_SOURCE_TITLES = {
    "",
    "document",
    "word document",
    "pdf document",
    "microsoft word document",
    "untitled",
    "untitled document",
}


def resolve_source_title(result: RetrievalResult) -> str:
    """
    Return a deterministic, audit-friendly source title.

    Prefer the extracted title when meaningful. For generic parser-generated
    titles such as "Word Document", fall back to the actual source filename.
    """
    citation = result.citation or {}

    extracted_title = str(
        citation.get("title") or ""
    ).strip()

    if extracted_title.lower() not in GENERIC_SOURCE_TITLES:
        return extracted_title

    raw_path = (
        citation.get("relative_path")
        or citation.get("source_path")
        or ""
    )

    if raw_path:
        filename = PurePosixPath(
            str(raw_path).replace("\\", "/")
        ).name

        if filename:
            return filename

    return extracted_title or "Untitled source"


@dataclass
class Evidence:
    """A retrieved chunk interpreted as evidence for decision support."""

    source_number: int
    display_source_number: int
    source_kind: str
    citation_label: str
    result: RetrievalResult
    evidence_class: EvidenceClass
    confidence: float
    rationale: str

    @property
    def title(self) -> str:
        return resolve_source_title(self.result)

    @property
    def relative_path(self) -> str:
        return self.result.citation.get("relative_path") or "Unknown path"

    @property
    def score(self) -> float:
        return self.result.score


def evidence_role_label(item: "Evidence") -> str:
    """Return a claim-safe, deterministic role more specific than class."""
    text = _normalized_source_text(item.result)

    if item.evidence_class == EvidenceClass.CONSTITUTIONAL:
        return "Strategic / Constitutional Document"
    if _is_institutional_self_study(text):
        return "Institutional Self-Study"
    if item.evidence_class == EvidenceClass.EXTERNAL_STANDARD:
        return "Formal External Standard"
    if item.evidence_class == EvidenceClass.EXTERNAL_COMPARATOR:
        return "Contextual Reference"
    if item.evidence_class == EvidenceClass.PLANNING:
        return "Planning Document"
    if item.evidence_class == EvidenceClass.INSTITUTIONAL:
        if any(term in text for term in ("department", "annual report", "pcse")):
            return "Departmental Report"
        return "Institutional Operating Record"
    if item.evidence_class == EvidenceClass.HISTORICAL:
        return "Contextual Reference"
    return "Contextual Reference"


def _normalized_source_text(result: RetrievalResult) -> str:
    citation = result.citation or {}
    parts = [
        citation.get("relative_path") or "",
        citation.get("source_path") or "",
        citation.get("title") or "",
        result.metadata.get("source_collection") or "",
        result.metadata.get("collection") or "",
    ]
    return " ".join(parts).lower()


_EXTERNAL_COMPARATOR_MARKERS = (
    "sample", "purdue", "self-study report (purdue",
)
_FORMAL_ABET_STANDARD_MARKERS = (
    "abet_standards",
    "criteria for accrediting",
    "accreditation criteria",
    "general criteria",
    "program criteria",
    "formal standard",
)


def _is_institutional_self_study(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold())
    if any(marker.replace("_", " ") in normalized for marker in _FORMAL_ABET_STANDARD_MARKERS):
        return False
    if any(marker in text for marker in _EXTERNAL_COMPARATOR_MARKERS):
        return False
    if "self study" in normalized or "selfstudy" in text:
        return True
    # Locally authored criterion-response exports may omit "self-study" but
    # normally retain both a response topic and either a local program code or
    # draft/final workflow marker. A bare "ABET Criterion 5 Curriculum" title
    # is therefore not silently reclassified as an institutional response.
    criterion_response = re.search(
        r"\bcriterion\s*\d+\b.*\b(?:faculty|inst(?:itutional)?\s*support|"
        r"curriculum|students|facilities)\b",
        normalized,
    )
    local_marker = re.search(
        r"\b(?:ce|cpe|cpen|cs|cpsc|ece|ee|final|finaldraft|draft)\b",
        normalized,
    )
    return bool(criterion_response and local_marker)


def classify_evidence(result: RetrievalResult) -> tuple[EvidenceClass, float, str]:
    """
    Classify a retrieved result by evidence role.

    Version 0.1 is intentionally deterministic and path/title based. This keeps
    evidence-class assignment inspectable and reproducible while the Phase II
    reasoning pipeline is being developed.
    """
    # Constitutional objects carry institutional values and commitments.
    # This semantic identity takes precedence over path/title heuristics.
    if result.object_type == "constitutional_knowledge":
        constitutional_type = result.metadata.get(
            "constitutional_type",
            "unspecified",
        )
        return (
            EvidenceClass.CONSTITUTIONAL,
            1.00,
            (
                "Retrieved object is explicitly typed as constitutional "
                f"knowledge ({constitutional_type})."
            ),
        )

    text = _normalized_source_text(result)

    # External standards: normative agencies, accreditors, regulatory bodies.
    if any(term in text for term in ["schev", "sacscoc", "sacs", "federal"]):
        return (
            EvidenceClass.EXTERNAL_STANDARD,
            0.90,
            "Path/title references an external regulatory or oversight body.",
        )

    if "abet" in text:
        if any(term in text for term in _EXTERNAL_COMPARATOR_MARKERS):
            return (
                EvidenceClass.EXTERNAL_COMPARATOR,
                0.80,
                "Path/title indicates an ABET self-study sample from another institution.",
            )
        if _is_institutional_self_study(text):
            return (
                EvidenceClass.INSTITUTIONAL,
                0.90,
                (
                    "Path/title identifies a locally authored ABET self-study "
                    "or institutional criterion-response section."
                ),
            )
        return (
            EvidenceClass.EXTERNAL_STANDARD,
            0.85,
            "Path/title references ABET accreditation criteria or formal material.",
        )

    if _is_institutional_self_study(text):
        return (
            EvidenceClass.INSTITUTIONAL,
            0.85,
            "Path/title identifies an institutional self-study or criterion response.",
        )

    # Planning documents: intended future state, program review, strategic/budget planning.
    if any(
        term in text
        for term in [
            "planning/",
            "strategic",
            "program review",
            "major initiatives",
            "budget",
            "initiative",
            "proposal",
            "curriculum/",
            "mechatronics",
        ]
    ):
        return (
            EvidenceClass.PLANNING,
            0.80,
            "Path/title indicates institutional planning, curriculum proposal, budget, or program-review material.",
        )

    # Institutional evidence: current internal records and reports.
    if any(
        term in text
        for term in [
            "annual reports/",
            "annual report",
            "faculty handbook",
            "minutes",
            "committee",
            "department",
            "pcse",
            "cnu",
        ]
    ):
        return (
            EvidenceClass.INSTITUTIONAL,
            0.75,
            "Path/title indicates an internal institutional document.",
        )

    # Historical documents: old archives, prior years, retired material.
    if any(term in text for term in ["archive", "historical", "retired", "old"]):
        return (
            EvidenceClass.HISTORICAL,
            0.75,
            "Path/title indicates archived or historical institutional material.",
        )

    return (
        EvidenceClass.BACKGROUND,
        0.40,
        "No deterministic path/title rule matched; treated as low-authority background evidence.",
    )


def make_evidence(
    results: List[RetrievalResult],
) -> List[Evidence]:
    """
    Assign stable citation identities in retrieval order.

    Constitutional and empirical sources each receive their own numbering
    sequence. These labels must remain unchanged even when evidence is later
    grouped by class for prompt construction.
    """
    evidence_items: List[Evidence] = []

    constitutional_number = 0
    empirical_number = 0

    for source_number, result in enumerate(results, start=1):
        evidence_class, confidence, rationale = classify_evidence(
            result
        )

        if result.object_type == "constitutional_knowledge":
            constitutional_number += 1
            display_source_number = constitutional_number
            source_kind = "Constitutional Source"
        else:
            empirical_number += 1
            display_source_number = empirical_number
            source_kind = "Empirical Source"

        citation_label = (
            f"{source_kind} {display_source_number}"
        )

        result.metadata["evidence_class"] = evidence_class.value
        result.metadata["evidence_class_confidence"] = confidence
        result.metadata["evidence_class_rationale"] = rationale
        # This narrower role is serialized into the governed prompt so the
        # model cannot silently generalize a local narrative into a standard.
        result.metadata["source_kind"] = source_kind
        result.metadata["display_source_number"] = (
            display_source_number
        )
        result.metadata["citation_label"] = citation_label
        result.metadata["display_title"] = resolve_source_title(result)

        evidence_items.append(
            Evidence(
                source_number=source_number,
                display_source_number=display_source_number,
                source_kind=source_kind,
                citation_label=citation_label,
                result=result,
                evidence_class=evidence_class,
                confidence=confidence,
                rationale=rationale,
            )
        )

        result.metadata["evidence_role"] = evidence_role_label(
            evidence_items[-1]
        )

    return evidence_items


def group_evidence_by_class(evidence_items: List[Evidence]) -> Dict[EvidenceClass, List[Evidence]]:
    grouped: Dict[EvidenceClass, List[Evidence]] = {
        evidence_class: [] for evidence_class in EVIDENCE_CLASS_ORDER
    }

    for item in evidence_items:
        grouped[item.evidence_class].append(item)

    return grouped


def evidence_class_guidance() -> str:
    return """
Evidence classes define how sources should be used in reasoning:

- Constitutional Evidence: institutional values, commitments, mission, and strategic directions. These guide normative reasoning but do not by themselves establish empirical facts.
- Institutional Evidence: authoritative information about CNU's current or recent internal state.
- Planning Documents: internal documents describing proposals, intended future actions, strategy, budgets, or program development.
- Historical Documents: older or archived documents useful for precedent, but not necessarily current policy.
- External Standards: external requirements, accreditor criteria, regulatory guidance, or state-level expectations.
- External Comparators: examples from peer or comparator institutions; useful for context but not evidence about CNU.
- Background Knowledge: general context with the lowest authority; use only when clearly identified as general knowledge.
""".strip()
