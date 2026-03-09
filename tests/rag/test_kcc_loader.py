"""Tests for KCCLoader — rag/kcc_loader.py."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from agromind.rag.kcc_loader import KCCLoader


@pytest.fixture
def loader():
    return KCCLoader(api_key=None)


class TestKCCLoaderInit:
    def test_instantiates_with_no_key(self):
        kl = KCCLoader(api_key=None)
        assert kl is not None

    def test_instantiates_with_key(self):
        kl = KCCLoader(api_key="test-key")
        assert kl is not None


class TestKCCFetchPage:
    def test_returns_list_of_dicts(self, loader):
        mock_records = [
            {"QueryText": "stem borer on rice", "KccAns": "Use carbofuran", "StateName": "Punjab"},
            {"QueryText": "urea dose wheat", "KccAns": "Apply 120 kg/ha", "StateName": "Bihar"},
        ]
        with patch.object(loader, "_client") as mock_client:
            mock_client.search_queries.return_value = mock_records
            result = loader.fetch_page(offset=0, limit=2)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(r, dict) for r in result)

    def test_returns_empty_on_api_error(self, loader):
        with patch.object(loader, "_client") as mock_client:
            mock_client.search_queries.side_effect = RuntimeError("API down")
            result = loader.fetch_page(offset=0, limit=10)
        assert result == []


class TestKCCRecordsToDocuments:
    def test_converts_records_to_documents(self, loader):
        records = [
            {
                "QueryText": "stem borer on rice",
                "KccAns": "Use carbofuran granules",
                "StateName": "Punjab",
                "Year": "2023",
                "Month": "6",
            }
        ]
        docs = loader.records_to_documents(records)
        assert isinstance(docs, list)
        assert len(docs) == 1
        assert isinstance(docs[0], Document)

    def test_document_content_includes_query_and_answer(self, loader):
        records = [{"QueryText": "irrigation timing", "KccAns": "Water at tillering stage"}]
        docs = loader.records_to_documents(records)
        content = docs[0].page_content
        assert "irrigation timing" in content
        assert "tillering" in content

    def test_document_metadata_has_state(self, loader):
        records = [{"QueryText": "q", "KccAns": "a", "StateName": "Maharashtra"}]
        docs = loader.records_to_documents(records)
        assert docs[0].metadata.get("state") == "Maharashtra"

    def test_skips_records_with_empty_answer(self, loader):
        records = [
            {"QueryText": "q1", "KccAns": "good answer"},
            {"QueryText": "q2", "KccAns": ""},
            {"QueryText": "q3", "KccAns": "   "},
        ]
        docs = loader.records_to_documents(records)
        assert len(docs) == 1

    def test_empty_input_returns_empty(self, loader):
        assert loader.records_to_documents([]) == []
