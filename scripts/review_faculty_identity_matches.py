#!/usr/bin/env python3
"""Review proposed schedule-to-workforce faculty identity matches in Streamlit."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytical_workforce import (  # noqa: E402
    AnalyticalWorkforceBuilder,
    AnalyticalWorkforcePolicy,
    load_overrides,
)
from app.faculty_identity import FacultyIdentityService  # noqa: E402
from app.faculty_identity_review import (  # noqa: E402
    FacultyIdentityMatchReviewService,
    load_match_reviews,
    save_match_review,
)
from app.metric_readiness_audit import load_normalized_objects  # noqa: E402


def _arguments():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--normalized-root", type=Path, default=Path("storage/normalized"))
    parser.add_argument("--policy", type=Path, default=Path("config/analytical_workforce_policy.yaml"))
    parser.add_argument("--overrides", type=Path, default=Path("config/analytical_workforce_overrides.yaml"))
    parser.add_argument("--aliases", type=Path, default=Path("config/faculty_identity_aliases.yaml"))
    parser.add_argument("--reviews", type=Path, default=Path("config/faculty_identity_match_reviews.yaml"))
    parser.add_argument("--reviewer", default="Edward Brash")
    return parser.parse_known_args()[0]


@st.cache_data(show_spinner=False)
def _load_objects(root: str):
    objects, integrity = load_normalized_objects(Path(root))
    if integrity["invalid_json_count"]:
        raise ValueError("Normalized corpus contains invalid JSON")
    return objects


@st.cache_data(show_spinner=False)
def _build_base_proposals(normalized_root: str, policy_path: str, overrides_path: str):
    objects = _load_objects(normalized_root)
    identities = FacultyIdentityService().audit(objects).identities
    decisions, _ = AnalyticalWorkforceBuilder(
        AnalyticalWorkforcePolicy.load(Path(policy_path)),
        load_overrides(Path(overrides_path)),
    ).build(objects)
    return FacultyIdentityMatchReviewService().propose(
        objects, identities, decisions
    )


def _proposal_rows(proposals):
    return [{
        "Schedule name": item.schedule_name,
        "Candidate workforce name": item.workforce_name,
        "Unit": item.workforce_academic_unit_name,
        "Score": item.score,
        "Sections": item.schedule_section_count,
        "SCH": item.schedule_sch,
        "Prior decision": item.prior_decision or "unreviewed",
    } for item in proposals]


def main():
    args = _arguments()
    st.set_page_config(
        page_title="Faculty Identity Governance Review",
        layout="wide",
    )
    st.title("Faculty Identity Governance Review")
    st.caption(
        "Candidates are deterministic proposals only. No identity is merged "
        "until an institutional reviewer approves it."
    )
    if st.sidebar.button("Rebuild identities after approvals"):
        st.cache_data.clear()
        st.rerun()
    with st.spinner("Building current identity and workforce evidence…"):
        base_proposals = _build_base_proposals(
            str(args.normalized_root), str(args.policy), str(args.overrides)
        )
        reviews = load_match_reviews(args.reviews)
        reviews_by_id = {
            item["proposal_id"]: item for item in reviews
        }
        proposals = tuple(
            replace(
                item,
                prior_decision=reviews_by_id.get(
                    item.proposal_id, {}
                ).get("decision"),
                prior_review=reviews_by_id.get(item.proposal_id),
            )
            for item in base_proposals
        )

    status = st.radio(
        "Show proposals",
        ("Unreviewed", "Needs more evidence", "Rejected", "All"),
        horizontal=True,
    )
    selected = tuple(
        item for item in proposals
        if status == "All"
        or (status == "Unreviewed" and item.prior_decision is None)
        or (
            status == "Needs more evidence"
            and item.prior_decision == "needs_more_evidence"
        )
        or (status == "Rejected" and item.prior_decision == "rejected")
    )
    st.write(
        f"**{len(selected)} shown** · {len(proposals)} total candidate pairs · "
        f"{sum(item.prior_decision is None for item in proposals)} unreviewed"
    )
    if not selected:
        st.success("No proposals remain in this view.")
        return

    labels = [
        f"{item.schedule_name} → {item.workforce_name} "
        f"({item.score:.1f}, {item.workforce_academic_unit_name or 'unit unknown'})"
        for item in selected
    ]
    index = st.selectbox(
        "Candidate",
        range(len(selected)),
        format_func=lambda value: labels[value],
    )
    proposal = selected[index]

    left, middle, right = st.columns(3)
    left.metric("Schedule identity", proposal.schedule_name)
    middle.metric("Candidate workforce identity", proposal.workforce_name)
    right.metric("Proposal score", f"{proposal.score:.1f}")
    st.write(f"**Department/unit:** {proposal.workforce_academic_unit_name or 'Unknown'}")
    st.write(
        "**Why proposed:** "
        + ", ".join(f"`{reason}`" for reason in proposal.proposal_reasons)
    )
    if proposal.prior_review:
        st.info(
            "Prior decision: "
            f"**{proposal.prior_decision}** by "
            f"{proposal.prior_review.get('reviewer')} on "
            f"{proposal.prior_review.get('review_date')}. "
            f"{proposal.prior_review.get('notes') or ''}"
        )

    st.subheader("Current directory evidence")
    st.write(
        "**Published directory name:** "
        + (", ".join(proposal.candidate_directory_names) or "Not published")
    )
    st.write(
        "**Email:** "
        + (", ".join(proposal.candidate_email_addresses) or "Not published")
    )
    st.write(
        "**Profile:** "
        + (", ".join(proposal.candidate_profile_sources) or "Not published")
    )

    st.subheader("Schedule evidence")
    schedule_data = {
        "Terms": ", ".join(proposal.schedule_terms),
        "Sections": proposal.schedule_section_count,
        "Prefixes": ", ".join(proposal.schedule_prefixes),
        "SCH": proposal.schedule_sch,
    }
    st.dataframe([schedule_data], hide_index=True, use_container_width=True)
    with st.expander("Schedule observation IDs"):
        st.code("\n".join(proposal.schedule_observation_ids))

    st.subheader("Catalog and roster evidence")
    if proposal.catalog_and_roster_evidence:
        st.dataframe(
            proposal.catalog_and_roster_evidence,
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.write("No catalog or department-roster evidence is linked to the candidate.")

    notes = st.text_area("Review notes", key=f"notes:{proposal.proposal_id}")
    approve, reject, defer = st.columns(3)
    if approve.button(
        "Approve same person",
        type="primary",
        use_container_width=True,
    ):
        save_match_review(
            proposal, "approved", args.reviewer,
            alias_path=args.aliases, review_path=args.reviews, notes=notes,
        )
        st.success("Approved. Governed alias saved; rebuilding will merge the identities.")
        st.rerun()
    if reject.button("Reject", use_container_width=True):
        save_match_review(
            proposal, "rejected", args.reviewer,
            alias_path=args.aliases, review_path=args.reviews, notes=notes,
        )
        st.warning("Rejected proposal saved.")
        st.rerun()
    if defer.button("Needs more evidence", use_container_width=True):
        save_match_review(
            proposal, "needs_more_evidence", args.reviewer,
            alias_path=args.aliases, review_path=args.reviews, notes=notes,
        )
        st.info("Deferred decision saved.")
        st.rerun()

    with st.expander("Candidate queue"):
        st.dataframe(
            _proposal_rows(selected),
            hide_index=True,
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
