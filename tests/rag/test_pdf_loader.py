"""Tests for DocumentLoader — rag/pdf_loader.py."""

import textwrap
from pathlib import Path

import pytest
from langchain_core.documents import Document

from agromind.rag.pdf_loader import DocumentLoader


WHEAT_PDF = "dataset/Methods Manual Soil Testing In India - Department of Agriculture & Cooperation.pdf"
OCR_TXT = "dataset/iari_soil_water_testing_ocr.txt"
CHEMICALS_MD = "dataset/cibrc/chemicals.md"


@pytest.fixture(scope="module")
def loader():
    return DocumentLoader()


class TestDocumentLoaderInit:
    def test_instantiates(self):
        dl = DocumentLoader()
        assert dl is not None


class TestLoadPDF:
    def test_returns_list_of_documents(self, loader):
        docs = loader.load_pdf(WHEAT_PDF)
        assert isinstance(docs, list)
        assert len(docs) > 0
        assert all(isinstance(d, Document) for d in docs)

    def test_documents_have_page_content(self, loader):
        docs = loader.load_pdf(WHEAT_PDF)
        assert all(len(d.page_content) > 0 for d in docs)

    def test_documents_have_source_metadata(self, loader):
        docs = loader.load_pdf(WHEAT_PDF)
        assert all("source" in d.metadata for d in docs)

    def test_custom_metadata_merged(self, loader):
        docs = loader.load_pdf(WHEAT_PDF, metadata={"collection": "icar", "topic": "soil"})
        assert all(d.metadata.get("collection") == "icar" for d in docs)
        assert all(d.metadata.get("topic") == "soil" for d in docs)

    def test_missing_file_raises(self, loader):
        with pytest.raises(FileNotFoundError):
            loader.load_pdf("dataset/does_not_exist.pdf")


class TestLoadText:
    def test_returns_list_of_documents(self, loader):
        docs = loader.load_text(OCR_TXT)
        assert isinstance(docs, list)
        assert len(docs) > 0

    def test_content_nonempty(self, loader):
        docs = loader.load_text(OCR_TXT)
        total_chars = sum(len(d.page_content) for d in docs)
        assert total_chars > 1000

    def test_source_metadata_set(self, loader):
        docs = loader.load_text(OCR_TXT)
        assert all("source" in d.metadata for d in docs)

    def test_missing_file_raises(self, loader):
        with pytest.raises(FileNotFoundError):
            loader.load_text("dataset/no_such_file.txt")


class TestLoadMarkdown:
    def test_returns_list_of_documents(self, loader):
        docs = loader.load_markdown(CHEMICALS_MD)
        assert isinstance(docs, list)
        assert len(docs) > 0

    def test_content_nonempty(self, loader):
        docs = loader.load_markdown(CHEMICALS_MD)
        assert all(len(d.page_content) > 0 for d in docs)

    def test_missing_file_raises(self, loader):
        with pytest.raises(FileNotFoundError):
            loader.load_markdown("dataset/no_such.md")


class TestChunk:
    def test_chunk_splits_large_doc(self, loader):
        big_text = "Agriculture is the backbone of the Indian economy. " * 200
        docs = [Document(page_content=big_text, metadata={"source": "test"})]
        chunks = loader.chunk(docs)
        assert len(chunks) > 1

    def test_chunk_preserves_metadata(self, loader):
        docs = [Document(page_content="soil moisture " * 100, metadata={"source": "x", "crop": "wheat"})]
        chunks = loader.chunk(docs)
        assert all(c.metadata.get("crop") == "wheat" for c in chunks)

    def test_chunk_small_doc_stays_single(self, loader):
        docs = [Document(page_content="Short text.", metadata={"source": "test"})]
        chunks = loader.chunk(docs)
        assert len(chunks) == 1

    def test_empty_input_returns_empty(self, loader):
        assert loader.chunk([]) == []
