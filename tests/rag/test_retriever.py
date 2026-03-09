"""Tests for RAGRetriever — rag/retriever.py.

All tests use an in-memory (ephemeral) ChromaDB instance so no disk I/O.
Embeddings are mocked to avoid Vertex AI calls.
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from agromind.rag.retriever import RAGRetriever


def _mock_embeddings():
    """Return a mock embedding function that returns fixed-size vectors."""
    mock = MagicMock()
    # embed_documents is called with a list of strings; return matching-length vectors
    mock.embed_documents.side_effect = lambda texts: [[0.1] * 768 for _ in texts]
    mock.embed_query.return_value = [0.1] * 768
    return mock


@pytest.fixture
def retriever(tmp_path):
    embeddings = _mock_embeddings()
    return RAGRetriever(
        collection="test_col",
        embeddings=embeddings,
        persist_dir=str(tmp_path / "chroma"),
    )


class TestRAGRetrieverInit:
    def test_instantiates(self, tmp_path):
        r = RAGRetriever(
            collection="col",
            embeddings=_mock_embeddings(),
            persist_dir=str(tmp_path / "chroma"),
        )
        assert r is not None


class TestAddDocuments:
    def test_add_single_document(self, retriever):
        doc = Document(page_content="Wheat is a rabi crop.", metadata={"source": "test"})
        retriever.add_documents([doc])  # should not raise

    def test_count_increases_after_add(self, retriever):
        before = retriever.count()
        docs = [
            Document(page_content=f"Doc {i}", metadata={"source": "test"})
            for i in range(3)
        ]
        retriever.add_documents(docs)
        assert retriever.count() == before + 3

    def test_add_empty_list_is_noop(self, retriever):
        before = retriever.count()
        retriever.add_documents([])
        assert retriever.count() == before


class TestSearch:
    def test_search_returns_list(self, retriever):
        retriever.add_documents([
            Document(page_content="Wheat needs 120 kg/ha urea.", metadata={"source": "t"}),
        ])
        results = retriever.search("urea wheat", k=1)
        assert isinstance(results, list)

    def test_search_returns_documents(self, retriever):
        retriever.add_documents([
            Document(page_content="Rice paddy needs flooding.", metadata={"source": "t"}),
        ])
        results = retriever.search("rice", k=1)
        assert all(isinstance(d, Document) for d in results)

    def test_search_k_limits_results(self, retriever):
        docs = [
            Document(page_content=f"Crop {i} info.", metadata={"source": "t"})
            for i in range(10)
        ]
        retriever.add_documents(docs)
        results = retriever.search("crop", k=3)
        assert len(results) <= 3

    def test_search_with_metadata_filter(self, retriever):
        retriever.add_documents([
            Document(page_content="ICAR rice advisory.", metadata={"collection": "icar"}),
            Document(page_content="KCC rice query.", metadata={"collection": "kcc"}),
        ])
        results = retriever.search("rice", k=5, filter={"collection": "icar"})
        # All returned docs should have the icar collection (if any returned)
        for doc in results:
            assert doc.metadata.get("collection") == "icar"

    def test_search_empty_collection_returns_empty(self, tmp_path):
        r = RAGRetriever(
            collection="empty_col",
            embeddings=_mock_embeddings(),
            persist_dir=str(tmp_path / "chroma2"),
        )
        results = r.search("anything", k=5)
        assert results == []
