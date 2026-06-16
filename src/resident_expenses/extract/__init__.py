"""PDF → text extraction: native pdfplumber, with an OCRmyPDF fallback for scans."""

from __future__ import annotations

from resident_expenses.extract.ocr import OcrError, run_ocr
from resident_expenses.extract.pdf_text import extract_pages, extract_text

__all__ = ["OcrError", "extract_pages", "extract_text", "run_ocr"]
