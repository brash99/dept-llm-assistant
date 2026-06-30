from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd

from app.observatory.metrics import ObservatoryAssessment


def _pct(value: float) -> str:
    return f"{100 * value:.0f}%"


def _score_label(score: float) -> str:
    if score >= 85:
        return "Strong"
    if score >= 70:
        return "Moderate-high"
    if score >= 55:
        return "Moderate"
    if score >= 40:
        return "Limited"
    return "Weak"


def _safe_report_value(report: Dict[str, Any], key: str, default: Any = None) -> Any:
    value = report.get(key, default)
    return default if value is None else value


def _progress_metric(st, label: str, score: float, help_text: str | None = None) -> None:
    st.metric(label, f"{score:.0f}%", help=help_text)
    st.progress(max(0.0, min(1.0, score / 100.0)))
    st.caption(_score_label(score))


def _infer_domain_counts(report: Dict[str, Any]) -> Dict[str, int]:
    """Infer a first-pass semantic-domain profile from top-folder chunk counts.

    This is intentionally simple and deterministic for the ISO Overview v0.1.
    It uses corpus folder labels as a proxy for institutional semantic domains.
    """
    by_folder: Iterable[Tuple[str, int]] = report.get("by_folder", []) or []

    domain_keywords: Dict[str, List[str]] = {
        "Curriculum": ["curriculum", "syllabi", "course", "catalog"],
        "Assessment": ["assessment", "abet", "accreditation", "uac"],
        "Planning": ["planning", "program review", "annual reports", "strategic"],
        "Governance": ["senate", "department meetings", "committee", "minutes"],
        "Budget": ["budget", "finance", "initiative", "initiatives"],
        "Facilities": ["facilities", "serc", "space", "building", "makerspace"],
        "Faculty": ["faculty", "annual reports", "hiring", "workload"],
        "Students / Enrollment": ["enrollment", "admissions", "student", "advising"],
        "Research": ["research", "grants", "jlab", "publications"],
    }

    counts = {domain: 0 for domain in domain_keywords}

    for folder, chunks in by_folder:
        folder_text = str(folder).lower()
        for domain, keywords in domain_keywords.items():
            if any(keyword in folder_text for keyword in keywords):
                counts[domain] += int(chunks)

    return counts


def _domain_coverage_rows(domain_counts: Dict[str, int]) -> list[dict[str, Any]]:
    max_count = max(domain_counts.values()) if domain_counts else 0
    rows: list[dict[str, Any]] = []

    for domain, count in domain_counts.items():
        if max_count > 0:
            coverage = round(100.0 * count / max_count, 1)
        else:
            coverage = 0.0

        if coverage >= 70:
            status = "Strong"
        elif coverage >= 40:
            status = "Moderate"
        elif count > 0:
            status = "Limited"
        else:
            status = "No signal"

        rows.append(
            {
                "Domain": domain,
                "Signal": count,
                "Relative coverage": f"{coverage:.0f}%",
                "Status": status,
            }
        )

    return sorted(rows, key=lambda row: row["Signal"], reverse=True)


def _estimate_global_scores(report: Dict[str, Any]) -> dict[str, float]:
    documents = float(_safe_report_value(report, "documents", 0) or 0)
    chunks = float(_safe_report_value(report, "total_chunks", 0) or 0)
    gini = float(_safe_report_value(report, "gini", 0.0) or 0.0)
    dominance = report.get("dominance", {}) or {}
    top_1 = float(dominance.get(1, 0.0) or dominance.get("1", 0.0) or 0.0)
    top_10 = float(dominance.get(10, 0.0) or dominance.get("10", 0.0) or 0.0)

    domain_counts = _infer_domain_counts(report)
    represented_domains = sum(1 for count in domain_counts.values() if count > 0)
    domain_coverage = 100.0 * represented_domains / max(1, len(domain_counts))

    # Transparent v0.1 heuristics. These should become calibrated once the
    # global observatory has a richer corpus-level evidence model.
    scale_score = min(100.0, 40.0 + 20.0 * (documents > 1000) + 20.0 * (documents > 5000) + 20.0 * (chunks > 100000))
    balance_score = max(0.0, 100.0 - 70.0 * gini - 100.0 * top_1 - 25.0 * top_10)
    ecosystem_health = max(0.0, min(100.0, 0.45 * scale_score + 0.35 * balance_score + 0.20 * domain_coverage))
    decision_readiness = max(0.0, min(100.0, 0.55 * ecosystem_health + 0.45 * domain_coverage))

    return {
        "ecosystem_health": round(ecosystem_health, 1),
        "semantic_coverage": round(domain_coverage, 1),
        "evidence_balance": round(balance_score, 1),
        "decision_readiness": round(decision_readiness, 1),
    }


def render_iso_overview(st, report: Dict[str, Any]) -> None:
    """Render the global ISO Overview page.

    This is a corpus-level observatory: it exists before the user asks a
    question. It describes the current state of the semantic ecosystem using
    deterministic metrics available from the corpus observatory report.
    """
    st.subheader("🔭 ISO Overview")
    st.caption(
        "A global observatory view of the current semantic ecosystem before any specific question is asked."
    )

    documents = int(_safe_report_value(report, "documents", 0) or 0)
    chunks = int(_safe_report_value(report, "total_chunks", 0) or 0)
    median = _safe_report_value(report, "median", "—")
    gini = float(_safe_report_value(report, "gini", 0.0) or 0.0)
    scores = _estimate_global_scores(report)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _progress_metric(
            st,
            "Ecosystem health",
            scores["ecosystem_health"],
            "A v0.1 corpus-level heuristic combining scale, balance, and semantic-domain coverage.",
        )
    c2.metric("Documents", f"{documents:,}")
    c3.metric("Chunks", f"{chunks:,}")
    c4.metric("Gini", f"{gini:.3f}", help="Higher values indicate that relatively few documents contribute many chunks.")

    st.divider()

    left, middle, right = st.columns([1.1, 1.2, 1.0])

    with left:
        st.markdown("#### Semantic coverage")
        _progress_metric(
            st,
            "Coverage",
            scores["semantic_coverage"],
            "Relative coverage across SEC semantic domains inferred from corpus folders.",
        )
        st.markdown("#### Decision readiness")
        _progress_metric(
            st,
            "Readiness",
            scores["decision_readiness"],
            "A v0.1 estimate of how prepared the current corpus is to support broad institutional questions.",
        )

    with middle:
        st.markdown("#### Coverage by institutional domain")
        domain_counts = _infer_domain_counts(report)
        domain_rows = _domain_coverage_rows(domain_counts)
        st.dataframe(pd.DataFrame(domain_rows), use_container_width=True, hide_index=True)

    with right:
        st.markdown("#### Corpus balance")
        _progress_metric(
            st,
            "Evidence balance",
            scores["evidence_balance"],
            "A v0.1 balance score penalizing chunk dominance and high corpus inequality.",
        )
        st.metric("Median chunks / document", median)
        dominance = report.get("dominance", {}) or {}
        if dominance:
            st.markdown("**Dominance**")
            st.write({
                f"Top {k}": f"{100 * v:.2f}%"
                for k, v in dominance.items()
            })

    st.divider()

    gap_col, issue_col, next_col = st.columns(3)

    domain_counts = _infer_domain_counts(report)
    weak_domains = [domain for domain, count in domain_counts.items() if count == 0]
    limited_domains = [
        row["Domain"] for row in _domain_coverage_rows(domain_counts)
        if row["Status"] in {"Limited", "No signal"}
    ]

    with gap_col:
        st.markdown("#### Known weak regions")
        if limited_domains:
            for domain in limited_domains[:6]:
                st.warning(domain)
        else:
            st.success("No obvious weak semantic regions detected in v0.1 metrics.")

    with issue_col:
        st.markdown("#### Observatory alerts")
        if gini >= 0.70:
            st.warning("Chunk distribution is highly unequal; inspect dominant documents.")
        else:
            st.success("Chunk inequality is within expected range for a mixed institutional corpus.")
        if scores["semantic_coverage"] < 70:
            st.warning("Some institutional domains appear weakly represented.")
        else:
            st.success("Most core SEC semantic domains are represented.")
        st.info("Global evidence classes will become available after corpus-level classification is added.")

    with next_col:
        st.markdown("#### Recommended next evidence sources")
        recommendations = []
        if "Budget" in limited_domains:
            recommendations.append("Approved budgets and multi-year budget history")
        if "Facilities" in limited_domains:
            recommendations.append("Facilities utilization and space planning records")
        if "Students / Enrollment" in limited_domains:
            recommendations.append("Enrollment, retention, and admissions demand data")
        if "Faculty" in limited_domains:
            recommendations.append("Faculty workload, annual reports, and staffing plans")
        if "Research" in limited_domains:
            recommendations.append("Research output, grants, and scholarly activity records")
        if not recommendations:
            recommendations = [
                "University-wide corpus expansion",
                "SCHEV and external standards data",
                "Institutional Research datasets",
            ]
        for recommendation in recommendations[:6]:
            st.write(f"- {recommendation}")

    with st.expander("Developer details: corpus observatory tables", expanded=False):
        st.write("**Largest documents**")
        st.dataframe(report.get("largest", []), use_container_width=True)

        st.write("**Chunks by file type**")
        st.dataframe(
            pd.DataFrame([{"type": k, "chunks": v} for k, v in (report.get("by_type", []) or [])[:20]]),
            use_container_width=True,
            hide_index=True,
        )

        st.write("**Chunks by top folder**")
        st.dataframe(
            pd.DataFrame([{"folder": k, "chunks": v} for k, v in (report.get("by_folder", []) or [])[:20]]),
            use_container_width=True,
            hide_index=True,
        )

        st.write("**Chunks by parser**")
        st.dataframe(
            pd.DataFrame([{"parser": k, "chunks": v} for k, v in (report.get("by_parser", []) or [])]),
            use_container_width=True,
            hide_index=True,
        )


def render_observatory_assessment(st, assessment: ObservatoryAssessment) -> None:
    """Render a lightweight per-question Observatory panel in Streamlit."""
    st.subheader("🔭 Observatory Assessment")

    st.caption(
        "A deterministic summary of the retrieved evidence landscape before the LLM writes the Decision Brief."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Decision readiness", f"{assessment.decision_readiness_score:.0f}%")
    c2.metric("Knowledge completeness", f"{assessment.knowledge_completeness_score:.0f}%")
    c3.metric("Topic coverage", f"{assessment.topic_coverage_score:.0f}%")
    c4.metric("Dominant evidence", assessment.dominant_evidence_class)

    st.caption(
        "Topic coverage measures whether the retrieved evidence touches the expected semantic domains. "
        "Knowledge completeness is stricter: it is reduced when evidence is planning-heavy, externally dependent, "
        "or thin in direct institutional evidence."
    )

    st.write("**Evidence class balance**")
    rows = []
    for label, count in assessment.evidence_class_counts.items():
        if count == 0:
            continue
        rows.append(
            {
                "Evidence class": label,
                "Sources": count,
                "Share": _pct(assessment.evidence_class_percentages[label]),
            }
        )

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No evidence classes available.")

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Institutional evidence", _pct(assessment.institutional_evidence_ratio))
    r2.metric("Planning reliance", _pct(assessment.planning_ratio))
    r3.metric("External dependence", _pct(assessment.external_ratio))
    r4.metric("Evidence balance", f"{assessment.evidence_balance_score:.0f}%")

    with st.expander("Semantic coverage", expanded=False):
        if assessment.covered_topics:
            st.write("**Covered topics**")
            st.write(", ".join(assessment.covered_topics))
        if assessment.missing_topics:
            st.write("**Potential gaps**")
            st.warning(", ".join(assessment.missing_topics))
        if not assessment.covered_topics and not assessment.missing_topics:
            st.info("No topic coverage analysis available.")

    if assessment.warnings:
        with st.expander("Observatory warnings", expanded=True):
            for warning in assessment.warnings:
                st.warning(warning)

    if assessment.recommendations:
        with st.expander("Recommended evidence improvements", expanded=False):
            for recommendation in assessment.recommendations:
                st.write(f"- {recommendation}")
