"""Extract text from a PDF — native pdfplumber first, OCRmyPDF fallback.

For scanned PDFs (no text layer), pdfplumber returns blank, so we OCR to a temp
searchable PDF and re-extract. ``extract_pages`` keeps per-page text.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pdfplumber

from resident_expenses.extract.ocr import OcrError, run_ocr

__all__ = ["OcrError", "extract_pages", "extract_text"]


def _raw_pages(path: Path) -> list[str]:
    with pdfplumber.open(path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def _has_text(pages: list[str]) -> bool:
    return any(p.strip() for p in pages)


def extract_pages(path: Path, *, ocr: bool = True, language: str = "spa") -> list[str]:
    pages = _raw_pages(path)
    if _has_text(pages) or not ocr:
        return pages
    with tempfile.TemporaryDirectory() as td:
        ocr_pdf = Path(td) / "ocr.pdf"
        run_ocr(path, ocr_pdf, language=language)
        return _raw_pages(ocr_pdf)


def extract_text(path: Path, *, ocr: bool = True, language: str = "spa") -> str:
    return "\n".join(extract_pages(path, ocr=ocr, language=language))
