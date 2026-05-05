"""
RAG pipeline — embedding and vector store.

Uses HuggingFaceEmbeddings (sentence-transformers) so no LLM API key
is needed for embeddings. Works with any LLM provider (Groq, OpenAI, etc.).
"""
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

CHROMA_PATH = "./chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # fast, lightweight, runs locally


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Return a shared HuggingFace embedding model (downloaded once, cached)."""
    return HuggingFaceEmbeddings()


def build_vector_store(stories: list[dict]) -> Chroma:
    """
    Embed all stories and persist them in a local Chroma vector store.
    No API key required — embeddings run locally via sentence-transformers.
    """
    docs = [
        Document(
            page_content=f"{s['summary']}\n{s['description']}",
            metadata={"key": s["key"], "summary": s["summary"]},
        )
        for s in stories
    ]
    db = Chroma.from_documents(
        docs,
        _get_embeddings(),
        persist_directory=CHROMA_PATH,
    )
    db.persist()
    return db


def retrieve_context(query: str, k: int = 3) -> str:
    """
    Retrieve the k most relevant story chunks for a query.
    Returns concatenated page content as a single string.
    """
    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=_get_embeddings(),
    )
    results = db.similarity_search(query, k=k)
    return "\n\n".join(r.page_content for r in results)
