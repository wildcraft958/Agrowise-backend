"""One-time ingestion script — builds ChromaDB vector database.

Usage:
    python scripts/ingest.py [--icar] [--kcc] [--all] [--kcc-limit N]

Options:
    --icar        Ingest ICAR PDFs + text + markdown into icar_knowledge
    --kcc         Bulk-ingest KCC transcripts into kcc_transcripts
    --all         Both (default when no flag given)
    --kcc-limit   Max KCC pages to fetch (default 200 = 20k records)

Idempotent: skips already-populated collections.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make project root importable
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest")

from agromind.config import settings  # noqa: E402
from agromind.rag.pdf_loader import DocumentLoader  # noqa: E402
from agromind.rag.kcc_loader import KCCLoader  # noqa: E402
from agromind.rag.retriever import RAGRetriever  # noqa: E402
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # noqa: E402


def _make_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.models.embedding,
        project=settings.gcp.project_id,
        location=settings.gcp.location,
    )


# ---------------------------------------------------------------------------
# ICAR ingestion
# ---------------------------------------------------------------------------

_ICAR_SOURCES = [
    (
        "dataset/ICAR Eng Annual Report_2024-25.pdf",
        "pdf",
        {"topic": "icar_report", "year": "2025"},
    ),
    (
        "dataset/Indian Farming November 2025.pdf",
        "pdf",
        {"topic": "farming", "year": "2025"},
    ),
    (
        "dataset/INTEGRATED PLANT NUTRITION MANAGEMENT SYSTEM 12 JAN 24.pdf",
        "pdf",
        {"topic": "nutrition"},
    ),
    (
        "dataset/Methods Manual Soil Testing In India - Department of Agriculture & Cooperation.pdf",
        "pdf",
        {"topic": "soil_testing"},
    ),
    (
        "dataset/iari_soil_water_testing_ocr.txt",
        "text",
        {"topic": "soil_testing"},
    ),
    (
        "data/KisanVani_Knowledge_Base.md",
        "markdown",
        {"topic": "kisanvani"},
    ),
]


def ingest_icar(embeddings: GoogleGenerativeAIEmbeddings) -> None:
    """Ingest ICAR PDFs, text, and markdown into icar_knowledge collection."""
    retriever = RAGRetriever(
        settings.rag.collections["icar"],
        embeddings,
        settings.rag.chroma_persist_dir,
    )

    existing = retriever.count()
    if existing > 100:
        logger.info("icar_knowledge already has %d docs — skipping ICAR ingestion.", existing)
        return

    loader = DocumentLoader()
    total_chunks = 0

    for rel_path, kind, meta in _ICAR_SOURCES:
        abs_path = str(_ROOT / rel_path)
        if not Path(abs_path).exists():
            logger.warning("File not found, skipping: %s", rel_path)
            continue

        logger.info("Loading %s (%s)…", rel_path, kind)
        try:
            if kind == "pdf":
                raw_docs = loader.load_pdf(abs_path, metadata=meta)
            elif kind == "text":
                raw_docs = loader.load_text(abs_path, metadata=meta)
            else:
                raw_docs = loader.load_markdown(abs_path, metadata=meta)

            chunks = loader.chunk(raw_docs)
            logger.info("  → %d chunks", len(chunks))
            retriever.add_documents(chunks)
            total_chunks += len(chunks)
        except Exception as exc:
            logger.error("Failed to ingest %s: %s", rel_path, exc)

    logger.info("ICAR ingestion complete. Total chunks added: %d", total_chunks)
    logger.info("icar_knowledge now has %d docs.", retriever.count())


# ---------------------------------------------------------------------------
# KCC ingestion
# ---------------------------------------------------------------------------

def ingest_kcc(embeddings: GoogleGenerativeAIEmbeddings, max_pages: int = 200) -> None:
    """Bulk-ingest KCC transcripts into kcc_transcripts collection."""
    retriever = RAGRetriever(
        settings.rag.collections["kcc"],
        embeddings,
        settings.rag.chroma_persist_dir,
    )

    existing = retriever.count()
    if existing > 1000:
        logger.info("kcc_transcripts already has %d docs — skipping KCC ingestion.", existing)
        return

    if not settings.data_gov_api_key:
        logger.warning(
            "AGRO_DATA_GOV_API_KEY not set — KCC ingestion will use sample data (10 records/call)."
        )

    kcc_loader = KCCLoader(api_key=settings.data_gov_api_key or None)
    total_docs = 0
    limit = 100

    for page_num in range(max_pages):
        offset = page_num * limit
        logger.info("KCC page %d/%d (offset=%d)…", page_num + 1, max_pages, offset)
        records = kcc_loader.fetch_page(offset=offset, limit=limit)

        if not records:
            logger.info("Empty page returned — stopping KCC ingestion.")
            break

        docs = kcc_loader.records_to_documents(records)
        if docs:
            retriever.add_documents(docs)
            total_docs += len(docs)
            logger.info("  → %d docs added (total: %d)", len(docs), total_docs)

        # Stop early if we got fewer records than the limit (last page)
        if len(records) < limit:
            logger.info("Last KCC page reached.")
            break

    logger.info("KCC ingestion complete. Total docs added: %d", total_docs)
    logger.info("kcc_transcripts now has %d docs.", retriever.count())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build ChromaDB vector database for AgroMind.")
    parser.add_argument("--icar", action="store_true", help="Ingest ICAR documents")
    parser.add_argument("--kcc", action="store_true", help="Ingest KCC transcripts")
    parser.add_argument("--all", action="store_true", dest="all_", help="Ingest everything (default)")
    parser.add_argument("--kcc-limit", type=int, default=200, metavar="N",
                        help="Max KCC pages to fetch (default: 200)")
    args = parser.parse_args()

    # Default to --all when no specific flag is given
    run_icar = args.icar or args.all_ or not (args.icar or args.kcc)
    run_kcc = args.kcc or args.all_ or not (args.icar or args.kcc)

    logger.info("Initialising Vertex AI embeddings (%s)…", settings.models.embedding)
    embeddings = _make_embeddings()
    logger.info("Embeddings ready.")

    if run_icar:
        logger.info("=== ICAR ingestion ===")
        ingest_icar(embeddings)

    if run_kcc:
        logger.info("=== KCC ingestion ===")
        ingest_kcc(embeddings, max_pages=args.kcc_limit)

    logger.info("All done.")


if __name__ == "__main__":
    main()
