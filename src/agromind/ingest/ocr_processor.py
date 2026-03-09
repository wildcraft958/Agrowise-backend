"""One-time OCR preprocessing for scanned PDFs using Vertex AI Document AI.

Converts scanned PDF pages to extractable text, saves output as a plain-text
file alongside the original PDF. The text file is then picked up by the
normal pdf_loader.py ingestion pipeline.

Usage:
    python -m agromind.ingest.ocr_processor \\
        --pdf "dataset/Soil and Water Testing Methods - Department of IARI.pdf" \\
        --output "dataset/iari_soil_water_testing_ocr.txt"

Requires:
    - GOOGLE_APPLICATION_CREDENTIALS set
    - Document AI API enabled (documentai.googleapis.com)
    - Processor created (run once, processor_name stored in config or passed as arg)
"""

import argparse
import logging
import time
from pathlib import Path

from google.cloud import documentai
from google.api_core.client_options import ClientOptions

logger = logging.getLogger(__name__)

# Processor created for agrowise-192e3
_DEFAULT_PROCESSOR = "projects/779023846662/locations/us/processors/f0653ed0f68823ec"
_LOCATION = "us"
_API_ENDPOINT = f"{_LOCATION}-documentai.googleapis.com"

# Document AI online processing limit per request
_MAX_PAGES_PER_REQUEST = 15


def ocr_pdf(
    pdf_path: str,
    output_txt_path: str,
    processor_name: str = _DEFAULT_PROCESSOR,
) -> int:
    """OCR a scanned PDF using Document AI and write extracted text to a file.

    Splits the PDF into chunks of up to 15 pages (Document AI online limit)
    and concatenates the results.

    Args:
        pdf_path: Path to the scanned PDF file.
        output_txt_path: Path to write the extracted text.
        processor_name: Full Document AI processor resource name.

    Returns:
        Number of pages processed.
    """
    client = documentai.DocumentProcessorServiceClient(
        client_options=ClientOptions(api_endpoint=_API_ENDPOINT)
    )

    pdf_bytes = Path(pdf_path).read_bytes()
    total_pages = _count_pdf_pages(pdf_bytes)
    logger.info("PDF: %s | %d pages", pdf_path, total_pages)

    all_text: list[str] = []

    for start in range(0, total_pages, _MAX_PAGES_PER_REQUEST):
        end = min(start + _MAX_PAGES_PER_REQUEST, total_pages)
        logger.info("  Processing pages %d–%d ...", start + 1, end)

        request = documentai.ProcessRequest(
            name=processor_name,
            raw_document=documentai.RawDocument(
                content=pdf_bytes,
                mime_type="application/pdf",
            ),
            process_options=documentai.ProcessOptions(
                individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
                    pages=list(range(start + 1, end + 1))  # 1-indexed
                )
            ),
        )

        result = client.process_document(request=request)
        page_text = result.document.text
        all_text.append(page_text)
        logger.info("    Extracted %d chars from pages %d–%d", len(page_text), start + 1, end)

        # Avoid quota exhaustion between chunks
        if end < total_pages:
            time.sleep(1)

    full_text = "\n\n".join(all_text)
    Path(output_txt_path).write_text(full_text, encoding="utf-8")
    logger.info("Saved %d chars to %s", len(full_text), output_txt_path)
    return total_pages


def _count_pdf_pages(pdf_bytes: bytes) -> int:
    """Count pages in a PDF without loading the full file into memory."""
    from pypdf import PdfReader
    import io
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return len(reader.pages)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="OCR a scanned PDF via Document AI")
    parser.add_argument(
        "--pdf",
        default="dataset/Soil and Water Testing Methods - Department of IARI.pdf",
    )
    parser.add_argument(
        "--output",
        default="dataset/iari_soil_water_testing_ocr.txt",
    )
    parser.add_argument("--processor", default=_DEFAULT_PROCESSOR)
    args = parser.parse_args()

    pages = ocr_pdf(args.pdf, args.output, args.processor)
    print(f"Done. {pages} pages processed → {args.output}")
