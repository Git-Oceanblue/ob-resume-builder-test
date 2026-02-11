# when running use this command in the local :
import os
import io
import logging

from typing import List

from PyPDF2 import PdfReader
from docx import Document

logger = logging.getLogger(__name__)

# ----------------------------
# Optional PDF extraction deps
# ----------------------------
try:
    import pdfplumber  # better PDF text extraction than PyPDF2 for many layouts
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from pdf2image import convert_from_bytes
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


# ----------------------------
# PDF extractors
# ----------------------------
def _extract_text_from_pdf_with_pdfplumber(file_bytes: bytes) -> str:
    """Extract text using pdfplumber (often best for complex layouts)."""
    if not HAS_PDFPLUMBER:
        return ""

    text_parts: List[str] = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(page_text)
                logger.info(f"📄 pdfplumber page {page_idx}: {len(page_text or '')} chars")
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")
        return ""

    return "\n".join(text_parts).strip()


def _extract_text_from_pdf_with_pypdf2(file_bytes: bytes) -> str:
    """Extract text using PyPDF2 as fallback."""
    text_parts: List[str] = []
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        for page_idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
            logger.info(f"📄 PyPDF2 page {page_idx}: {len(page_text)} chars")
    except Exception as e:
        logger.warning(f"PyPDF2 extraction failed: {e}")
        return ""

    return "\n".join(text_parts).strip()


def _extract_text_from_pdf_with_ocr(file_bytes: bytes) -> str:
    """Extract text using OCR (for scanned/image-based PDFs)."""
    if not HAS_OCR:
        logger.warning("OCR not available (missing pdf2image and/or pytesseract).")
        return ""

    text_parts: List[str] = []
    try:
        images = convert_from_bytes(file_bytes, dpi=300)
        for i, image in enumerate(images, start=1):
            try:
                page_text = pytesseract.image_to_string(image, lang="eng") or ""
                if page_text.strip():
                    text_parts.append(page_text.strip())
                logger.info(f"🧾 OCR page {i}: {len(page_text)} chars")
            except Exception as e:
                logger.warning(f"OCR failed for page {i}: {e}")
                continue
    except Exception as e:
        logger.warning(f"OCR extraction failed: {e}")
        return ""

    return "\n".join(text_parts).strip()


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from PDF using multiple methods with fallback:
    1) pdfplumber
    2) PyPDF2
    3) OCR (if available)
    """
    text = _extract_text_from_pdf_with_pdfplumber(file_bytes)
    if text:
        logger.info("✅ PDF extracted successfully using pdfplumber")
        return text

    text = _extract_text_from_pdf_with_pypdf2(file_bytes)
    if text:
        logger.info("✅ PDF extracted successfully using PyPDF2")
        return text

    logger.info("⚠️ Standard PDF extraction failed; attempting OCR...")
    text = _extract_text_from_pdf_with_ocr(file_bytes)
    if text:
        logger.info("✅ PDF extracted successfully using OCR")
        return text

    logger.warning("❌ All PDF extraction methods failed")
    return ""


# ----------------------------
# DOCX extractor
# ----------------------------
def _extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX including paragraphs + tables."""
    try:
        doc = Document(io.BytesIO(file_bytes))
        parts: List[str] = []

        # Paragraphs
        for para in doc.paragraphs:
            t = (para.text or "").strip()
            if t:
                parts.append(t)

        # Tables
        for table in doc.tables:
            for row in table.rows:
                row_cells: List[str] = []
                for cell in row.cells:
                    ct = (cell.text or "").strip()
                    if ct:
                        row_cells.append(ct)
                if row_cells:
                    parts.append(" | ".join(row_cells))

        return "\n".join(parts).strip()
    except Exception as e:
        logger.warning(f"DOCX extraction failed: {e}")
        return ""


# ----------------------------
# TXT extractor
# ----------------------------
def _extract_text_from_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore").strip()


# ============================================================
# ✅ REQUIRED: keep this public function name & signature SAME
# ============================================================
def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from uploaded file using direct parsing (path-based API).

    Args:
        file_path: Path to the uploaded file

    Returns:
        Extracted text content
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    logger.info(f"🔍 Processing file: {file_path} (extension: {file_extension})")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    logger.info(f"📊 File size: {file_size} bytes")

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        # Route by extension (same supported types)
        if file_extension == ".pdf":
            logger.info("🔄 Extracting PDF (pdfplumber -> PyPDF2 -> OCR fallback)...")
            text = _extract_text_from_pdf(file_bytes)

        elif file_extension == ".docx":
            logger.info("🔄 Extracting DOCX (python-docx paragraphs + tables)...")
            text = _extract_text_from_docx(file_bytes)

        elif file_extension == ".txt":
            logger.info("🔄 Reading TXT...")
            text = _extract_text_from_txt(file_bytes)

        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        logger.info(f"✅ Extraction successful - Text length: {len(text)} characters")
        logger.info(f"📝 First 500 characters: {text[:500]}...")
        return text

    except Exception as e:
        logger.error(f"❌ File extraction failed: {e}")
        raise Exception(f"Failed to extract text from file: {e}")
