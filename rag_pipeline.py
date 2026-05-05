"""
RAG pipeline — embedding and vector store.

Uses HuggingFaceEmbeddings (sentence-transformers) — no API key needed.
Stores the vector store IN MEMORY (via st.session_state) rather than on
disk, which is compatible with Streamlit Cloud's ephemeral filesystem.
"""

import streamlit as st
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Return embedding model — cached in session state so it loads once."""
    if "_embeddings" not in st.session_state:
        st.session_state._embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return st.session_state._embeddings


def build_vector_store(stories: list[dict]) -> Chroma:
    """
    Embed all stories into an in-memory Chroma vector store.
    Stores the db object in session state so retrieve_context can use it.
    No disk persistence — works on Streamlit Cloud and local alike.
    """
    docs = [
        Document(
            page_content=f"{s['summary']}\n{s['description']}",
            metadata={"key": s["key"], "summary": s["summary"]},
        )
        for s in stories
    ]
    db = Chroma.from_documents(docs, _get_embeddings())
    st.session_state._chroma_db = db
    return db


def retrieve_context(query: str, k: int = 3) -> str:
    """
    Retrieve the k most relevant story chunks for a query.
    Reads the in-memory Chroma db from session state.
    Returns concatenated page content as a single string.
    """
    db = st.session_state.get("_chroma_db")
    if db is None:
        # No vector store built yet — return empty context gracefully
        return ""
    results = db.similarity_search(query, k=k)
    return "\n\n".join(r.page_content for r in results)
