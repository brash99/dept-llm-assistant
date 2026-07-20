import streamlit as st
from pathlib import Path

from app.config import load_config
from app.rag import answer_question
from app.decision_brief import generate_decision_brief
from app.observatory.dashboard import (
    render_iso_overview,
    render_observatory_assessment,
    render_evidence_fitness,
)
from app.evidence import resolve_source_title
from app.source_presentation import executive_source_label
from app.constitution import (
    ConstitutionalCatalog,
    ConstitutionalOrientation,
    ConstitutionalOrientationService,
)

from app.corpus_observatory import analyze_corpus
from app.control_plane.catalog import ProgramCatalog
from app.control_plane.resolver import ProgramResolver
from app.control_plane.semantic_neighbors import (
    SemanticProgramNeighborhoodService,
)
from app.control_plane.orientation import (
    InstitutionalOrientation,
    ProgramOrientationService,
)
from app.control_plane.dual_orientation import (
    SemanticControlPlaneResult,
    SemanticControlPlaneService,
)
from app.acquisition import (
    AcquisitionManifest,
    WebObserverCatalog,
)


def find_program_catalog_path(config: dict, project_root: Path) -> Path:
    """
    Locate the asserted institutional program catalog.

    A configured path takes precedence. Fallback locations support the
    current development repository without coupling the control plane
    permanently to one directory layout.
    """
    control_plane_cfg = config.get("control_plane", {})
    configured_path = control_plane_cfg.get("program_catalog")

    if configured_path:
        candidate = Path(configured_path)

        if not candidate.is_absolute():
            candidate = project_root / candidate

        if not candidate.exists():
            raise FileNotFoundError(
                f"Configured program catalog does not exist: {candidate}"
            )

        return candidate

    preferred_candidates = [
        project_root / "config" / "institutional_programs.yaml",
        project_root / "config" / "programs.yaml",
        project_root / "config" / "program_catalog.yaml",
        project_root / "data" / "programs.yaml",
        project_root / "data" / "program_catalog.yaml",
        project_root / "app" / "control_plane" / "programs.yaml",
        project_root / "app" / "control_plane" / "program_catalog.yaml",
    ]

    for candidate in preferred_candidates:
        if candidate.exists():
            return candidate

    discovered = []

    for pattern in (
        "**/programs.yaml",
        "**/program_catalog.yaml",
        "**/programs.yml",
        "**/program_catalog.yml",
    ):
        discovered.extend(project_root.glob(pattern))

    discovered = sorted(set(discovered))

    if len(discovered) == 1:
        return discovered[0]

    if not discovered:
        raise FileNotFoundError(
            "No program catalog was found. Add "
            "'control_plane.program_catalog' to settings.yaml."
        )

    raise RuntimeError(
        "Multiple possible program catalogs were found. Set "
        "'control_plane.program_catalog' in settings.yaml. Candidates: "
        + ", ".join(str(candidate) for candidate in discovered)
    )


@st.cache_resource(show_spinner=False)
def load_semantic_control_plane(
    catalog_path: str,
    model_name: str,
    device: str,
    neighbor_limit: int,
):
    """
    Load the catalog and the Sprint 2 Semantic Control Plane service once
    per Streamlit process.
    """
    catalog = ProgramCatalog.from_yaml(Path(catalog_path))
    resolver = ProgramResolver(catalog)

    neighborhood_service = SemanticProgramNeighborhoodService(
        programs=catalog.all(),
        model_name=model_name,
        device=device,
    )

    return ProgramOrientationService(
        resolver=resolver,
        neighborhood_service=neighborhood_service,
        neighbor_limit=neighbor_limit,
    )


@st.cache_resource(show_spinner=False)
def load_dual_semantic_control_plane(
    *,
    catalog_path: str,
    model_name: str,
    device: str,
    neighbor_limit: int,
    constitutional_dir: str,
) -> SemanticControlPlaneService:
    """
    Load both empirical and constitutional orientation services once.
    """
    institutional_service = load_semantic_control_plane(
        catalog_path=catalog_path,
        model_name=model_name,
        device=device,
        neighbor_limit=neighbor_limit,
    )

    constitutional_service = (
        load_constitutional_orientation_service(
            constitutional_dir
        )
    )

    return SemanticControlPlaneService(
        institutional_service=(
            institutional_service
        ),
        constitutional_service=(
            constitutional_service
        ),
    )


def render_institutional_orientation(
    orientation: InstitutionalOrientation,
) -> None:
    """
    Render the Semantic Control Plane contract produced before retrieval.

    This panel is advisory in Sprint 2. It explains the institutional
    interpretation but does not yet alter retrieval behavior.
    """
    with st.container(border=True):
        st.subheader("🧭 Institutional Orientation")
        st.caption(
            "Semantic Control Plane interpretation generated before "
            "institutional evidence retrieval."
        )

        st.markdown(
            f"**Question Scope:** {orientation.question_scope.label}"
        )
        st.caption(orientation.question_scope.rationale)

        st.markdown("**Resolved institutional entities**")

        if orientation.resolved_entities:
            for entity in orientation.resolved_entities:
                scope_value = orientation.question_scope.scope.value
                prefix = (
                    "Contextual program reference"
                    if scope_value in {"institution_wide", "multi_entity"}
                    else "Existing program"
                )
                st.success(f"{prefix}: **{entity.name}**")

                details = []

                if entity.degree_type:
                    details.append(f"Degree type: {entity.degree_type}")

                if entity.department:
                    details.append(f"Department: {entity.department}")

                if entity.school:
                    details.append(f"School: {entity.school}")

                if details:
                    st.write(" | ".join(details))

            resolution = orientation.resolution

            st.caption(
                f"Match type: {resolution.match_type} | "
                f"Matched phrase: {resolution.matched_phrase!r} | "
                f"Resolution confidence: {resolution.confidence:.2f}"
            )
        else:
            st.write("No existing cataloged program was resolved.")

        if orientation.resolution.diagnostics:
            st.markdown("**Resolution diagnostics**")
            for diagnostic in orientation.resolution.diagnostics:
                st.caption(diagnostic)

        st.markdown("**Proposed institutional concepts**")

        if orientation.proposed_concepts:
            for concept in orientation.proposed_concepts:
                structure_label = concept.concept_type.removeprefix(
                    "academic_"
                ).replace("_", " ").capitalize()

                st.info(
                    f"Proposed {structure_label}: **{concept.name}**\n\n"
                    "This concept is not asserted as an existing program "
                    "in the institutional catalog."
                )

                st.caption(
                    f"Concept type: {concept.concept_type} | "
                    f"Extraction method: {concept.extraction_method} | "
                    f"Confidence: {concept.confidence:.2f}"
                )
        else:
            st.write("No proposed academic-structure concept was identified.")

        st.markdown("**Semantic program neighborhood**")

        if orientation.semantic_neighbors:
            rows = []

            for rank, neighbor in enumerate(
                orientation.semantic_neighbors,
                start=1,
            ):
                program = neighbor.program

                rows.append(
                    {
                        "Rank": rank,
                        "Program": program.name,
                        "Degree type": program.degree_type or "",
                        "Department": program.department or "",
                        "School": program.school or "",
                        "Similarity": round(neighbor.score, 4),
                        "Method": neighbor.method,
                    }
                )

            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("No semantic program neighbors were produced.")

        if orientation.notes:
            st.markdown("**Orientation notes**")

            for note in orientation.notes:
                st.write(f"- {note}")

        st.caption(
            f"Overall orientation confidence: "
            f"{orientation.confidence:.2f}"
        )


def summarize_acquisition_manifest(
    manifest_path: Path,
) -> dict:
    """
    Summarize one append-only SourceDocument manifest.
    """
    manifest = AcquisitionManifest(manifest_path)

    documents = manifest.read_all()
    latest_documents = manifest.latest_documents()

    versions_by_path = {}

    for document in documents:
        versions_by_path.setdefault(
            document.relative_path,
            [],
        ).append(document)

    paths_by_hash = {}

    for document in latest_documents:
        paths_by_hash.setdefault(
            document.content_hash,
            [],
        ).append(document.relative_path)

    duplicate_groups = {
        content_hash: paths
        for content_hash, paths in paths_by_hash.items()
        if len(paths) > 1
    }

    duplicate_paths = sum(
        len(paths) - 1
        for paths in duplicate_groups.values()
    )

    versioned_paths = sum(
        1
        for versions in versions_by_path.values()
        if len(versions) > 1
    )

    acquired_at_values = [
        document.acquired_at
        for document in documents
    ]

    latest_acquired_at = (
        max(acquired_at_values)
        if acquired_at_values
        else None
    )

    return {
        "manifest_path": manifest_path,
        "records": len(documents),
        "current_paths": len(latest_documents),
        "duplicate_paths": duplicate_paths,
        "duplicate_groups": duplicate_groups,
        "versioned_paths": versioned_paths,
        "latest_acquired_at": latest_acquired_at,
        "documents": documents,
        "latest_documents": latest_documents,
    }


def render_acquisition_overview(
    project_root: Path,
) -> None:
    """
    Render telemetry for all configured institutional observers.

    This panel reads acquisition manifests only. It does not acquire,
    normalize, embed, or modify retrieval behavior.
    """
    st.subheader("📡 Distributed Institutional Observation")
    st.caption(
        "Governed observers contributing SourceDocuments to unified "
        "Institutional Memory."
    )

    observer_rows = []
    summaries = []

    sec_manifest_path = (
        project_root
        / "storage"
        / "manifests"
        / "sec_google_drive.jsonl"
    )

    if sec_manifest_path.exists():
        try:
            summary = summarize_acquisition_manifest(
                sec_manifest_path
            )

            summaries.append(summary)

            observer_rows.append(
                {
                    "Observer": "SEC Google Drive",
                    "Type": "filesystem",
                    "Governance": "institutional source",
                    "Current observations": (
                        summary["current_paths"]
                    ),
                    "Manifest records": summary["records"],
                    "Duplicate-content paths": (
                        summary["duplicate_paths"]
                    ),
                    "Versioned paths": (
                        summary["versioned_paths"]
                    ),
                    "Last observed": (
                        summary["latest_acquired_at"].isoformat()
                        if summary["latest_acquired_at"]
                        else ""
                    ),
                }
            )
        except Exception as error:
            st.error(
                "Could not read the SEC Google Drive manifest."
            )
            st.exception(error)

    observer_config_path = (
        project_root
        / "config"
        / "web_observers.yaml"
    )

    if observer_config_path.exists():
        try:
            catalog = WebObserverCatalog.from_yaml(
                observer_config_path,
                project_root=project_root,
            )

            for observer in catalog.all():
                governance = (
                    observer.authorization.mode
                    if observer.authorization is not None
                    else "robots_policy"
                )

                if observer.manifest_path.exists():
                    summary = summarize_acquisition_manifest(
                        observer.manifest_path
                    )

                    summaries.append(summary)

                    observer_rows.append(
                        {
                            "Observer": observer.name,
                            "Type": "web",
                            "Governance": governance,
                            "Current observations": (
                                summary["current_paths"]
                            ),
                            "Manifest records": (
                                summary["records"]
                            ),
                            "Duplicate-content paths": (
                                summary["duplicate_paths"]
                            ),
                            "Versioned paths": (
                                summary["versioned_paths"]
                            ),
                            "Last observed": (
                                summary[
                                    "latest_acquired_at"
                                ].isoformat()
                                if summary["latest_acquired_at"]
                                else ""
                            ),
                        }
                    )
                else:
                    observer_rows.append(
                        {
                            "Observer": observer.name,
                            "Type": "web",
                            "Governance": governance,
                            "Current observations": 0,
                            "Manifest records": 0,
                            "Duplicate-content paths": 0,
                            "Versioned paths": 0,
                            "Last observed": "",
                        }
                    )

        except Exception as error:
            st.error(
                "Could not load the configured observer network."
            )
            st.exception(error)

    total_records = sum(
        summary["records"]
        for summary in summaries
    )

    total_current_paths = sum(
        summary["current_paths"]
        for summary in summaries
    )

    total_duplicate_paths = sum(
        summary["duplicate_paths"]
        for summary in summaries
    )

    total_versioned_paths = sum(
        summary["versioned_paths"]
        for summary in summaries
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Active observer manifests",
        f"{len(summaries):,}",
    )

    c2.metric(
        "Current observations",
        f"{total_current_paths:,}",
        help=(
            "Latest SourceDocument observation for every path "
            "across all observer manifests."
        ),
    )

    c3.metric(
        "Manifest records",
        f"{total_records:,}",
        help=(
            "All preserved acquisition records, including prior "
            "versions."
        ),
    )

    c4.metric(
        "Duplicate-content paths",
        f"{total_duplicate_paths:,}",
    )

    if total_versioned_paths:
        st.caption(
            f"Versioned source paths preserved: "
            f"{total_versioned_paths:,}"
        )

    st.markdown("**Observer network**")

    if observer_rows:
        st.dataframe(
            observer_rows,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Current observations": st.column_config.NumberColumn(
                    format="%d",
                ),
                "Manifest records": st.column_config.NumberColumn(
                    format="%d",
                ),
                "Duplicate-content paths": (
                    st.column_config.NumberColumn(
                        format="%d",
                    )
                ),
                "Versioned paths": st.column_config.NumberColumn(
                    format="%d",
                ),
            },
        )
    else:
        st.info(
            "No acquisition manifests have been created yet."
        )

    source_counts = {}

    for summary in summaries:
        for document in summary["latest_documents"]:
            label = (
                document.source_organization
                or "Unknown"
            )

            source_counts[label] = (
                source_counts.get(label, 0) + 1
            )

    if source_counts:
        st.markdown("**Current observations by organization**")

        organization_rows = [
            {
                "Organization": organization,
                "Observations": count,
            }
            for organization, count in sorted(
                source_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0].casefold(),
                ),
            )
        ]

        st.dataframe(
            organization_rows,
            use_container_width=True,
            hide_index=True,
        )

    with st.expander(
        "Observer configuration",
        expanded=False,
    ):
        if observer_config_path.exists():
            try:
                catalog = WebObserverCatalog.from_yaml(
                    observer_config_path,
                    project_root=project_root,
                )

                config_rows = []

                for observer in catalog.all():
                    config_rows.append(
                        {
                            "Observer": observer.name,
                            "Enabled": observer.enabled,
                            "Purposes": ", ".join(
                                observer.purposes
                            ),
                            "Allowed hosts": ", ".join(
                                observer.allowed_hosts
                            ),
                            "Robots enforced": (
                                observer.respect_robots
                            ),
                            "Authorization": (
                                observer.authorization.mode
                                if observer.authorization
                                else "public robots policy"
                            ),
                            "Manifest": str(
                                observer.manifest_path
                            ),
                        }
                    )

                st.dataframe(
                    config_rows,
                    use_container_width=True,
                    hide_index=True,
                )

            except Exception as error:
                st.exception(error)
        else:
            st.write(
                "No web observer configuration was found."
            )


@st.cache_resource(show_spinner=False)
def load_constitutional_orientation_service(
    constitutional_dir: str,
) -> ConstitutionalOrientationService:
    """
    Load the curated Institutional Constitution once per Streamlit process.
    """
    catalog = ConstitutionalCatalog.from_directory(
        Path(constitutional_dir)
    )

    return ConstitutionalOrientationService(
        catalog=catalog,
    )


def render_constitutional_orientation(
    orientation: ConstitutionalOrientation,
) -> None:
    """
    Render potentially relevant institutional values.

    This performs orientation only. It does not determine whether a proposal
    aligns or conflicts with an institutional principle.
    """
    with st.container(border=True):
        st.subheader("🧭 Constitutional Orientation")

        st.caption(
            "Institutional values and strategic directions "
            "that may be relevant to the question. "
            "This is orientation, not an alignment judgment."
        )

        if orientation.matches:
            for rank, match in enumerate(
                orientation.matches,
                start=1,
            ):
                st.markdown(
                    f"**{rank}. {match.principle}**"
                )

                st.caption(
                    f"Relevance score: {match.score:.2f} | "
                    f"Source: {match.constitutional_object_title} | "
                    f"Type: {match.constitutional_type}"
                )

                if match.matched_terms:
                    st.write(
                        "**Matched concepts:** "
                        + ", ".join(
                            match.matched_terms
                        )
                    )
        else:
            st.info(
                "No constitutional principle exceeded "
                "the current relevance threshold."
            )

        if orientation.notes:
            st.markdown("**Orientation notes**")

            for note in orientation.notes:
                st.write(f"- {note}")

        st.caption(
            "Overall constitutional orientation confidence: "
            f"{orientation.confidence:.2f}"
        )


def render_constitutional_orientation_for_question(
    *,
    question: str,
    project_root: Path,
    config: dict,
) -> None:
    """
    Orient a question against the curated Institutional Constitution.
    """
    constitutional_dir = (
        project_root
        / config["storage"].get(
            "constitutional",
            "storage/constitutional",
        )
    )

    if not constitutional_dir.exists():
        st.warning(
            "The Institutional Constitution has not "
            "been built yet."
        )
        return

    service = load_constitutional_orientation_service(
        str(constitutional_dir)
    )

    orientation = service.orient(
        question
    )

    render_constitutional_orientation(
        orientation
    )


st.set_page_config(
    page_title="Institutional Semantic Observatory (ISO)",
    page_icon="🔭",
    layout="wide",
)

st.title("🔭 Institutional Semantic Observatory (ISO)")
st.markdown("### *Observe. Explain. Illuminate.*")
st.caption(
    "ISO is an evidence-driven semantic observatory that constructs an explainable "
    "digital representation of an institution's knowledge ecosystem."
)

with st.expander("Mission", expanded=False):
    st.markdown(
        """
        **Observe. Explain. Illuminate.**

        ISO does not replace human judgment.

        ISO synthesizes institutional evidence to support transparent, explainable
        decision making. Rather than making decisions, ISO observes the institution's
        semantic ecosystem, identifies relevant evidence, highlights uncertainty,
        and reveals knowledge gaps so that human decision-makers remain firmly in
        control.
        """
    )

mode = st.radio(
    "Mode",
    ["Overview", "Question Answering", "Decision Brief"],
    horizontal=True,
)

query_label = "Ask a question"
query_placeholder = "What is the CNU travel reimbursement policy?"
button_label = "Ask"
spinner_text = "Searching documents and generating answer..."

if mode == "Overview":
    query = ""
    top_k = 0
else:
    if mode == "Decision Brief":
        query_label = "Institutional question"
        query_placeholder = (
            "What additional resources would be required to establish a "
            "Mechanical Engineering major?"
        )
        button_label = "Generate Decision Brief"
        spinner_text = "Searching documents and generating decision brief..."

    query = st.text_area(
        query_label,
        placeholder=query_placeholder,
        height=100,
    )

    if mode == "Decision Brief":
        top_k = st.slider("Number of retrieved sources", 5, 20, 12)
    else:
        top_k = st.slider("Number of retrieved sources", 3, 10, 5)

developer_mode = st.checkbox("Developer mode", value=False)


if mode == "Overview":
    config = load_config()
    project_root = Path(config["project"]["root"])
    chunks_dir = project_root / config["storage"]["chunks"]

    try:
        report = analyze_corpus(chunks_dir)
        render_iso_overview(st, report)

        st.divider()

        render_acquisition_overview(
            project_root
        )
    except Exception as e:
        st.error("ISO Overview failed.")
        st.exception(e)

    st.stop()

if developer_mode:
    with st.expander("🌱 Semantic Ecosystem Observatory", expanded=False):
        config = load_config()
        project_root = Path(config["project"]["root"])
        chunks_dir = project_root / config["storage"]["chunks"]

        try:
            report = analyze_corpus(chunks_dir)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Documents", f"{report['documents']:,}")
            c2.metric("Chunks", f"{report['total_chunks']:,}")
            c3.metric("Median chunks/doc", report["median"])
            c4.metric("Gini", f"{report['gini']:.3f}")

            st.write("**Corpus dominance**")
            st.write({
                f"Top {k}": f"{100 * v:.2f}%"
                for k, v in report["dominance"].items()
            })

            st.write("**Largest documents**")
            st.dataframe(report["largest"], use_container_width=True)

            st.write("**Chunks by file type**")
            st.dataframe(
                [{"type": k, "chunks": v} for k, v in report["by_type"][:20]],
                use_container_width=True,
            )

            st.write("**Chunks by top folder**")
            st.dataframe(
                [{"folder": k, "chunks": v} for k, v in report["by_folder"][:20]],
                use_container_width=True,
            )

            st.write("**Chunks by parser**")
            st.dataframe(
                [{"parser": k, "chunks": v} for k, v in report["by_parser"]],
                use_container_width=True,
            )

        except Exception as e:
            st.error("Corpus Observatory failed.")
            st.exception(e)

dedupe_by = st.selectbox(
    "Deduplicate sources by",
    ["relative_path", "text", "source_path", None],
    index=0,
)

default_fetch_k = 100 if mode == "Decision Brief" else 50
fetch_k = st.slider("Fetch candidates", 10, 200, default_fetch_k)

if st.button(button_label, type="primary") and query.strip():
    clean_query = query.strip()

    config = load_config()

    project_root = Path(config["project"]["root"])
    vector_db_dir = project_root / config["storage"]["vector_db"]

    embed_cfg = config.get("embedding", {})
    llm_cfg = config.get("llm", {})
    rerank_cfg = config.get("reranking", {})

    control_plane_cfg = config.get("control_plane", {})

    orientation_enabled = control_plane_cfg.get(
        "institutional_orientation_enabled",
        True,
    )

    orientation_neighbor_limit = int(
        control_plane_cfg.get("semantic_neighbor_limit", 5)
    )
    control_plane_result = None

    if orientation_enabled:
        try:
            program_catalog_path = find_program_catalog_path(
                config=config,
                project_root=project_root,
            )

            constitutional_dir = (
                project_root
                / config["storage"].get(
                    "constitutional",
                    "storage/constitutional",
                )
            )

            control_plane_service = (
                load_dual_semantic_control_plane(
                    catalog_path=str(
                        program_catalog_path
                    ),
                    model_name=embed_cfg.get(
                        "model",
                        "BAAI/bge-small-en-v1.5",
                    ),
                    device=embed_cfg.get(
                        "device",
                        "cuda",
                    ),
                    neighbor_limit=(
                        orientation_neighbor_limit
                    ),
                    constitutional_dir=str(
                        constitutional_dir
                    ),
                )
            )

            control_plane_result = (
                control_plane_service.orient(
                    clean_query
                )
            )

            render_institutional_orientation(
                control_plane_result
                .institutional_orientation
            )

            render_constitutional_orientation(
                control_plane_result
                .constitutional_orientation
            )

        except Exception as e:
            st.error("Institutional Orientation failed.")
            st.exception(e)
            st.stop()

    rerank_enabled = rerank_cfg.get("enabled", False)

    retrieval_cfg = config.get("retrieval", {})
    constitutional_top_k = retrieval_cfg.get(
        "constitutional_top_k",
        2,
    )
    empirical_top_k = retrieval_cfg.get(
        "empirical_top_k",
        10,
    )
    configured_fetch_k = retrieval_cfg.get(
        "fetch_k",
        200,
    )
    max_per_document_family = retrieval_cfg.get(
        "max_per_document_family",
        2,
    )

    # The constitutional retrieval policy is configuration-driven.
    # Use the configured broad candidate pool rather than the older UI
    # fetch value when evidence allocation is active.
    fetch_k = configured_fetch_k

    # Keep this optional while calibrating. In settings.yaml, use:
    # reranking:
    #   min_score: null
    # A hard score threshold can otherwise discard every result for some queries.
    min_rerank_score = rerank_cfg.get("min_score", None)

    try:
        with st.spinner(spinner_text):
            common_kwargs = dict(
                vector_db_dir=vector_db_dir,
                model_name=embed_cfg.get("model", "BAAI/bge-small-en-v1.5"),
                embedding_device=embed_cfg.get("device", "cuda"),
                llm_base_url=llm_cfg["base_url"],
                llm_model=llm_cfg["model"],
                top_k=top_k,
                fetch_k=fetch_k,
                dedupe_by=dedupe_by,
                rerank=rerank_enabled,
                reranker_model=rerank_cfg.get("model"),
                reranker_device=rerank_cfg.get("device", "cuda"),
                min_rerank_score=min_rerank_score,
                return_trace=developer_mode,
                constitutional_top_k=constitutional_top_k,
                empirical_top_k=empirical_top_k,
                max_per_document_family=max_per_document_family,
            )

            if mode == "Decision Brief":
                response = generate_decision_brief(
                    question=clean_query,
                    constitutional_orientation=(
                        control_plane_result.constitutional_orientation
                        if control_plane_result is not None
                        else None
                    ),
                    **common_kwargs,
                )
            else:
                response = answer_question(
                    query=clean_query,
                    **common_kwargs,
                )

        if developer_mode:
            artifact, results, retrieval_report, trace, profile = response
        else:
            artifact, results, profile = response
            retrieval_report = None
            trace = None

        if mode == "Decision Brief":
            answer = artifact.raw_markdown
        else:
            answer = artifact

    except Exception as e:
        st.error("The pipeline failed.")
        st.exception(e)
        st.stop()

    st.caption(
        f"Reranking: {'enabled' if rerank_enabled else 'disabled'} | "
        f"fetch_k={fetch_k} | "
        f"constitutional_k={constitutional_top_k} | "
        f"empirical_k={empirical_top_k} | "
        f"dedupe_by={dedupe_by} | "
        f"min_rerank_score={min_rerank_score}"
    )

    if mode == "Decision Brief":
        if getattr(
            artifact,
            "observatory_assessment",
            None,
        ) is not None:
            render_observatory_assessment(
                st,
                artifact.observatory_assessment,
            )

        if getattr(
            artifact,
            "evidence_fitness",
            None,
        ) is not None:
            render_evidence_fitness(
                st,
                artifact.evidence_fitness,
            )

    if mode == "Decision Brief":
        st.subheader("📄 Decision Brief")
    else:
        st.subheader("Answer")

    st.markdown(answer.replace("$", r"\$"))

    st.subheader("Sources")

    if not results:
        st.warning("No sources were returned.")
    else:
        constitutional_source_number = 0
        empirical_source_number = 0

        for result in results:
            citation = result.citation

            title = resolve_source_title(result)
            relative_path = citation.get("relative_path") or "Unknown path"
            start_char = citation.get("start_char")
            end_char = citation.get("end_char")

            evidence_class = result.metadata.get("evidence_class")

            citation_label = result.metadata.get(
                "citation_label"
            )

            if citation_label is None:
                if result.object_type == "constitutional_knowledge":
                    constitutional_source_number += 1
                    citation_label = (
                        "Constitutional Source "
                        f"{constitutional_source_number}"
                    )
                else:
                    empirical_source_number += 1
                    citation_label = (
                        "Empirical Source "
                        f"{empirical_source_number}"
                    )

            expander_label = executive_source_label(
                citation_label,
                title,
                evidence_class,
            )

            with st.expander(expander_label):
                st.write(f"**Path:** `{relative_path}`")

                if result.metadata.get("evidence_class"):
                    st.write(f"**Evidence Class:** {result.metadata.get('evidence_class')}")
                    st.write(f"**Evidence Class Confidence:** `{result.metadata.get('evidence_class_confidence')}`")
                    st.write(f"**Evidence Class Rationale:** {result.metadata.get('evidence_class_rationale')}")

                if start_char is not None and end_char is not None:
                    st.write(f"**Characters:** {start_char}–{end_char}")

                st.write("**Text preview:**")
                st.write(result.text[:2000])

                if developer_mode:
                    st.write("**Citation metadata:**")
                    st.json(citation)

                    st.write("**Result metadata:**")
                    st.json(result.metadata)

    if developer_mode and trace is not None:
        st.subheader("Retrieval Timing")

        st.write(
            {
                "total_seconds": round(profile.total_seconds, 3),
                "search_seconds": round(profile.search_seconds, 3),
                "dedupe_seconds": round(profile.dedupe_seconds, 3),
                "rerank_seconds": round(profile.rerank_seconds, 3),
                "family_diversity_seconds": round(
                    profile.family_diversity_seconds, 3
                ),
                "threshold_seconds": round(profile.threshold_seconds, 3),
            }
        )

        st.subheader("Retrieval Diagnostics")

        st.write(
            {
                "query": retrieval_report.query,
                "fetch_k": retrieval_report.fetch_k,
                "top_k": retrieval_report.requested_top_k,
                "dedupe_by": retrieval_report.dedupe_by,
                "raw_candidates": retrieval_report.num_candidates,
                "after_dedup": retrieval_report.num_after_dedup,
                "after_rerank": retrieval_report.num_after_rerank,
                "after_document_family_diversity": (
                    retrieval_report.num_after_family_diversity
                ),
                "removed_by_document_family_diversity": (
                    retrieval_report.num_removed_by_family_diversity
                ),
                "removed_by_evidence_allocation": (
                    retrieval_report.num_removed_by_evidence_allocation
                ),
                "max_per_document_family": (
                    retrieval_report.max_per_document_family
                ),
                "after_threshold": retrieval_report.num_after_threshold,
                "final_results": retrieval_report.num_results,
                "reranking_enabled": retrieval_report.reranking_enabled,
                "reranker_model": retrieval_report.reranker_model,
                "min_rerank_score": retrieval_report.min_rerank_score,
            }
        )

        def show_trace_section(label, items, max_items=25):
            with st.expander(label, expanded=False):
                for i, result in enumerate(items[:max_items], start=1):
                    citation = result.citation
                    metadata = result.metadata

                    title = citation.get("title") or "Untitled source"
                    path = citation.get("relative_path") or "Unknown path"

                    st.markdown(
                        f"### {i}. {title} — score {result.score:.4f}"
                    )
                    st.write(f"**Path:** `{path}`")
                    if metadata.get("evidence_class"):
                        st.write(f"**Evidence Class:** {metadata.get('evidence_class')}")
                    st.write(
                        f"**Parser:** `{citation.get('parser') or metadata.get('parser')}`"
                    )
                    st.write(
                        f"**Chars:** {citation.get('start_char')}–{citation.get('end_char')}"
                    )

                    if metadata.get("faiss_score") is not None:
                        st.write(f"**FAISS score:** `{metadata.get('faiss_score')}`")

                    if metadata.get("rerank_score") is not None:
                        st.write(f"**Rerank score:** `{metadata.get('rerank_score')}`")

                    if metadata.get("document_family_key"):
                        st.write(
                            "**Document family:** "
                            f"`{metadata.get('document_family_key')}`"
                        )

                    authority = (
                        metadata.get("issuing_authority")
                        or citation.get("source_organization")
                        or metadata.get("source_organization")
                    )
                    if authority:
                        st.write(f"**Source authority:** {authority}")

                    if metadata.get("evidence_role"):
                        st.write(f"**Evidence role:** {metadata.get('evidence_role')}")

                    if metadata.get("evidence_selection_reason"):
                        st.write(
                            "**Selection reason:** "
                            f"{metadata.get('evidence_selection_reason')}"
                        )

                    if metadata.get("evidence_exclusion_reason"):
                        st.write(
                            "**Exclusion reason:** "
                            f"{metadata.get('evidence_exclusion_reason')}"
                        )

                    st.write(
                        "**Constitutional fallback:** "
                        f"{metadata.get('constitutional_fallback', False)}"
                    )

                    st.write("**Chunk preview:**")
                    st.write(result.text[:1500])
                    st.divider()

        show_trace_section("1. Raw FAISS Candidates", trace.raw_candidates)
        show_trace_section("2. After Deduplication", trace.deduped_candidates)
        show_trace_section("3. After Reranking", trace.reranked_candidates)
        show_trace_section(
            "4. After Document-Family Diversity",
            trace.family_diversified_candidates,
        )
        show_trace_section(
            "5. Removed by Document-Family Diversity",
            trace.family_removed_candidates,
        )
        show_trace_section("6. After Threshold", trace.thresholded_candidates)
        show_trace_section(
            "7. Removed by Evidence Allocation",
            trace.allocation_removed_candidates,
        )
        show_trace_section(
            "8. Final Results Sent to LLM",
            trace.final_results,
            max_items=top_k,
        )
