from __future__ import annotations

import pandas as pd

from app.observatory.metrics import ObservatoryAssessment


def _pct(value: float) -> str:
    return f"{100 * value:.0f}%"


def render_observatory_assessment(st, assessment: ObservatoryAssessment) -> None:
    """Render a lightweight v0.1 Observatory panel in Streamlit."""
    st.subheader("🔭 Observatory Assessment")

    st.caption(
        "A deterministic summary of the retrieved evidence landscape before the LLM writes the Decision Brief."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Decision readiness", f"{assessment.decision_readiness_score:.0f}%")
    c2.metric("Knowledge completeness", f"{assessment.knowledge_completeness_score:.0f}%")
    c3.metric("Evidence balance", f"{assessment.evidence_balance_score:.0f}%")
    c4.metric("Dominant evidence", assessment.dominant_evidence_class)

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

    r1, r2, r3 = st.columns(3)
    r1.metric("Institutional evidence", _pct(assessment.institutional_evidence_ratio))
    r2.metric("Planning reliance", _pct(assessment.planning_ratio))
    r3.metric("External dependence", _pct(assessment.external_ratio))

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
