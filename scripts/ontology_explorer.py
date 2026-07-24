#!/usr/bin/env python3
"""ISO Ontology Explorer: a developer event display for semantic objects."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ontology_explorer import (  # noqa: E402
    OntologyExplorerRegistry,
    OntologyObjectRepository,
)


def _arguments():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--objects-dir",
        type=Path,
        default=Path(
            os.environ.get(
                "ISO_ONTOLOGY_OBJECTS_DIR",
                "storage/semantic/contributions/departments",
            )
        ),
    )
    return parser.parse_known_args()[0]


@st.cache_data(show_spinner=False)
def _load(root: str, directory_fingerprint: tuple[tuple[str, int, int], ...]):
    del directory_fingerprint
    return OntologyObjectRepository().load_directory(Path(root))


def _directory_fingerprint(root: Path):
    if not root.exists():
        return ()
    return tuple(
        (item.name, item.stat().st_size, item.stat().st_mtime_ns)
        for item in sorted(root.glob("*.json"))
    )


def main():
    args = _arguments()
    st.set_page_config(
        page_title="ISO Ontology Explorer",
        page_icon="🔬",
        layout="wide",
    )
    st.title("ISO Ontology Explorer")
    st.caption(
        "Developer instrument for inspecting reconstructed semantic objects. "
        "No interpretation, evaluation, or executive reporting."
    )

    configured = st.sidebar.text_input(
        "Canonical ontology-object directory",
        value=str(args.objects_dir),
    )
    root = Path(configured).expanduser()
    registry = OntologyExplorerRegistry.default()
    st.sidebar.caption(
        "Supported object types: "
        + ", ".join(registry.supported_object_types)
    )
    if st.sidebar.button("Reload canonical objects"):
        st.cache_data.clear()
        st.rerun()
    result = _load(str(root), _directory_fingerprint(root))
    if result.errors:
        for error in result.errors:
            st.error(error)
    if result.ignored_paths:
        with st.sidebar.expander(
            f"Ignored JSON objects ({len(result.ignored_paths)})"
        ):
            for path in result.ignored_paths:
                st.code(str(path))
    if not result.objects:
        st.warning(
            "No supported canonical semantic objects were loaded. Generate "
            "DepartmentContributionKnowledgeObjects with "
            "scripts/inspect_department_contributions.py or select their "
            "existing directory."
        )
        return

    object_types = sorted({item.object_type for item in result.objects})
    selected_type = st.sidebar.selectbox("Semantic object type", object_types)
    candidates = tuple(
        item for item in result.objects if item.object_type == selected_type
    )
    selected_index = st.sidebar.selectbox(
        "Governed semantic object",
        range(len(candidates)),
        format_func=lambda index: (
            f"{candidates[index].display_label} · "
            f"{candidates[index].semantic_object.entity.entity_id}"
        ),
    )
    selected = candidates[selected_index]
    adapter = registry.adapter(selected.adapter_id)
    value = selected.semantic_object
    predicates = sorted(
        {assertion.predicate.value for assertion in value.assertions}
    )
    selected_predicates = st.sidebar.multiselect(
        "Predicate visibility",
        predicates,
        default=predicates,
        help="Filters the event display only. It does not alter the object.",
    )
    target_types = sorted(
        {assertion.object.entity_type for assertion in value.assertions}
    )
    selected_target_types = st.sidebar.multiselect(
        "Target entity types",
        target_types,
        default=target_types,
        help="Filters the event display only. It does not alter the object.",
    )
    visible = tuple(
        assertion
        for assertion in value.assertions
        if assertion.predicate.value in selected_predicates
        and assertion.object.entity_type in selected_target_types
    )

    st.subheader(selected.display_label)
    st.code(value.entity.entity_id)
    st.caption(f"Loaded from {selected.source_path}")

    hierarchy_tab, graph_tab, canonical_tab = st.tabs(
        ("Hierarchy", "Experimental graph", "Canonical JSON")
    )
    with hierarchy_tab:
        _render_identity(value)
        st.markdown("### Contribution assertions")
        st.caption(
            f"Displaying {len(visible)} of {len(value.assertions)} assertions. "
            "Filters change only this projection."
        )
        for assertion in visible:
            _render_assertion(assertion)
        with st.expander("Complete machine hierarchy"):
            st.json(adapter.hierarchy(value), expanded=2)

    with graph_tab:
        st.caption(
            "Each directed edge is one ContributionAssertion. The graph is a "
            "projection of the canonical object, not an inferred network."
        )
        graph = adapter.graph(value)
        st.graphviz_chart(
            graph.to_dot(selected_predicates, selected_target_types),
            width="stretch",
        )
        with st.expander("Graph edges and assertion fingerprints"):
            st.json(
                [
                    {
                        "assertion_id": edge.edge_id,
                        "subject": edge.subject_id,
                        "predicate": edge.predicate,
                        "object": edge.object_id,
                        "assertion_fingerprint": edge.assertion_fingerprint,
                    }
                    for edge in graph.edges
                    if edge.predicate in selected_predicates
                    and next(
                        node.entity_type
                        for node in graph.nodes
                        if node.entity_id == edge.object_id
                    )
                    in selected_target_types
                ],
                expanded=1,
            )

    with canonical_tab:
        st.caption(
            "Exact canonical serialization. Display filters do not alter it."
        )
        st.code(adapter.canonical_json(value), language="json")


def _render_identity(value):
    left, right = st.columns(2)
    with left:
        st.markdown("### Governed entity")
        st.json(value.entity.to_dict(), expanded=2)
    with right:
        st.markdown("### Object identity")
        st.code(value.contribution_object_id)
        st.write("**Ontology version**")
        st.code(value.ontology_version)
        st.write("**Deterministic fingerprint**")
        st.code(value.deterministic_fingerprint)
    temporal, provenance = st.columns(2)
    with temporal:
        st.markdown("### Temporal scope")
        st.json(value.temporal_scope.to_dict(), expanded=2)
    with provenance:
        st.markdown("### Provenance")
        st.json(dict(value.provenance), expanded=2)


def _render_assertion(assertion):
    label = (
        f"{assertion.subject.published_name or assertion.subject.entity_id} "
        f"— {assertion.predicate.value} → "
        f"{assertion.object.published_name or assertion.object.entity_id}"
    )
    with st.expander(label):
        st.markdown("#### Subject → Predicate → Object")
        st.json(
            {
                "subject": assertion.subject.to_dict(),
                "predicate": assertion.predicate.value,
                "object": assertion.object.to_dict(),
            },
            expanded=3,
        )
        st.write("**Assertion ID**")
        st.code(assertion.assertion_id)
        st.write("**Assertion fingerprint**")
        st.code(assertion.deterministic_fingerprint)
        scope, qualifiers = st.columns(2)
        with scope:
            st.markdown("#### Temporal scope")
            st.json(assertion.temporal_scope.to_dict(), expanded=2)
        with qualifiers:
            st.markdown("#### Qualifiers")
            st.json(dict(assertion.qualifiers), expanded=2)
        st.markdown("#### Contribution measures")
        if assertion.measures:
            for measure in assertion.measures:
                st.json(measure.to_dict(), expanded=2)
        else:
            st.caption("No measures attached.")
        st.markdown("#### Evidence bindings")
        for binding in assertion.evidence_bindings:
            payload = binding.to_dict()
            payload["evidence_fitness"] = list(
                binding.provenance.get("evidence_fitness") or ()
            )
            st.json(payload, expanded=2)
        st.markdown("#### Provenance")
        st.json(dict(assertion.provenance), expanded=2)


if __name__ == "__main__":
    main()
