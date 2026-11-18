import os
import re
import logging
from dataclasses import dataclass, field
import pymupdf
import docx
import pdfplumber

logger = logging.getLogger("resumeranker.parser")


@dataclass
class ParseResult:
    raw_text: str
    page_count: int = 1
    quality: str = "good"  # "good", "partial", "poor"
    warnings: list[str] = field(default_factory=list)
    file_type: str = "unknown"


def clean_text(text: str) -> str:
    """
    Normalize extracted text:
    - Replace non-breaking and zero-width spaces
    - Standardize bullet points and quote characters
    - Collapse excessive blank lines and spaces
    """
    if not text:
        return ""

    # Replace special unicode spaces & symbols
    text = text.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"[\u2022\u2023\u25e6\u2043\u2219]", "-", text)

    # Standardize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Consolidate orphan bullet lines (e.g. "-\nText" -> "- Text")
    text = re.sub(r"(?:\n|^)[ \t]*[-•·*][ \t]*\n[ \t]*", "\n- ", text)

    # Collapse horizontal spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse 3 or more newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def parse_pdf_pymupdf(file_path: str) -> tuple[str, int]:
    """Extract text from PDF using PyMuPDF."""
    text_parts = []
    page_count = 0
    with pymupdf.open(file_path) as doc:
        page_count = len(doc)
        for page in doc:
            text = page.get_text("text")
            if text:
                text_parts.append(text)
    return "\n\n".join(text_parts), page_count


def parse_pdf_pdfplumber(file_path: str) -> tuple[str, int]:
    """Fallback extraction using pdfplumber for table-heavy or unusual layouts."""
    text_parts = []
    page_count = 0
    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text:
                text_parts.append(text)
    return "\n\n".join(text_parts), page_count


def parse_pdf(file_path: str) -> ParseResult:
    """
    Extract text from a PDF file using PyMuPDF as primary and pdfplumber as fallback.
    Assesses extraction quality and detects scanned/image PDFs.
    """
    warnings: list[str] = []
    raw_text = ""
    page_count = 1

    try:
        raw_text, page_count = parse_pdf_pymupdf(file_path)
    except Exception as exc:
        logger.warning(f"PyMuPDF failed on {file_path}: {exc}. Trying pdfplumber fallback.")
        warnings.append(f"PyMuPDF extraction issue: {str(exc)}")

    cleaned = clean_text(raw_text)

    # Fallback if PyMuPDF yielded very little text
    if len(cleaned) < 50:
        try:
            fallback_text, fb_page_count = parse_pdf_pdfplumber(file_path)
            fb_cleaned = clean_text(fallback_text)
            if len(fb_cleaned) > len(cleaned):
                cleaned = fb_cleaned
                page_count = fb_page_count
                warnings.append("Used pdfplumber fallback for better text extraction.")
        except Exception as exc:
            logger.warning(f"pdfplumber fallback also failed on {file_path}: {exc}")
            warnings.append(f"pdfplumber fallback issue: {str(exc)}")

    # Assess quality
    char_len = len(cleaned)
    if char_len >= 200:
        quality = "good"
    elif 50 <= char_len < 200:
        quality = "partial"
        warnings.append("Document yielded limited text content (between 50 and 200 characters).")
    else:
        quality = "poor"
        warnings.append(
            "Document yielded fewer than 50 characters of text. "
            "This may be a scanned image-only PDF, a protected file, or empty."
        )

    return ParseResult(
        raw_text=cleaned,
        page_count=max(1, page_count),
        quality=quality,
        warnings=warnings,
        file_type="pdf",
    )


def parse_docx(file_path: str) -> ParseResult:
    """
    Extract text from a Word document (.docx).
    Extracts body paragraphs and table contents.
    """
    warnings: list[str] = []
    text_parts: list[str] = []

    try:
        doc = docx.Document(file_path)

        # 1. Paragraphs
        for p in doc.paragraphs:
            if p.text and p.text.strip():
                text_parts.append(p.text.strip())

        # 2. Tables
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
                if row_cells:
                    # Deduplicate adjacent identical cells from merged cells
                    deduped: list[str] = []
                    for c in row_cells:
                        if not deduped or deduped[-1] != c:
                            deduped.append(c)
                    text_parts.append(" | ".join(deduped))

    except Exception as exc:
        logger.error(f"Failed to parse DOCX {file_path}: {exc}")
        return ParseResult(
            raw_text="",
            page_count=1,
            quality="poor",
            warnings=[f"Failed to parse DOCX file: {str(exc)}"],
            file_type="docx",
        )

    combined = "\n\n".join(text_parts)
    cleaned = clean_text(combined)

    char_len = len(cleaned)
    if char_len >= 200:
        quality = "good"
    elif 50 <= char_len < 200:
        quality = "partial"
        warnings.append("DOCX file yielded limited text content.")
    else:
        quality = "poor"
        warnings.append("DOCX file is empty or contains no extractable text.")

    return ParseResult(
        raw_text=cleaned,
        page_count=1,
        quality=quality,
        warnings=warnings,
        file_type="docx",
    )


def parse_txt(file_path: str) -> ParseResult:
    """Extract and decode plain text files."""
    warnings: list[str] = []
    raw = b""
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
    except Exception as exc:
        return ParseResult(
            raw_text="",
            page_count=1,
            quality="poor",
            warnings=[f"Could not read text file: {str(exc)}"],
            file_type="txt",
        )

    # Try encodings
    text = ""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    cleaned = clean_text(text)
    char_len = len(cleaned)

    if char_len >= 100:
        quality = "good"
    elif 20 <= char_len < 100:
        quality = "partial"
        warnings.append("Text file has very short content.")
    else:
        quality = "poor"
        warnings.append("Text file is empty or nearly empty.")

    return ParseResult(
        raw_text=cleaned,
        page_count=1,
        quality=quality,
        warnings=warnings,
        file_type="txt",
    )


def parse_document(file_path: str, filename: str | None = None) -> ParseResult:
    """
    Main document parsing router.
    Detects file extension and invokes the appropriate parser.
    """
    ref_name = filename or file_path
    ext = os.path.splitext(ref_name)[1].lower()

    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext == ".docx":
        return parse_docx(file_path)
    elif ext in [".txt", ".md"]:
        return parse_txt(file_path)
    else:
        return ParseResult(
            raw_text="",
            page_count=1,
            quality="poor",
            warnings=[f"Unsupported file format '{ext}'. Supported: .pdf, .docx, .txt"],
            file_type="unsupported",
        )

