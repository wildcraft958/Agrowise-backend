"""ChromaDB RAG retriever backed by Vertex AI embeddings.

Each retriever wraps a single ChromaDB collection and exposes:
- add_documents(docs)  — upsert into the collection
- search(query, k, filter) — similarity search with optional metadata filter
- count() — number of stored documents

The embeddings object must implement the LangChain Embeddings interface
(embed_documents / embed_query).  In production this is VertexAIEmbeddings;
in tests it is mocked.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Thin wrapper around a LangChain Chroma vectorstore."""

    def __init__(
        self,
        collection: str,
        embeddings: Any,
        persist_dir: str = "./chroma_db",
    ) -> None:
        self._store = Chroma(
            collection_name=collection,
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )
        logger.debug("RAGRetriever: collection=%s persist=%s", collection, persist_dir)

    def add_documents(self, docs: list[Document]) -> None:
        """Add (upsert) documents into the collection."""
        if not docs:
            return
        self._store.add_documents(docs)
        logger.info("Added %d documents to collection", len(docs))

    def search(
        self,
        query: str,
        k: int = 5,
        filter: dict | None = None,  # noqa: A002
    ) -> list[Document]:
        """Similarity search returning up to k documents.

        Args:
            query: Natural-language query string.
            k: Maximum number of results.
            filter: Optional ChromaDB metadata filter dict.

        Returns:
            List of matching Documents (may be fewer than k if collection is small).
        """
        try:
            results = self._store.similarity_search(query, k=k, filter=filter)
            return results
        except Exception as exc:
            # Empty collection raises in some ChromaDB versions
            logger.debug("Search error (likely empty collection): %s", exc)
            return []

    def count(self) -> int:
        """Return number of documents currently in the collection."""
        try:
            return self._store._collection.count()
        except Exception:
            return 0
