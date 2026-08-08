"""PDF text extraction for complaint attachments.

Text-layer extraction only (pypdf) — no OCR. Scanned/image-only PDFs produce no
text and are rejected with a clear error so the caller can respond with a 400.
"""
import io
import logging

from pypdf import PdfReader

logger = logging.getLogger("pdf")


def extract_pdf_text(content: bytes) -> str:
    """Extract the text layer of a PDF document.

    Raises ValueError if the PDF has no extractable text (e.g. a scan).
    """
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("pypdf failed on a page: %s", e)
            text = ""
        if text.strip():
            pages.append(text.strip())
    joined = "\n".join(pages).strip()
    if not joined:
        raise ValueError(
            "No extractable text found in the PDF. Only text-based PDFs are "
            "supported (scanned images would require OCR)."
        )
    return joined
