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
st.caption("Prototype RAG system over the department document repository. Results should be verified against cited sources.")

query = st.text_area(
    "Ask a question",
    placeholder="What is the cybersecurity major?",
    height=100,
)

top_k = st.slider("Number of retrieved sources", 3, 10, 5)

if st.button("Ask", type="primary") and query.strip():
    config = load_config()

    project_root = Path(config["project"]["root"])
    vector_db_dir = project_root / config["storage"]["vector_db"]

    embed_cfg = config.get("embedding", {})
    llm_cfg = config.get("llm", {})

    with st.spinner("Searching documents and generating answer..."):
        answer, results = answer_question(
            query=query,
            vector_db_dir=vector_db_dir,
            model_name=embed_cfg.get("model", "BAAI/bge-small-en-v1.5"),
            embedding_device=embed_cfg.get("device", "cuda"),
            llm_base_url=llm_cfg["base_url"],
            llm_model=llm_cfg["model"],
            top_k=top_k,
            fetch_k=50,
            dedupe_by="text",
        )

    st.subheader("Answer")
    st.write(answer)

    st.subheader("Sources")
    for i, result in enumerate(results, start=1):
        citation = result.citation

        with st.expander(
            f"[Source {i}] {citation.get('title')} — score {result.score:.4f}"
        ):
            st.write(f"**Path:** `{citation.get('relative_path')}`")
            st.write(
                f"**Characters:** {citation.get('start_char')}–{citation.get('end_char')}"
            )
            st.write(result.text[:2000])
