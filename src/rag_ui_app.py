"""
rag_ui_app.py
=============

This app provides a chat interface to ask natural-language questions over a
Turtle knowledge graph using a local LLM (Ollama) and SPARQL-based RAG.

What it does:
- Loads a .ttl knowledge graph
- Generates SPARQL queries from user questions
- Queries the graph and returns grounded answers
- Optionally shows a baseline LLM answer (no KG)

Requirements:
    pip install streamlit rdflib requests

Ollama setup:
    ollama serve
    ollama pull llama3.2:1b

Run the app:
    python -m streamlit run scripts/rag_ui_app.py

Notes:
- Default Ollama API: http://localhost:11434/api/generate
- You can configure KG path, model, and endpoint in the sidebar
- Ollama must be running before starting the app
"""
from __future__ import annotations
import os
from typing import Any, Dict

import streamlit as st

from src.rag_pipeline import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    answer_no_rag,
    answer_with_sparql_generation,
    build_schema_summary,
    load_graph,
    resolve_ttl_path,
)

st.set_page_config(page_title="KG RAG Chatbot", page_icon="🧠", layout="wide")


@st.cache_resource
def init_graph(ttl_path: str):
    g = load_graph(ttl_path)
    schema = build_schema_summary(g)
    return g, schema


def render_result(result: Dict[str, Any]) -> None:
    if result.get("error"):
        st.error(result["error"])

    st.subheader("Grounded answer")
    st.write(result.get("grounded_answer") or "No grounded answer generated.")

    with st.expander("SPARQL query used", expanded=False):
        st.code(result.get("query", ""), language="sparql")

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Repaired", "Yes" if result.get("repaired") else "No")
    with c2:
        st.metric("Rows returned", len(result.get("rows", [])))

    rows = result.get("rows", [])
    vars_ = result.get("vars", [])

    with st.expander("Raw KG results", expanded=True):
        if not rows:
            st.info("No rows returned from the KG.")
        else:
            data = [dict(zip(vars_, row)) for row in rows[:50]]
            st.dataframe(data, use_container_width=True)


def main() -> None:
    st.title("🧠 Knowledge Graph RAG Chatbot")
    st.caption("Ask a question about the geopolitical landscape of greenland (January 2026) in natural language. The app generates SPARQL, queries the KG, and returns a grounded answer.")

    with st.sidebar:
        st.header("Configuration")

        try:
            default_ttl = str(resolve_ttl_path())
        except Exception:
            default_ttl = ""

        
        ttl_path=st.selectbox(
            "KG Turtle file (.ttl)",
            options=[
                "outputs/graphs/mykg_step4_expanded.ttl",
                "outputs/graphs/mykg_step1.ttl",
            ],
            index=0,
        )
        available_models = [
        "llama3.2:1b",
        "gemma:2b",
        ]

        model_name = st.selectbox(
        "Ollama model",
        options=available_models,
        index=available_models.index(DEFAULT_MODEL) if DEFAULT_MODEL in available_models else 0,
        )

        ollama_url = st.text_input(
            "Ollama URL",
            value=os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL),
        )

        show_baseline = st.checkbox("Show baseline answer (no KG)", value=True)
        if st.button("🔄 Clear conversation"):
            st.session_state.messages = []
            st.rerun()

    if not ttl_path:
        st.warning("Please provide a .ttl file path.")
        return

    try:
        g, schema = init_graph(ttl_path)
    except Exception as e:
        st.error(f"Failed to load KG: {e}")
        return

    st.success(f"Loaded KG with {len(g)} triples.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("rag_result"):
                render_result(msg["rag_result"])
            if msg["role"] == "assistant" and msg.get("baseline_answer"):
                with st.expander("Baseline answer (no KG)", expanded=False):
                    st.write(msg["baseline_answer"])

    question = st.chat_input("Ask a question about your knowledge graph...")

    if question:
        st.session_state.messages.append({"role": "user", "content": question})

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            baseline_answer = None
            if show_baseline:
                with st.spinner("Generating baseline answer..."):
                    try:
                        baseline_answer = answer_no_rag(
                            question=question,
                            model=model_name,
                            ollama_url=ollama_url,
                        )
                    except Exception as e:
                        baseline_answer = f"Baseline failed: {e}"

            with st.spinner("Generating SPARQL and querying the knowledge graph..."):
                try:
                    rag_result = answer_with_sparql_generation(
                        g=g,
                        schema_summary=schema,
                        question=question,
                        model=model_name,
                        ollama_url=ollama_url,
                        try_repair=True,
                    )
                except Exception as e:
                    rag_result = {
                        "query": "",
                        "vars": [],
                        "rows": [],
                        "repaired": False,
                        "error": str(e),
                        "grounded_answer": None,
                    }

            if show_baseline:
                with st.expander("Baseline answer (no KG)", expanded=False):
                    st.write(baseline_answer)

            render_result(rag_result)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": rag_result.get("grounded_answer") or "No answer generated.",
                "rag_result": rag_result,
                "baseline_answer": baseline_answer,
            }
        )


if __name__ == "__main__":
    main()