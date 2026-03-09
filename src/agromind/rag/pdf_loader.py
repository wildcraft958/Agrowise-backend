"""Document loader for PDFs, plain-text files, and Markdown files.

Splits documents into chunks using LangChain's RecursiveCharacterTextSplitter
with chunk_size and chunk_overlap from config.yaml.

All loaders set a `source` metadata key to the file path.
Custom metadata passed in is merged into every document's metadata.
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from agromind.config import settings

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Loads and chunks PDFs, text files, and markdown files into LangChain Documents."""

    def __init__(self) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag.chunk_size,
            chunk_overlap=settings.rag.chunk_overlap,
        )

    # ------------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------------

    def load_pdf(self, path: str, metadata: dict | None = None) -> list[Document]:
        """Load a PDF file using pypdf, one Document per page.

        Args:
            path: Path to the PDF file.
            metadata: Extra metadata to merge into each document.

        Returns:
            List of Documents (one per page with content).

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        from pypdf import PdfReader

        reader = PdfReader(str(p))
        docs: list[Document] = []
        base_meta = {"source": str(path), **(metadata or {})}

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            docs.append(Document(
                page_content=text,
                metadata={**base_meta, "page": i + 1},
            ))

        logger.info("Loaded %d pages from %s", len(docs), path)
        return docs

    def load_text(self, path: str, metadata: dict | None = None) -> list[Document]:
        """Load a plain-text file as a single Document.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Text file not found: {path}")

        content = p.read_text(encoding="utf-8")
        base_meta = {"source": str(path), **(metadata or {})}
        logger.info("Loaded %d chars from %s", len(content), path)
        return [Document(page_content=content, metadata=base_meta)]

    def load_markdown(self, path: str, metadata: dict | None = None) -> list[Document]:
        """Load a Markdown file as a single Document.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Markdown file not found: {path}")

        content = p.read_text(encoding="utf-8")
        base_meta = {"source": str(path), **(metadata or {})}
        logger.info("Loaded markdown %s (%d chars)", path, len(content))
        return [Document(page_content=content, metadata=base_meta)]

    # ------------------------------------------------------------------
    # Chunker
    # ------------------------------------------------------------------

    def chunk(self, docs: list[Document]) -> list[Document]:
        """Split documents into smaller chunks using RecursiveCharacterTextSplitter.

        Preserves all existing metadata on each chunk.
        """
        if not docs:
            return []
        return self._splitter.split_documents(docs)
