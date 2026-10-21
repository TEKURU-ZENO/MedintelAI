"""Backward-compatible image/page loader backed by the shared document processor."""
import os
from typing import List, Optional, Union

import numpy as np

from app.ai.utils.logger import get_logger
from app.core.document_errors import DocumentProcessingError
from app.services.document_processing_service import DocumentProcessingService
from app.schemas.document import SourceType

logger = get_logger(__name__)
_processor = DocumentProcessingService()


def is_pdf(file_path_or_bytes: Union[str, bytes], filename: Optional[str] = None) -> bool:
    if filename and filename.lower().endswith(".pdf"):
        return True
    if isinstance(file_path_or_bytes, bytes):
        return file_path_or_bytes.startswith(b"%PDF-")
    if isinstance(file_path_or_bytes, str):
        if file_path_or_bytes.lower().endswith(".pdf"):
            return True
        try:
            with open(file_path_or_bytes, "rb") as handle:
                return handle.read(5).startswith(b"%PDF-")
        except OSError:
            return False
    return False


def render_pdf_to_images(file_path_or_bytes: Union[str, bytes], dpi_scale: float = 2.0) -> List[np.ndarray]:
    try:
        if isinstance(file_path_or_bytes, str):
            with open(file_path_or_bytes, "rb") as handle:
                data = handle.read()
            filename = os.path.basename(file_path_or_bytes)
        else:
            data = file_path_or_bytes
            filename = "document.pdf"
        # dpi_scale is retained for compatibility; rendering scale is centrally configured.
        document = _processor.process(data, filename, SourceType.PDF, render_scale=dpi_scale)
        return [page.image for page in document.pages if page.image is not None]
    except (OSError, DocumentProcessingError) as exc:
        logger.warning("PDF rendering failed: %s", exc)
        return []


def load_document_pages(file_path_or_bytes: Union[str, bytes, np.ndarray], filename: Optional[str] = None) -> List[np.ndarray]:
    try:
        if isinstance(file_path_or_bytes, np.ndarray):
            return [file_path_or_bytes]
        if isinstance(file_path_or_bytes, str):
            with open(file_path_or_bytes, "rb") as handle:
                data = handle.read()
            name = filename or os.path.basename(file_path_or_bytes)
        else:
            data = bytes(file_path_or_bytes)
            name = filename or ("document.pdf" if is_pdf(data) else "document.png")
        document = _processor.process(data, name)
        return [page.image for page in document.pages if page.image is not None]
    except (OSError, DocumentProcessingError, TypeError, ValueError) as exc:
        logger.warning("Document page loading failed: %s", exc)
        return []


def extract_pdf_digital_text(file_path_or_bytes: Union[str, bytes]) -> List[str]:
    """
    Extracts native digital vector text directly from PDF textpage if present.
    Returns list of page texts.
    """
    text_pages = []
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(file_path_or_bytes)
        for page in pdf:
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            text_pages.append(text.strip() if text else "")
        return text_pages
    except Exception as e:
        logger.warning(f"Could not extract digital text from PDF: {e}")
        return []
