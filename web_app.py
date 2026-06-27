import streamlit as st
from pathlib import Path

from app.config import load_config
from app.rag import answer_question


st.set_page_config(
    page_title="Department Knowledge Assistant",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 Department Knowledge Assistant")
st.caption(
    "Prototype RAG system over the department document repository. "
    "Results should be verified against cited sources."
)

query = st.text_area(
    "Ask a question",
    placeholder="What is the CNU travel reimbursement policy?",
    height=100,
)

top_k = st.slider("Number of retrieved sources", 3, 10, 5)

developer_mode = st.checkbox("Developer mode", value=False)

dedupe_by = st.selectbox(
    "Deduplicate sources by",
    ["relative_path", "text", "source_path", None],
    index=0,
)

fetch_k = st.slider("Fetch candidates", 10, 200, 50)

if st.button("Ask", type="primary") and query.strip():
    config = load_config()

    project_root = Path(config["project"]["root"])
    vector_db_dir = project_root / config["storage"]["vector_db"]

    embed_cfg = config.get("embedding", {})
    llm_cfg = config.get("llm", {})
    rerank_cfg = config.get("reranking", {})

    rerank_enabled = rerank_cfg.get("enabled", False)

    try:
        with st.spinner("Searching documents and generating answer..."):
            response = answer_question(
                query=query,
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
                return_trace=developer_mode,
                min_rerank_score=rerank_cfg.get("min_score", None),
            )

        if developer_mode:
            answer, results, retrieval_report, trace = response
        else:
            answer, results = response
            retrieval_report = None
            trace = None

    except Exception as e:
        st.error("The question-answering pipeline failed.")
        st.exception(e)
        st.stop()

    st.caption(
        f"Reranking: {'enabled' if rerank_enabled else 'disabled'} | "
        f"fetch_k={fetch_k} | top_k={top_k} | dedupe_by={dedupe_by}"
    )

    st.subheader("Answer")
    st.write(answer)

    st.subheader("Sources")

    if not results:
        st.warning("No sources were returned.")
    else:
        for i, result in enumerate(results, start=1):
            citation = result.citation

            title = citation.get("title") or "Untitled source"
            relative_path = citation.get("relative_path") or "Unknown path"
            start_char = citation.get("start_char")
            end_char = citation.get("end_char")

            with st.expander(
                f"[Source {i}] {title} — score {result.score:.4f}"
            ):
                st.write(f"**Path:** `{relative_path}`")

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
        st.subheader("Retrieval Diagnostics")

        st.write(
            {
                "query": retrieval_report.query,
                "fetch_k": retrieval_report.fetch_k,
                "top_k": retrieval_report.requested_top_k,
                "dedupe_by": retrieval_report.dedupe_by,
                "raw_candidates": len(trace.raw_candidates),
                "deduped_candidates": len(trace.deduped_candidates),
                "reranked_candidates": len(trace.reranked_candidates),
                "final_results": len(trace.final_results),
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

                    st.write("**Chunk preview:**")
                    st.write(result.text[:1500])
                    st.divider()

        show_trace_section("1. Raw FAISS Candidates", trace.raw_candidates)
        show_trace_section("2. After Deduplication", trace.deduped_candidates)
        show_trace_section("3. After Reranking", trace.reranked_candidates)
        show_trace_section(
            "4. Final Results Sent to LLM",
            trace.final_results,
            max_items=top_k,
        )
