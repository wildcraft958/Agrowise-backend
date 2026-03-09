"""KCC (Kisan Call Centre) bulk ingestion loader.

Fetches KCC transcripts via KCCClient and converts them to LangChain Documents
for bulk ingestion into ChromaDB.

Each document's page_content is:
    "Q: <QueryText>\nA: <KccAns>"

Metadata includes: state, year, month, source="kcc".
Records with empty answers are skipped.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from langchain_core.documents import Document

# Make tools/ importable
_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.kcc_tool import KCCClient  # noqa: E402

logger = logging.getLogger(__name__)


class KCCLoader:
    """Loads KCC transcripts from the API and converts them to LangChain Documents."""

    def __init__(self, api_key: str | None = None) -> None:
        self._client = KCCClient(api_key=api_key)

    def fetch_page(self, offset: int = 0, limit: int = 100) -> list[dict]:
        """Fetch a page of KCC records.

        Returns empty list on any API error (safe for bulk ingestion loops).
        """
        try:
            return self._client.search_queries(keyword="", limit=limit)  # type: ignore[arg-type]
        except Exception as exc:
            logger.warning("KCC fetch_page error (offset=%d): %s", offset, exc)
            return []

    def records_to_documents(self, records: list[dict]) -> list[Document]:
        """Convert raw KCC API records to LangChain Documents.

        Skips records where KccAns is empty or whitespace-only.
        """
        docs: list[Document] = []
        for rec in records:
            answer = (rec.get("KccAns") or "").strip()
            if not answer:
                continue
            query = (rec.get("QueryText") or "").strip()
            content = f"Q: {query}\nA: {answer}"
            meta: dict[str, str] = {"source": "kcc"}
            if state := (rec.get("StateName") or "").strip():
                meta["state"] = state
            if year := (rec.get("Year") or "").strip():
                meta["year"] = year
            if month := (rec.get("Month") or "").strip():
                meta["month"] = month
            docs.append(Document(page_content=content, metadata=meta))
        return docs
